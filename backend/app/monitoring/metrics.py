"""Consultas de métricas técnicas para el panel de gerencia → Sistema.

Mismo criterio que analytics_repository: SQL explícito, en hora local del
negocio, que se puede pegar en psql para contrastar una cifra.

Dos formas de contar las llamadas al modelo, y las dos importan:
- **Intentos** (filas de llm_calls): lo que se le pidió de verdad a NVIDIA.
  Latencia y tokens se miden aquí.
- **Llamadas lógicas** (call_id distintos): lo que pidió la app. Una llamada
  lógica "falló" solo si NINGUNO de sus intentos salió bien — si falló y
  el reintento la salvó, el alumno no se enteró. Esa es la tasa de error
  que importa; la de intentos mide lo saturado que está el proveedor.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.analytics_repository import _local, local_now

# Horas de la ventana → ancho de cada tramo de las series (~50-60 puntos).
BUCKETS = {1: timedelta(minutes=1), 24: timedelta(minutes=30), 168: timedelta(hours=3), 720: timedelta(days=1)}


@dataclass(frozen=True)
class Window:
    hours: int

    @property
    def params(self) -> dict:
        end = local_now()
        return {
            "start": end - timedelta(hours=self.hours),
            "end": end,
            "bucket": BUCKETS[self.hours],
            "tz": settings.analytics_timezone,
        }


async def _one(db: AsyncSession, sql: str, params: dict) -> dict:
    return dict((await db.execute(text(sql), params)).mappings().one())


async def _all(db: AsyncSession, sql: str, params: dict) -> list[dict]:
    return [dict(r) for r in (await db.execute(text(sql), params)).mappings().all()]


LLM_CTE = f"""
calls AS (
    SELECT *, {_local('created_at')} AS at
      FROM llm_calls
     WHERE {_local('created_at')} >= CAST(:start AS timestamp)
),
logical AS (
    SELECT call_id, bool_or(status = 'ok') AS succeeded, count(*) AS attempts
      FROM calls GROUP BY call_id
)
"""


async def llm_summary(db: AsyncSession, w: Window) -> dict:
    sql = f"""
    WITH {LLM_CTE}
    SELECT
        (SELECT count(*) FROM calls) AS attempts,
        (SELECT count(*) FROM logical) AS calls,
        (SELECT count(*) FROM logical WHERE NOT succeeded) AS failed_calls,
        (SELECT count(*) FROM logical WHERE attempts > 1) AS retried_calls,
        (SELECT count(*) FROM calls WHERE status = 'error') AS failed_attempts,
        (SELECT coalesce(sum(input_tokens), 0) FROM calls) AS input_tokens,
        (SELECT coalesce(sum(output_tokens), 0) FROM calls) AS output_tokens,
        (SELECT count(*) FROM calls WHERE finish_reason = 'length') AS truncated,
        (SELECT count(*) FROM calls WHERE operation = 'chat' AND status = 'ok') AS chat_ok,
        (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) FROM calls WHERE status = 'ok' AND operation = 'chat')::float AS chat_p50_ms,
        (SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) FROM calls WHERE status = 'ok' AND operation = 'chat')::float AS chat_p95_ms,
        (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) FROM calls WHERE status = 'ok' AND purpose = 'tutor_reply')::float AS tutor_p50_ms,
        (SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) FROM calls WHERE status = 'ok' AND purpose = 'tutor_reply')::float AS tutor_p95_ms,
        (SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY queue_ms) FROM calls WHERE queue_ms IS NOT NULL)::float AS queue_p95_ms,
        (SELECT coalesce(sum(input_chars), 0) FROM calls WHERE operation = 'tts') AS tts_chars
    """
    return await _one(db, sql, w.params)


async def llm_series(db: AsyncSession, w: Window) -> list[dict]:
    """Por tramo: llamadas, fallos, tokens y latencia p50/p95 del chat.
    date_bin y no date_trunc: permite tramos de 30 minutos o 3 horas."""
    sql = f"""
    WITH {LLM_CTE},
    bins AS (
        SELECT generate_series(
            date_bin(CAST(:bucket AS interval), CAST(:start AS timestamp), TIMESTAMP '2000-01-01'),
            date_bin(CAST(:bucket AS interval), CAST(:end AS timestamp), TIMESTAMP '2000-01-01'),
            CAST(:bucket AS interval)
        ) AS b
    ),
    agg AS (
        SELECT date_bin(CAST(:bucket AS interval), at, TIMESTAMP '2000-01-01') AS b,
               count(*) AS attempts,
               count(*) FILTER (WHERE status = 'error') AS errors,
               coalesce(sum(input_tokens), 0) AS input_tokens,
               coalesce(sum(output_tokens), 0) AS output_tokens,
               (percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) FILTER (WHERE status = 'ok' AND operation = 'chat'))::float AS p50_ms,
               (percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) FILTER (WHERE status = 'ok' AND operation = 'chat'))::float AS p95_ms
          FROM calls GROUP BY 1
    )
    SELECT bins.b AS bucket,
           coalesce(agg.attempts, 0) AS attempts, coalesce(agg.errors, 0) AS errors,
           coalesce(agg.input_tokens, 0) AS input_tokens, coalesce(agg.output_tokens, 0) AS output_tokens,
           agg.p50_ms, agg.p95_ms
      FROM bins LEFT JOIN agg ON agg.b = bins.b
     ORDER BY bins.b
    """
    return await _all(db, sql, w.params)


async def llm_by_purpose(db: AsyncSession, w: Window) -> list[dict]:
    sql = f"""
    WITH {LLM_CTE}
    SELECT purpose, operation,
           count(*) AS attempts,
           count(DISTINCT call_id) AS calls,
           count(*) FILTER (WHERE status = 'error') AS errors,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) FILTER (WHERE status = 'ok'))::float AS p50_ms,
           (percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) FILTER (WHERE status = 'ok'))::float AS p95_ms,
           avg(input_tokens)::float AS avg_input_tokens,
           avg(output_tokens)::float AS avg_output_tokens,
           coalesce(sum(input_tokens), 0) + coalesce(sum(output_tokens), 0) AS total_tokens,
           count(*) FILTER (WHERE finish_reason = 'length') AS truncated
      FROM calls
     GROUP BY purpose, operation
     ORDER BY count(*) DESC
    """
    return await _all(db, sql, w.params)


async def llm_by_model(db: AsyncSession, w: Window) -> list[dict]:
    sql = f"""
    WITH {LLM_CTE}
    SELECT model, operation,
           count(*) AS attempts,
           count(*) FILTER (WHERE status = 'error') AS errors,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) FILTER (WHERE status = 'ok'))::float AS p50_ms,
           (percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) FILTER (WHERE status = 'ok'))::float AS p95_ms,
           coalesce(sum(input_tokens), 0) AS input_tokens,
           coalesce(sum(output_tokens), 0) AS output_tokens
      FROM calls
     GROUP BY model, operation
     ORDER BY count(*) DESC
    """
    return await _all(db, sql, w.params)


REQ_CTE = f"""
reqs AS (
    SELECT *, {_local('created_at')} AS at
      FROM request_logs
     WHERE {_local('created_at')} >= CAST(:start AS timestamp)
)
"""


async def http_summary(db: AsyncSession, w: Window) -> dict:
    sql = f"""
    WITH {REQ_CTE}
    SELECT count(*) AS requests,
           count(*) FILTER (WHERE status_code >= 500) AS server_errors,
           count(*) FILTER (WHERE status_code >= 400 AND status_code < 500) AS client_errors,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms))::float AS p50_ms,
           (percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms))::float AS p95_ms
      FROM reqs
    """
    return await _one(db, sql, w.params)


async def http_series(db: AsyncSession, w: Window) -> list[dict]:
    sql = f"""
    WITH {REQ_CTE},
    bins AS (
        SELECT generate_series(
            date_bin(CAST(:bucket AS interval), CAST(:start AS timestamp), TIMESTAMP '2000-01-01'),
            date_bin(CAST(:bucket AS interval), CAST(:end AS timestamp), TIMESTAMP '2000-01-01'),
            CAST(:bucket AS interval)
        ) AS b
    ),
    agg AS (
        SELECT date_bin(CAST(:bucket AS interval), at, TIMESTAMP '2000-01-01') AS b,
               count(*) AS requests,
               count(*) FILTER (WHERE status_code >= 500) AS server_errors,
               (percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms))::float AS p95_ms
          FROM reqs GROUP BY 1
    )
    SELECT bins.b AS bucket, coalesce(agg.requests, 0) AS requests,
           coalesce(agg.server_errors, 0) AS server_errors, agg.p95_ms
      FROM bins LEFT JOIN agg ON agg.b = bins.b
     ORDER BY bins.b
    """
    return await _all(db, sql, w.params)


async def http_routes(db: AsyncSession, w: Window) -> list[dict]:
    """Por ruta: volumen, errores y latencia. Se devuelven todas (son
    decenas, no miles) y el frontend ordena: por lentitud o por errores."""
    sql = f"""
    WITH {REQ_CTE}
    SELECT method, route,
           count(*) AS requests,
           count(*) FILTER (WHERE status_code >= 500) AS server_errors,
           count(*) FILTER (WHERE status_code >= 400 AND status_code < 500) AS client_errors,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms))::float AS p50_ms,
           (percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms))::float AS p95_ms,
           max(duration_ms) AS max_ms
      FROM reqs
     GROUP BY method, route
     ORDER BY count(*) DESC
    """
    return await _all(db, sql, w.params)


async def recent_failures(db: AsyncSession, w: Window, limit: int = 30) -> list[dict]:
    """Los fallos de las tres fuentes en una sola lista: modelo (intentos
    fallidos), API (5xx) y navegador. AGRUPADOS por fallo idéntico, con
    cuántas veces pasó y cuándo fue la primera y la última: un error en
    bucle son cientos de filas iguales, y sin agrupar taparía a los demás."""
    sql = f"""
    WITH f AS (
        SELECT {_local('created_at')} AS at, 'llm' AS source,
               purpose || ' · ' || model AS title,
               coalesce(error_type, 'Error') || ': ' || coalesce(error_message, '') AS message,
               NULL::text AS detail
          FROM llm_calls WHERE status = 'error'
        UNION ALL
        SELECT {_local('created_at')}, 'http',
               method || ' ' || route || ' → ' || status_code,
               coalesce(error_type, 'HTTP ' || status_code),
               error_detail
          FROM request_logs WHERE status_code >= 500
        UNION ALL
        SELECT {_local('created_at')}, 'client',
               coalesce(path, '(sin ruta)') || CASE WHEN in_app THEN '' ELSE ' · origen externo' END,
               message,
               stack
          FROM client_errors
    )
    SELECT source, title, message,
           count(*) AS occurrences,
           min(at) AS first_at,
           max(at) AS at,
           -- El detalle (traceback) de la ocurrencia más reciente.
           (array_agg(detail ORDER BY at DESC))[1] AS detail
      FROM f
     WHERE at >= CAST(:start AS timestamp)
     GROUP BY source, title, message
     ORDER BY max(at) DESC
     LIMIT :limit
    """
    return await _all(db, sql, {**w.params, "limit": limit})


async def client_error_count(db: AsyncSession, w: Window) -> int:
    """Solo los errores de NUESTRO código: las extensiones del navegador
    también lanzan errores en la página, y no deben disparar avisos (se
    siguen viendo en la lista, marcados como "origen externo")."""
    sql = f"SELECT count(*) AS n FROM client_errors WHERE in_app AND {_local('created_at')} >= CAST(:start AS timestamp)"
    return (await _one(db, sql, w.params))["n"]


async def prune(db: AsyncSession, retention_days: int) -> dict:
    """Borra la telemetría más vieja que `retention_days`. Son tablas que
    crecen con cada petición: sin poda, en unos meses pesarían más que
    los datos de negocio."""
    removed = {}
    for table in ("llm_calls", "request_logs", "client_errors"):
        result = await db.execute(
            text(f"DELETE FROM {table} WHERE created_at < now() - CAST(:days AS int) * interval '1 day'"),
            {"days": retention_days},
        )
        removed[table] = result.rowcount or 0
    await db.commit()
    return removed
