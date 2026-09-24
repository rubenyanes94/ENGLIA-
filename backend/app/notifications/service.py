"""Enviar un correo a un alumno: la única puerta por la que se manda algo.

Lo que garantiza esta capa, y que ninguna de las que llama debería tener
que repetir:

1. **Nunca dos veces el mismo.** Cada correo lleva una `dedupe_key` única
   por usuario, y la fila se inserta ANTES de llamar a Resend. El bucle de
   retención pasa cada hora y vuelve a ver al mismo alumno: sin esto le
   llegarían veinticuatro avisos iguales al día.

2. **Un correo que falla no rompe nada.** Ninguna función de aquí lanza
   hacia arriba. Si Resend está caído, un registro se completa igual y un
   pago se aprueba igual; queda la fila en "failed" y el panel de Sistema
   lo avisa. Al revés sería absurdo: perder una venta porque no salió un
   correo de bienvenida.

3. **Se respeta la baja.** Los correos comerciales no salen si el alumno
   apagó los avisos (`notifications_enabled`) o si se apagan todos con
   MARKETING_EMAILS_ENABLED. Los transaccionales — su pago, su cuenta —
   se envían igual.

4. **Mientras no haya dominio, no se escribe a clientes reales.** Con
   EMAIL_SANDBOX_TO puesto, todos los correos se desvían a esa dirección
   con un aviso arriba diciendo para quién era. Es lo que permite probar
   el ciclo completo contra la base de datos de verdad sin mandarle nada
   a nadie.
"""

import logging
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_unsubscribe_token
from app.models import EmailMessage, User
from app.notifications import messages, resend_client
from app.notifications.layout import LOGO_CID, logo_base64, render_html, render_text

logger = logging.getLogger(__name__)

# Un fallo de red se reintenta en la vuelta siguiente del bucle; uno de
# configuración (dominio sin verificar) fallaría para siempre, así que a
# la tercera se deja de intentar y que lo cante el panel de Sistema.
MAX_ATTEMPTS = 3

# Dominios que NO existen por definición (RFC 2606/6761): son los de los
# datos de demostración y los de cualquier cuenta de prueba. Escribirles
# garantiza un rebote duro, y los rebotes son justo lo que hace que
# Gmail empiece a mandar a spam lo que sí va a clientes reales.
DOMINIOS_FALSOS = ("example.com", "example.org", "example.net", ".test", ".invalid", ".local", ".localhost")


def es_entregable(email: str) -> bool:
    correo = (email or "").lower()
    return "@" in correo and not correo.endswith(DOMINIOS_FALSOS)


def _unsubscribe_url(user: User) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/api/notifications/baja?token={create_unsubscribe_token(str(user.id))}"


async def _already_handled(db: AsyncSession, user_id, dedupe_key: str) -> EmailMessage | None:
    """La fila anterior de este mismo correo, si la hay."""
    result = await db.execute(
        select(EmailMessage).where(EmailMessage.user_id == user_id, EmailMessage.dedupe_key == dedupe_key)
    )
    return result.scalars().first()


