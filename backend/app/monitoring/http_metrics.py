"""Middleware que registra cada petición a la API: ruta, código y duración.

ASGI puro y no `@app.middleware("http")` (BaseHTTPMiddleware): este ve
la excepción ORIGINAL cuando un endpoint revienta, antes de que Starlette
la convierta en un 500 genérico, y así el panel puede enseñar el tipo de
error y dónde saltó. La excepción se vuelve a lanzar tal cual: la
respuesta al cliente no cambia.

La fila se guarda DESPUÉS de haber enviado la respuesta, en su propia
sesión: medir no añade tiempo a lo que espera el alumno, y si falla el
guardado se ignora.
"""

import logging
import time
import traceback

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.db import AsyncSessionLocal
from app.models import RequestLog

logger = logging.getLogger(__name__)

# Ruido que no dice nada de si la app funciona: estáticos, documentación
# y el propio panel de monitoreo (se refresca solo cada minuto y acabaría
# siendo "la ruta más usada").
SKIP_PREFIXES = ("/media", "/docs", "/redoc", "/openapi.json", "/favicon.ico", "/management/monitoring")


def route_template(scope: Scope) -> str:
    """"/chat/sessions/9d3b…/messages" → "/chat/sessions/{session_id}/messages".

    Starlette no deja la plantilla en el scope, pero sí los parámetros ya
    extraídos: se sustituye cada valor por su nombre, segmento a segmento
    (no con un replace sobre la cadena, que podría pisar otro trozo)."""
    path = scope.get("path", "")
    if "endpoint" not in scope:
        return "(ruta inexistente)"
    params = {str(v): k for k, v in (scope.get("path_params") or {}).items()}
    return "/".join("{" + params[seg] + "}" if seg in params else seg for seg in path.split("/"))


class RequestMetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] in ("OPTIONS", "HEAD")
            or scope["path"].startswith(SKIP_PREFIXES)
        ):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 500  # si revienta antes de responder, es un 500
        error: BaseException | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            error = exc
            raise
        finally:
            await self._record(scope, status_code, int((time.perf_counter() - start) * 1000), error)

    async def _record(self, scope: Scope, status_code: int, duration_ms: int, error: BaseException | None) -> None:
        detail = None
        if error is not None:
            # Las últimas líneas del traceback: dónde saltó, no el recorrido
            # entero por Starlette, que no dice nada.
            detail = "".join(traceback.format_exception(error)[-4:])[-3000:]
        try:
            async with AsyncSessionLocal() as session:
                session.add(RequestLog(
                    method=scope["method"],
                    route=route_template(scope)[:200],
                    status_code=status_code,
                    duration_ms=duration_ms,
                    error_type=type(error).__name__ if error else None,
                    error_detail=detail,
                ))
                await session.commit()
        except Exception:  # noqa: BLE001 — medir nunca puede romper la app
            logger.warning("No se pudo registrar la petición", exc_info=True)
