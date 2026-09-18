"""Monitoreo técnico: estado en vivo, métricas y errores del navegador.

Dos routers:
- `router` (/management/monitoring): el panel de gerencia → Sistema.
  Solo lectura, rol manager o admin, igual que el resto de /management.
- `public_router` (/monitoring/client-errors): donde el navegador de
  cualquier usuario reporta sus errores de JavaScript. Público a
  propósito — un error en la pantalla de login también hay que verlo —
  y por eso con tope de tamaño y de frecuencia.
"""

import logging
import uuid
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_manager
from app.core.redis import redis_client
from app.core.security import decode_access_token
from app.models import ClientError
from app.monitoring import alerts as alert_rules
from app.monitoring import health
from app.monitoring import metrics
from app.repositories.analytics_repository import local_now
from app.schemas.monitoring import ActiveConfig, ClientErrorIn, MetricsOut, StatusOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/management/monitoring", tags=["monitoring"], dependencies=[Depends(get_current_manager)])
public_router = APIRouter(prefix="/monitoring", tags=["monitoring"])

ALLOWED_HOURS = tuple(metrics.BUCKETS)

# Errores de navegador: como mucho N por minuto y origen. Detrás del proxy
# de Vite todas las peticiones llegan desde la misma IP, así que en la
# práctica es un tope global: suficiente para ver un fallo, imposible de
# usar para llenar la base de datos.
CLIENT_ERRORS_PER_MINUTE = 30


async def _maybe_prune(db: AsyncSession) -> None:
    """Poda la telemetría vieja como mucho una vez por hora, aprovechando
    que alguien mira el panel (no hay tareas programadas en el proyecto).
    El candado en Redis evita que dos pestañas abiertas poden a la vez."""
    try:
        if await redis_client.set("monitoring:prune-lock", "1", nx=True, ex=3600):
            removed = await metrics.prune(db, settings.monitoring_retention_days)
            if any(removed.values()):
                logger.info("Telemetría podada: %s", removed)
    except Exception:  # noqa: BLE001 — podar es mantenimiento, no puede tumbar el panel
        logger.warning("No se pudo podar la telemetría", exc_info=True)


@router.get("/status", response_model=StatusOut)
async def monitoring_status(db: AsyncSession = Depends(get_db)) -> StatusOut:
    """Comprobaciones en vivo + avisos. Tarda un par de segundos: pregunta
    de verdad a NVIDIA, a Redis y al worker, no lee un valor guardado."""
    checks = await health.run_all(db)

    last_hour, last_day = metrics.Window(1), metrics.Window(24)
    alerts = alert_rules.from_checks(checks) + alert_rules.from_metrics(
        llm_1h=await metrics.llm_summary(db, last_hour),
        http_1h=await metrics.http_summary(db, last_hour),
        llm_24h=await metrics.llm_summary(db, last_day),
        client_errors_24h=await metrics.client_error_count(db, last_day),
    )
    await _maybe_prune(db)

    return StatusOut(
        checked_at=local_now(),
        overall=alert_rules.overall(alerts),
        checks=checks,
        alerts=sorted(alerts, key=lambda a: a["severity"] != "critical"),
        config=ActiveConfig(
            llm_host=urlparse(settings.llm_base_url).netloc or settings.llm_base_url,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            moderation_model=settings.moderation_model,
            pronunciation_model=settings.pronunciation_model,
            tts_provider=settings.tts_provider,
            llm_max_concurrency=settings.llm_max_concurrency,
            llm_max_retries=settings.llm_max_retries,
            api_key_configured=bool(settings.llm_api_key),
            environment=settings.environment,
        ),
    )


@router.get("/metrics", response_model=MetricsOut)
async def monitoring_metrics(hours: int = Query(24), db: AsyncSession = Depends(get_db)) -> MetricsOut:
    """Nemotron (latencia, tokens, errores, reintentos) y API HTTP en la
    ventana pedida, más la lista de fallos recientes. Solo lee la BD."""
    if hours not in ALLOWED_HOURS:
        raise HTTPException(status_code=422, detail=f"hours debe ser uno de {ALLOWED_HOURS}.")
    w = metrics.Window(hours)
    params = w.params
    return MetricsOut(
        hours=hours,
        start=params["start"],
        end=params["end"],
        bucket_minutes=int(metrics.BUCKETS[hours].total_seconds() // 60),
        llm=await metrics.llm_summary(db, w),
        llm_series=await metrics.llm_series(db, w),
        llm_by_purpose=await metrics.llm_by_purpose(db, w),
        llm_by_model=await metrics.llm_by_model(db, w),
        http=await metrics.http_summary(db, w),
        http_series=await metrics.http_series(db, w),
        routes=await metrics.http_routes(db, w),
        client_errors=await metrics.client_error_count(db, w),
        failures=await metrics.recent_failures(db, w),
    )


def _optional_user_id(request: Request) -> uuid.UUID | None:
    """Si el navegador manda su token, se anota de quién es el error; si
    no (pantalla de login, token caducado), se guarda igual sin usuario."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        return uuid.UUID(decode_access_token(header[7:]))
    except Exception:  # noqa: BLE001
        return None


@public_router.post("/client-errors", status_code=status.HTTP_204_NO_CONTENT)
async def report_client_error(payload: ClientErrorIn, request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    origin = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?")
    key = f"monitoring:client-errors:{origin}:{datetime.now().strftime('%Y%m%d%H%M')}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 120)
        if count > CLIENT_ERRORS_PER_MINUTE:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiados reportes de error.")
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 — sin Redis se acepta igual: perder el tope es mejor que perder el error
        pass

    db.add(ClientError(
        user_id=_optional_user_id(request),
        kind=payload.kind,
        message=payload.message,
        source=payload.source,
        path=payload.path,
        stack=payload.stack,
        user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        in_app=payload.in_app,
    ))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