async def send(
    db: AsyncSession, user: User, kind: str, *,
    dedupe_key: str | None = None, context: dict | None = None,
    builder: Callable[[User], "messages.Email"] | None = None,
) -> bool:
    """Envía el correo `kind` a `user`. Devuelve True solo si salió.

    `dedupe_key` identifica este envío concreto: "pago_aprobado:<id del
    pago>", "vence_pronto:2026-10-23". Por defecto es el propio `kind`,
    que es lo correcto para los que se mandan una sola vez en la vida
    (la bienvenida).

    `builder` es para las campañas escritas desde gerencia, cuyo texto no
    está en messages.py sino en la base de datos: recibe el alumno y
    devuelve su correo ya personalizado. Así `context` puede guardar solo
    el id de la campaña en vez de repetir el cuerpo entero en la fila de
    cada uno de los doscientos destinatarios.
    """
    context = context or {}
    key = dedupe_key or kind
    comercial = kind in messages.MARKETING_KINDS

    # Apagados del todo: no se deja rastro a propósito. Si mañana se
    # encienden, los avisos pendientes salen; una fila "skipped" los
    # habría bloqueado para siempre.
    if comercial and not settings.marketing_emails_enabled:
        return False
    if not resend_client.is_configured():
        logger.debug("Sin RESEND_API_KEY: no se envía %s a %s", kind, user.email)
        return False

    previous = await _already_handled(db, user.id, key)
    if previous is not None and (previous.status in ("sent", "skipped") or previous.context.get("attempts", 0) >= MAX_ATTEMPTS):
        return False

    if not es_entregable(user.email):
        await _record(db, previous, user, kind, key, context, status="skipped", error="Dirección de prueba: no se envía.", subject="—")
        return False

    # La baja SÍ se deja registrada: es la prueba de que se respetó, y de
    # paso impide recalcularlo cada hora.
    if comercial and not user.notifications_enabled:
        await _record(db, previous, user, kind, key, context, status="skipped", error="El alumno no quiere recibir recordatorios.", subject="—")
        return False

    try:
        email = (
            builder(user)
            if builder is not None
            else messages.build(kind, full_name=user.full_name, app_url=settings.frontend_base_url.rstrip("/"), context=context)
        )
    except Exception:  # noqa: BLE001 — un tipo mal escrito no tumba un registro
        logger.exception("No se pudo armar el correo %s para %s", kind, user.email)
        return False
    destino = settings.email_sandbox_to or user.email
    if settings.email_sandbox_to:
        # Como aviso de arriba y no como primer párrafo: quien revisa un
        # correo en modo de pruebas está mirando el diseño, y una nota
        # nuestra metida en el cuerpo es justo lo que no deja verlo.
        email.banner = f"<strong>Modo de pruebas.</strong> Este correo era para {user.full_name} ({user.email})."

    baja = _unsubscribe_url(user) if comercial else None
    row = await _record(db, previous, user, kind, key, context, status="sending", subject=email.subject, to_email=destino)
    if row is None:  # otro proceso se adelantó: es suyo, no nuestro
        return False

    # El logotipo viaja dentro del correo salvo que haya una URL pública
    # configurada (ver layout.py).
    logo_url = settings.email_logo_url or None
    adjuntos = None if logo_url else [{"filename": "espikin.png", "content": logo_base64(), "content_id": LOGO_CID, "content_type": "image/png"}]

    try:
        message_id = await resend_client.send_email(
            to=destino, subject=email.subject,
            html=render_html(email, baja, logo_url=logo_url), text=render_text(email, baja), tag=kind,
            attachments=adjuntos,
            # List-Unsubscribe: el botón de "cancelar suscripción" que
            # pinta el propio Gmail junto al remitente. Solo en los
            # comerciales, que son los que lo exigen.
            headers={"List-Unsubscribe": f"<{baja}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"} if baja else None,
        )
    except Exception as exc:  # noqa: BLE001 — un correo nunca tumba lo que lo disparó
        row.status = "failed"
        row.error = str(exc)[:1000]
        row.context = {**row.context, "attempts": row.context.get("attempts", 0) + 1}
        await db.commit()
        logger.warning("No se pudo enviar el correo %s a %s: %s", kind, destino, exc)
        return False

    row.status = "sent"
    row.provider_message_id = message_id
    row.error = None
    await db.commit()
    logger.info("Correo %s enviado a %s", kind, destino)
    return True


async def _record(
    db: AsyncSession, previous: EmailMessage | None, user: User, kind: str, key: str, context: dict,
    *, status: str, subject: str, to_email: str | None = None, error: str | None = None,
) -> EmailMessage | None:
    """Crea (o reutiliza, si es un reintento) la fila del envío. Devuelve
    None si otro proceso insertó la misma clave a la vez."""
    if previous is not None:
        previous.status = status
        previous.subject = subject
        previous.error = error
        if to_email:
            previous.to_email = to_email
        await db.commit()
        return previous

    row = EmailMessage(
        user_id=user.id, kind=kind, dedupe_key=key, status=status,
        to_email=to_email or user.email, subject=subject, error=error, context=context,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        # La restricción única (user_id, dedupe_key) hizo su trabajo: otro
        # worker mandó este mismo correo mientras preparábamos el nuestro.
        await db.rollback()
        return None
    await db.refresh(row)
    return row
