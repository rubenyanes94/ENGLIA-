"""Comprobaciones en vivo del panel de gerencia → Sistema.

Cada comprobación devuelve un `Check` con estado ok / warning / critical /
unknown y, si algo va mal, una pista de qué hacer. Todas corren en paralelo
y con tiempo máximo: si Redis está caído, el panel tiene que decirlo en
un par de segundos, no quedarse colgado esperándolo.

La más valiosa es la del catálogo de NVIDIA: compara los modelos que la
app tiene CONFIGURADOS (en settings y en los tutores de la BD) con los que
NVIDIA dice tener. Es exactamente el fallo que tumbó el chat el 17/09/2026:
el backend pedía "nomic-embed-text", un modelo de Ollama, a NVIDIA → 404
en cada primer mensaje. Con esto habría salido en rojo antes de que un
alumno lo notara.
"""

import asyncio
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
import redis.asyncio as aioredis
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_client
from app.repositories.analytics_repository import local_now

CHECK_TIMEOUT_S = 5.0
BACKEND_DIR = Path(__file__).resolve().parents[2]


@dataclass
class Check:
    key: str
    label: str
    status: str  # ok | warning | critical | unknown
    detail: str
    latency_ms: int | None = None
    hint: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


async def check_database(db: AsyncSession) -> Check:
    start = time.perf_counter()
    try:
        row = (
            await db.execute(
                text(
                    "SELECT pg_size_pretty(pg_database_size(current_database())) AS size, "
                    "(SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) AS connections"
                )
            )
        ).mappings().one()
    except Exception as exc:  # noqa: BLE001
        return Check("database", "Base de datos (PostgreSQL)", "critical", f"No responde: {type(exc).__name__}", _ms(start),
                     "Sin base de datos no funciona nada: revisar el contenedor db.")
    return Check("database", "Base de datos (PostgreSQL)", "ok", f"{row['size']} · {row['connections']} conexiones abiertas", _ms(start))


async def check_redis() -> Check:
    start = time.perf_counter()
    try:
        await asyncio.wait_for(redis_client.ping(), CHECK_TIMEOUT_S)
        info = await asyncio.wait_for(redis_client.info("memory"), CHECK_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001
        return Check("redis", "Redis (memoria del tutor)", "critical", f"No responde: {type(exc).__name__}", _ms(start),
                     "Sin Redis el tutor pierde el hilo de la conversación: revisar el contenedor redis.")
    return Check("redis", "Redis (memoria del tutor)", "ok", f"{info.get('used_memory_human', '?')} en uso", _ms(start))


async def check_worker() -> Check:
    """El worker de Celery resume y memoriza cada sesión al cerrarla. Si
    está caído, el chat sigue funcionando y NADIE lo nota: la memoria de
    largo plazo del tutor deja de crecer en silencio. Por eso se vigila."""
    from app.workers.celery_app import celery_app

    start = time.perf_counter()
    try:
        replies = await asyncio.wait_for(asyncio.to_thread(celery_app.control.ping, timeout=1.0), CHECK_TIMEOUT_S)
        broker = aioredis.from_url(settings.celery_broker_url)
        try:
            queued = await asyncio.wait_for(broker.llen("celery"), CHECK_TIMEOUT_S)
        finally:
            await broker.aclose()
    except Exception as exc:  # noqa: BLE001
        return Check("worker", "Worker de Celery (resúmenes)", "critical", f"No se pudo consultar: {type(exc).__name__}", _ms(start),
                     "Revisar el contenedor celery_worker (docker logs englia_celery_worker).")
    if not replies:
        return Check("worker", "Worker de Celery (resúmenes)", "critical", f"Ningún worker responde · {queued} tareas en cola", _ms(start),
                     "Las sesiones cerradas no se están resumiendo. Reiniciar: docker restart englia_celery_worker.")
    status = "warning" if queued > 20 else "ok"
    hint = "La cola crece más rápido de lo que el worker la vacía." if status == "warning" else None
    return Check("worker", "Worker de Celery (resúmenes)", status, f"{len(replies)} worker(s) activo(s) · {queued} tareas en cola", _ms(start), hint)


async def _configured_models(db: AsyncSession) -> dict[str, str]:
    """Modelo → para qué se usa. Incluye los de los tutores de la BD: el
    tutor usa el model_id de su fila, no settings.llm_model."""
    models = {
        settings.llm_model: "chat (por defecto)",
        settings.moderation_model: "moderación",
        settings.pronunciation_model: "pronunciación",
    }
    rows = await db.execute(text("SELECT DISTINCT model_id FROM agent_personas WHERE is_active"))
    for (model_id,) in rows:
        models.setdefault(model_id, "tutor (agent_personas)")
    return models


async def _catalog(base_url: str, api_key: str) -> tuple[set[str], int]:
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_S) as client:
        response = await client.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )
        response.raise_for_status()
        return {m["id"] for m in response.json().get("data", [])}, _ms(start)


