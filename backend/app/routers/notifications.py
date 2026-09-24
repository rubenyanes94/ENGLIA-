"""Baja (y alta) de los correos de recordatorio, desde el enlace del pie.

Es público a propósito: quien quiere dejar de recibir correos no puede
tener que acordarse de su contraseña para conseguirlo. Lo que protege la
acción es el token firmado del enlace (create_unsubscribe_token), que no
caduca — un correo de hace ocho meses tiene que seguir funcionando — y
que no sirve para iniciar sesión.

Responde HTML y no JSON porque quien llega aquí es una persona que acaba
de pulsar un enlace en su correo, no el frontend. Es una página suelta,
servida por el backend, para que funcione aunque el enlace se abra en un
navegador sin sesión.

Acepta GET (el enlace del pie) y POST (el botón "cancelar suscripción"
que pinta Gmail, que usa List-Unsubscribe-Post en un solo clic).
"""

import uuid

import jwt
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_unsubscribe_token, decode_unsubscribe_token
from app.models import User
from app.notifications.layout import BORDER, BRAND, FONT, INK, MUTED, TEXT

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _page(title: str, message: str, action: tuple[str, str] | None = None) -> HTMLResponse:
    """La misma cara que los correos: violeta de marca sobre fondo claro."""
    boton = (
        f'<a href="{action[1]}" style="display:inline-block;margin-top:22px;padding:13px 28px;border-radius:12px;'
        f'background:{BRAND};color:#fff;font-weight:700;text-decoration:none;">{action[0]}</a>'
        if action
        else ""
    )
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Espikin</title></head>
<body style="margin:0;background:#F1F0F7;font-family:{FONT};">
  <div style="max-width:520px;margin:0 auto;padding:48px 20px;text-align:center;">
    <div style="display:inline-flex;align-items:center;gap:10px;margin-bottom:24px;">
      <span style="display:inline-block;width:34px;height:34px;line-height:34px;border-radius:11px;background:{BRAND};color:#fff;font-weight:800;font-size:19px;">e</span>
      <span style="font-size:19px;font-weight:700;color:{INK};">Espikin</span>
    </div>
    <div style="background:#fff;border:1px solid {BORDER};border-radius:20px;padding:36px 30px;">
      <h1 style="margin:0 0 12px;font-size:23px;font-weight:800;color:{INK};">{title}</h1>
      <p style="margin:0;font-size:16px;line-height:1.6;color:{TEXT};">{message}</p>
      {boton}
    </div>
    <p style="margin:22px 0 0;font-size:12px;color:{MUTED};">Espikin · Tu academia de inglés con tutores de inteligencia artificial</p>
  </div>
</body></html>""")


async def _apply(token: str, db: AsyncSession, *, enabled: bool) -> HTMLResponse:
    try:
        user_id = uuid.UUID(decode_unsubscribe_token(token))
    except (jwt.PyJWTError, ValueError):
        return _page(
            "Este enlace no es válido",
            "Puede que esté incompleto por cómo lo abrió tu correo. Cambia la preferencia desde tu perfil en Espikin y listo.",
        )

    user = await db.get(User, user_id)
    if user is None:
        return _page("No encontramos esta cuenta", "Puede que la cuenta ya no exista. No recibirás más correos nuestros.")

    user.notifications_enabled = enabled
    await db.commit()

    if enabled:
        return _page("Listo, los vuelves a recibir", f"Te avisaremos de nuevo antes de que venza tu acceso, {user.full_name.split(' ')[0]}.")
    nuevo_token = create_unsubscribe_token(str(user.id))
    return _page(
        "Listo, no te escribimos más",
        "No volverás a recibir recordatorios ni avisos comerciales. Seguirás recibiendo lo de tu cuenta: "
        "confirmaciones de pago y avisos sobre tu suscripción.",
        action=("Me di de baja sin querer", f"/notifications/alta?token={nuevo_token}"),
    )


@router.get("/baja", response_class=HTMLResponse)
@router.post("/baja", response_class=HTMLResponse)
async def unsubscribe(token: str = Query(...), db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    return await _apply(token, db, enabled=False)


@router.get("/alta", response_class=HTMLResponse)
async def resubscribe(token: str = Query(...), db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    return await _apply(token, db, enabled=True)
