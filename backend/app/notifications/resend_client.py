"""Envío de correos a través de Resend (https://resend.com).

Se habla con su API REST por httpx en vez de usar el SDK oficial: el SDK
de Python es SÍNCRONO y bloquearía el event loop de FastAPI en mitad de
un registro o de una aprobación de pago. httpx ya es dependencia (lo usa
la tasa del BCV) y la API es una sola llamada POST.

Aquí no hay reglas de negocio: esto solo sabe mandar un correo y contar
qué respondió Resend. Quién recibe qué, y si le toca o no, se decide en
service.py.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"
TIMEOUT = 20


class EmailError(Exception):
    """Resend no aceptó el envío. El mensaje es el que devuelve su API
    (ej. "The gmail.com domain is not verified"), que es exactamente lo
    que hay que leer para arreglarlo."""


def is_configured() -> bool:
    return bool(settings.resend_api_key)


async def send_email(
    *, to: str, subject: str, html: str, text: str, tag: str | None = None, headers: dict[str, str] | None = None
) -> str:
    """Envía y devuelve el id del mensaje en Resend. Lanza EmailError si
    la API lo rechaza."""
    if not is_configured():
        raise EmailError("No hay RESEND_API_KEY configurada.")

    payload: dict = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if settings.email_reply_to:
        payload["reply_to"] = settings.email_reply_to
    if tag:
        # Etiqueta por tipo de correo, para poder mirar en el panel de
        # Resend cuántos "vence_pronto" se enviaron y cuántos rebotaron.
        payload["tags"] = [{"name": "kind", "value": tag}]
    if headers:
        # Hoy solo List-Unsubscribe (ver service.py). Gmail y Outlook
        # enseñan su propio botón "cancelar suscripción" cuando esta
        # cabecera está presente, y penalizan al remitente masivo que no
        # la manda: es entregabilidad, no un adorno.
        payload["headers"] = headers

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        )

    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json().get("message", detail)
        except ValueError:
            pass
        raise EmailError(f"Resend respondió {response.status_code}: {detail}")

    return response.json().get("id", "")