async def check_llm_catalog(configured: dict[str, str]) -> list[Check]:
    host = urlparse(settings.llm_base_url).netloc or settings.llm_base_url
    checks: list[Check] = []

    try:
        chat_ids, latency = await _catalog(settings.llm_base_url, settings.llm_api_key)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        hint = "La clave de NVIDIA no es válida o caducó (NVIDIA_API_KEY)." if code in (401, 403) else "El proveedor responde con error."
        return [Check("llm_api", f"API de modelos ({host})", "critical", f"HTTP {code}", None, hint)]
    except Exception as exc:  # noqa: BLE001
        return [Check("llm_api", f"API de modelos ({host})", "critical", f"Inaccesible: {type(exc).__name__}", None,
                      "Sin acceso al proveedor el tutor no puede responder. Revisar conexión y LLM_BASE_URL.")]

    checks.append(Check("llm_api", f"API de modelos ({host})", "ok", f"Responde · {len(chat_ids)} modelos en el catálogo", latency))

    missing = [f"{m} ({use})" for m, use in configured.items() if m not in chat_ids]
    if missing:
        checks.append(Check("llm_models", "Modelos de chat configurados", "critical", "No existen en el catálogo: " + ", ".join(missing), None,
                            "Las llamadas a esos modelos dan 404. Revisar LLM_MODEL / MODERATION_MODEL / PRONUNCIATION_MODEL "
                            "y el model_id de los tutores; si el .env está bien, el contenedor puede tener variables antiguas."))
    else:
        checks.append(Check("llm_models", "Modelos de chat configurados", "ok", f"Los {len(configured)} existen: " + ", ".join(sorted(configured)), None))

    # Embeddings: pueden vivir en otro endpoint (ver config.embedding_base_url).
    try:
        emb_ids = chat_ids if settings.embedding_base_url == settings.llm_base_url else (await _catalog(settings.embedding_base_url, settings.embedding_api_key))[0]
        if settings.embedding_model in emb_ids:
            checks.append(Check("embedding_model", "Modelo de embeddings", "ok", settings.embedding_model, None))
        else:
            checks.append(Check("embedding_model", "Modelo de embeddings", "critical", f"{settings.embedding_model} no existe en el catálogo", None,
                                "El primer mensaje de cada sesión y los resúmenes fallarán (fue la causa del error 500 del 17/09)."))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("embedding_model", "Modelo de embeddings", "critical", f"Catálogo inaccesible: {type(exc).__name__}", None))
    return checks


