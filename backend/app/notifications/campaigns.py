"""Envío de una campaña escrita desde gerencia a un grupo de clientes.

Tres cosas que definen cómo está hecho esto:

1. **En segundo plano.** Escribirle a doscientas personas es un minuto
   largo de llamadas a Resend. Quien pulsa "Enviar" no puede quedarse
   mirando una pantalla cargando: la campaña se crea, la respuesta vuelve
   al instante y el envío sigue por detrás, actualizando el contador. La
   pantalla lo refresca sola.

2. **Se puede reanudar y no duplica.** Si el backend se reinicia en mitad
   de un envío, la campaña se queda a medias. Volver a lanzarla es seguro:
   cada correo lleva la clave "campana:<id>", única por alumno, así que
   quien ya lo recibió no lo recibe otra vez (ver service.py). Por eso hay
   un botón de reanudar y no hace falta nada más complicado.

3. **Es publicidad, y se trata como tal.** Una campaña respeta la baja del
   alumno, lleva enlace para darse de baja y no se envía a direcciones de
   prueba. Todo eso ya lo hace service.send: aquí solo se decide a quién
   se le intenta.
"""

import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models import EmailCampaign, User
from app.notifications import audiences, service
from app.notifications.layout import Button, Email
from app.notifications.messages import nombre_corto

logger = logging.getLogger(__name__)

KIND = "campana"

# Un respiro entre correos. Resend admite bastante más, pero salir a
# ráfaga máxima contra cualquier proveedor es la forma más rápida de que
# te marquen como remitente sospechoso.
PAUSA_SEGUNDOS = 0.15


def personalizar(texto: str, user: User) -> str:
    """{nombre} → el nombre de pila. Es la única sustitución que hay: una
    plantilla de campaña no es un lenguaje de programación."""
    return (texto or "").replace("{nombre}", nombre_corto(user.full_name))


def build_email(content: dict, user: User) -> Email:
    """El correo de una campaña, ya personalizado para este alumno.

    El cuerpo se escribe como texto normal y cada línea en blanco separa
    un párrafo. Se escapa antes de meterlo en el HTML: lo que se escribe
    en el panel es texto, nunca etiquetas.
    """
    from html import escape

    parrafos = [escape(p.strip()).replace("\n", "<br>") for p in (content.get("body") or "").split("\n\n") if p.strip()]
    boton = None
    if content.get("button_label"):
        url = content.get("button_url") or f"{settings.frontend_base_url.rstrip('/')}/dashboard"
        boton = Button(personalizar(content["button_label"], user), url)

    return Email(
        subject=personalizar(content["subject"], user),
        preheader=personalizar(content.get("preheader") or "", user),
        eyebrow=content.get("eyebrow") or "Espikin",
        title=personalizar(content["title"], user),
        paragraphs=[personalizar(p, user) for p in parrafos],
        button=boton,
    )


async def _recipients(db: AsyncSession, campaign: EmailCampaign) -> list[User]:
    ids = await audiences.user_ids(db, campaign.audience)
    if not ids:
        return []
    return list((await db.execute(select(User).where(User.id.in_(ids)))).scalars().all())


async def run(campaign_id: uuid.UUID) -> None:
    """Envía (o termina de enviar) una campaña. No lanza nunca: cualquier
    fallo se registra y la campaña queda como terminada con sus números."""
    async with AsyncSessionLocal() as db:
        campaign = await db.get(EmailCampaign, campaign_id)
        if campaign is None:
            return
        try:
            destinatarios = await _recipients(db, campaign)
            campaign.recipients = len(destinatarios)
            campaign.status = "enviando"
            await db.commit()

            enviados = omitidos = fallidos = 0
            for user in destinatarios:
                ok = await service.send(
                    db, user, KIND,
                    dedupe_key=f"{KIND}:{campaign.id}",
                    context={"campaign_id": str(campaign.id), "subject": campaign.subject},
                    builder=lambda u: build_email(campaign.content, u),
                )
                if ok:
                    enviados += 1
                else:
                    omitidos += 1
                # Los contadores se guardan sobre la marcha: es lo que
                # mira quien tiene la pantalla abierta viendo el avance.
                campaign.sent, campaign.skipped = enviados, omitidos
                await db.commit()
                await asyncio.sleep(PAUSA_SEGUNDOS)

            # Cuántos de los "no enviados" fueron un fallo de verdad y no
            # una baja: se cuenta de las filas, que es donde está el motivo.
            fallidos = await _contar_fallidos(db, campaign.id)
            campaign.failed = fallidos
            campaign.skipped = max(0, omitidos - fallidos)
            campaign.status = "terminada"
            campaign.finished_at = datetime.utcnow()
            await db.commit()
            logger.info("Campaña %s terminada: %s enviados, %s omitidos, %s fallidos", campaign.name, enviados, campaign.skipped, fallidos)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo enviando la campaña %s", campaign_id)
            campaign.status = "terminada"
            campaign.finished_at = datetime.utcnow()
            await db.commit()


async def _contar_fallidos(db: AsyncSession, campaign_id: uuid.UUID) -> int:
    from sqlalchemy import func

    from app.models import EmailMessage

    return (
        await db.execute(
            select(func.count())
            .select_from(EmailMessage)
            .where(EmailMessage.dedupe_key == f"{KIND}:{campaign_id}", EmailMessage.status == "failed")
        )
    ).scalar() or 0