async def check_llm_auth() -> list[Check]:
    """Petición REAL y autenticada al proveedor. Hace falta porque el
    catálogo (/models) de NVIDIA es público: con una clave inválida o
    caducada responde igual de bien, y el panel diría "todo ok" mientras
    cada mensaje del tutor da 401.

    Se usa un embedding de "ping" (2 tokens, ~150 ms): valida la clave y
    el modelo de embeddings a la vez. Solo si el chat usa OTRA clave se
    prueba también el chat, con max_tokens=1 para que no cueste casi nada.
    Van por httpx directo, fuera de la telemetría: son sondas, no uso real."""
    checks: list[Check] = []

    async def probe(label: str, url: str, api_key: str, body: dict) -> Check:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_S * 2) as client:
                response = await client.post(url, json=body, headers={"Authorization": f"Bearer {api_key}"} if api_key else {})
        except Exception as exc:  # noqa: BLE001
            return Check("llm_auth", label, "critical", f"Sin respuesta: {type(exc).__name__}", _ms(start),
                         "El proveedor no contesta a una petición real.")
        latency = _ms(start)
        if response.status_code == 200:
            return Check("llm_auth", label, "ok", "Responde a una petición real con la clave configurada", latency)
        if response.status_code in (401, 403):
            return Check("llm_auth", label, "critical", f"HTTP {response.status_code}: la clave no es válida", latency,
                         "NVIDIA rechaza la clave: renovarla en build.nvidia.com y actualizar NVIDIA_API_KEY. Mientras tanto no funciona ninguna llamada al modelo.")
        if response.status_code == 404:
            return Check("llm_auth", label, "critical", "HTTP 404: el modelo no existe", latency,
                         "Revisar el nombre del modelo configurado.")
        if response.status_code == 429:
            return Check("llm_auth", label, "warning", "HTTP 429: límite de peticiones alcanzado", latency,
                         "NVIDIA está limitando el ritmo: las llamadas se reintentan, pero el alumno espera más.")
        return Check("llm_auth", label, "warning", f"HTTP {response.status_code}", latency, "El proveedor responde con error.")

    checks.append(await probe(
        "Clave de NVIDIA (petición real)",
        f"{settings.embedding_base_url.rstrip('/')}/embeddings",
        settings.embedding_api_key,
        {"model": settings.embedding_model, "input": ["ping"]},
    ))
    if settings.llm_api_key != settings.embedding_api_key or settings.llm_base_url != settings.embedding_base_url:
        checks.append(await probe(
            "Clave del chat (petición real)",
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            settings.llm_api_key,
            {"model": settings.llm_model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
        ))
    return checks


def check_migrations_sync(db_version: str | None) -> Check:
    try:
        head = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini"))).get_current_head()
    except Exception as exc:  # noqa: BLE001
        return Check("migrations", "Migraciones de la base de datos", "unknown", f"No se pudo leer Alembic: {type(exc).__name__}")
    if db_version == head:
        return Check("migrations", "Migraciones de la base de datos", "ok", f"Al día ({head})")
    return Check("migrations", "Migraciones de la base de datos", "warning", f"BD en {db_version or 'ninguna'}, código en {head}", None,
                 "Hay migraciones sin aplicar: alembic upgrade head. Las funciones nuevas pueden fallar hasta entonces.")


async def check_migrations(db: AsyncSession) -> Check:
    try:
        version = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
    except Exception:  # noqa: BLE001
        version = None
    return check_migrations_sync(version)


async def check_pending_summaries(db: AsyncSession) -> Check:
    """Sesiones cerradas hace más de 10 minutos (y menos de un día) que
    siguen sin resumen: la huella de un worker que falla en silencio."""
    pending = (
        await db.execute(
            text(
                """
                SELECT count(*) FROM conversation_sessions s
                 WHERE s.ended_at IS NOT NULL AND s.summary IS NULL
                   AND s.ended_at BETWEEN now() - interval '24 hours' AND now() - interval '10 minutes'
                   AND EXISTS (SELECT 1 FROM conversation_messages m WHERE m.session_id = s.id AND m.role = 'user')
                """
            )
        )
    ).scalar()
    if pending:
        return Check("summaries", "Resúmenes de sesión", "warning", f"{pending} sesiones cerradas en las últimas 24 h siguen sin resumir", None,
                     "El worker no está terminando las tareas: mirar docker logs englia_celery_worker.")
    return Check("summaries", "Resúmenes de sesión", "ok", "Todas las sesiones cerradas en las últimas 24 h tienen resumen")


async def check_bcv_rate(db: AsyncSession) -> Check:
    """La tasa del BCV con la que Pago Móvil calcula el monto en bolívares.
    Se lee sola cada hora (app/billing/bcv_rate.py); aquí se vigila que siga
    llegando. Tres fallos posibles, de más a menos grave: no hay ninguna
    tasa (no se puede pedir un monto), la que rige es de hace días (se
    cobra mal), o el lector lleva más de un día sin traer nada nuevo."""
    from app.billing import bcv_rate

    label = "Tasa BCV (Pago Móvil)"
    applicable = await bcv_rate.rate_for_today(db)
    if applicable is None:
        return Check("bcv_rate", label, "critical", "No hay ninguna tasa guardada", None,
                     "Pago Móvil no puede decirle al alumno cuánto transferir. Revisar si www.bcv.org.ve responde.")
    rate_text = f"{applicable.rate:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    detail = f"{rate_text} Bs/$ · fecha valor {applicable.value_date:%d/%m} · {applicable.source}"
    if settings.pago_movil_bs_per_usd:
        return Check("bcv_rate", label, "warning", detail, None,
                     "Hay una tasa fija manual (PAGO_MOVIL_BS_PER_USD): no se actualiza sola. Quitarla para volver a la del BCV.")

    today = local_now().date()
    if (today - applicable.value_date).days > 4:
        return Check("bcv_rate", label, "warning", detail, None,
                     "La tasa que se está cobrando es de hace más de 4 días: el monto en bolívares puede estar desfasado.")
    last_fetch = (
        await db.execute(text("SELECT max(fetched_at) FROM exchange_rates WHERE source = 'bcv.org.ve'"))
    ).scalar()
    if last_fetch is None or datetime.utcnow() - last_fetch > timedelta(hours=26):
        return Check("bcv_rate", label, "warning", detail + " · el lector no trae tasas nuevas desde hace más de un día", None,
                     "Revisar el log del backend (\"tasa del BCV\"): puede que el BCV haya cambiado su página.")
    return Check("bcv_rate", label, "ok", detail)


def check_disk() -> Check:
    try:
        usage = shutil.disk_usage(settings.media_root)
    except Exception as exc:  # noqa: BLE001
        return Check("disk", "Disco (audios de lecciones)", "unknown", f"No se pudo medir: {type(exc).__name__}")
    free = usage.free / usage.total
    gb = usage.free / 1024**3
    status = "critical" if free < 0.05 else "warning" if free < 0.15 else "ok"
    hint = "Con el disco lleno no se pueden guardar audios ni fotos de perfil." if status != "ok" else None
    return Check("disk", "Disco (audios de lecciones)", status, f"{gb:.1f} GB libres ({free:.0%})", None, hint)


async def run_all(db: AsyncSession) -> list[dict]:
    # La BD va primero y sola: las demás que la usan comparten la misma
    # sesión, y una AsyncSession no admite consultas concurrentes.
    database = await check_database(db)
    db_checks: list[Check] = []
    configured: dict[str, str] = {settings.llm_model: "chat (por defecto)"}
    if database.status == "ok":
        db_checks = [await check_migrations(db), await check_pending_summaries(db), await check_bcv_rate(db)]
        configured = await _configured_models(db)

    # Lo que sale de este proceso (NVIDIA, Redis, el worker) sí va en paralelo.
    llm_checks, auth_checks, redis_check, worker_check = await asyncio.gather(
        check_llm_catalog(configured), check_llm_auth(), check_redis(), check_worker()
    )
    checks = [*auth_checks, *llm_checks, database, redis_check, worker_check, *db_checks, check_disk()]
    return [c.as_dict() for c in checks]
