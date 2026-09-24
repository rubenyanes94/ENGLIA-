"""Panel de gerencia → Correos: qué se le ha enviado a los clientes, y
escribir mensajes nuevos para enviarles.

Dos partes que se apoyan en lo mismo:

- **Enviados**: el registro de todos los correos (email_messages), los de
  siempre y los escritos a mano, con su estado y el motivo si alguno no
  salió. Es solo lectura.
- **Plantillas y campañas**: escribir un mensaje, verlo tal como le va a
  llegar al alumno, mandárselo primero a uno mismo y después a un grupo.

Es la segunda escritura que puede hacer gerencia (la primera es aprobar
pagos), y por eso lleva dos frenos que no son negociables: el envío real
exige confirmar a cuántas personas va, y antes hay un botón para
probarlo en la propia bandeja. Un correo mal escrito a doscientos
clientes no se puede recoger.
"""

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_manager
from app.models import EmailCampaign, EmailMessage, EmailTemplate, User
from app.notifications import audiences, campaigns, resend_client, service, starters
from app.notifications.layout import logo_base64, render_html, render_text
from app.repositories.analytics_repository import local_now
from app.schemas.management import (
    AudienceOut,
    CampaignIn,
    CampaignOut,
    EmailKindCount,
    EmailMessageList,
    EmailMessageRow,
    EmailSummary,
    StarterOut,
    TemplateIn,
    TemplateOut,
    TemplatePreviewOut,
)

router = APIRouter(prefix="/management", tags=["management"], dependencies=[Depends(get_current_manager)])

SUMMARY_DAYS = 30


def _local(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(settings.analytics_timezone)).replace(tzinfo=None)


def _blocked_reason() -> str | None:
    """Por qué no está saliendo ningún correo, si es el caso. Se dice en la
    pantalla: un panel lleno de ceros sin explicación se interpreta como
    "no hay clientes", que es justo lo contrario de lo que pasa."""
    if not resend_client.is_configured():
        return "Falta la clave de Resend (RESEND_API_KEY): no se está enviando ningún correo."
    if settings.email_sandbox_to:
        return f"Modo de pruebas: todos los correos se desvían a {settings.email_sandbox_to} y no llegan a los clientes."
    return None


# --- Enviados ---------------------------------------------------------------


@router.get("/emails", response_model=EmailMessageList)
async def list_emails(
    kind: str | None = None,
    status_: str | None = Query(None, alias="status"),
    search: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> EmailMessageList:
    customer = aliased(User)
    base = select(EmailMessage, customer).join(customer, customer.id == EmailMessage.user_id)
    if kind:
        base = base.where(EmailMessage.kind == kind)
    if status_:
        base = base.where(EmailMessage.status == status_)
    if search and search.strip():
        like = f"%{search.strip()}%"
        base = base.where(or_(customer.full_name.ilike(like), customer.email.ilike(like), EmailMessage.subject.ilike(like)))

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (await db.execute(base.order_by(EmailMessage.created_at.desc()).limit(limit).offset(offset))).all()

    return EmailMessageList(
        items=[
            EmailMessageRow(
                id=message.id, kind=message.kind, status=message.status, to_email=message.to_email,
                subject=message.subject, error=message.error, created_at=_local(message.created_at),
                customer={"id": user.id, "full_name": user.full_name, "email": user.email},
            )
            for message, user in rows
        ],
        total=total,
        as_of=local_now(),
    )


@router.get("/emails/summary", response_model=EmailSummary)
async def emails_summary(db: AsyncSession = Depends(get_db)) -> EmailSummary:
    since = datetime.utcnow() - timedelta(days=SUMMARY_DAYS)
    rows = (
        await db.execute(
            select(EmailMessage.kind, EmailMessage.status, func.count())
            .where(EmailMessage.created_at >= since)
            .group_by(EmailMessage.kind, EmailMessage.status)
        )
    ).all()

    por_tipo: dict[str, dict[str, int]] = {}
    for kind, estado, total in rows:
        por_tipo.setdefault(kind, {"sent": 0, "failed": 0, "skipped": 0})
        if estado in ("sent", "failed", "skipped"):
            por_tipo[kind][estado] += total

    sent = sum(v["sent"] for v in por_tipo.values())
    failed = sum(v["failed"] for v in por_tipo.values())
    skipped = sum(v["skipped"] for v in por_tipo.values())
    intentados = sent + failed
    last = (await db.execute(select(func.max(EmailMessage.created_at)).where(EmailMessage.status == "sent"))).scalar()

    return EmailSummary(
        days=SUMMARY_DAYS,
        sent=sent, failed=failed, skipped=skipped,
        failure_rate=(failed / intentados) if intentados else None,
        by_kind=[EmailKindCount(kind=k, **v) for k, v in sorted(por_tipo.items(), key=lambda kv: -sum(kv[1].values()))],
        last_sent_at=_local(last),
        blocked_reason=_blocked_reason(),
    )


# --- Plantillas -------------------------------------------------------------


async def _template_out(db: AsyncSession, template: EmailTemplate) -> TemplateOut:
    author = await db.get(User, template.created_by_id) if template.created_by_id else None
    envios = (
        await db.execute(
            select(func.count(), func.max(EmailCampaign.created_at)).where(EmailCampaign.template_id == template.id)
        )
    ).one()
    return TemplateOut(
        id=template.id, name=template.name, subject=template.subject, preheader=template.preheader,
        eyebrow=template.eyebrow, title=template.title, body=template.body,
        button_label=template.button_label, button_url=template.button_url,
        created_at=_local(template.created_at), updated_at=_local(template.updated_at),
        author_name=author.full_name if author else None,
        times_sent=envios[0] or 0, last_sent_at=_local(envios[1]),
    )


@router.get("/email-starters", response_model=list[StarterOut])
async def list_starters() -> list[StarterOut]:
    """Los mensajes ya escritos con los que se puede empezar una campaña.
    Son fijos (app/notifications/starters.py), no filas de la base: son
    el punto de partida, y lo que se guarda después es una plantilla
    normal del usuario."""
    return [StarterOut(**s, button_url=None) for s in starters.as_dicts()]


@router.get("/email-templates", response_model=list[TemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db)) -> list[TemplateOut]:
    rows = (await db.execute(select(EmailTemplate).order_by(EmailTemplate.updated_at.desc()))).scalars().all()
    return [await _template_out(db, t) for t in rows]


@router.post("/email-templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(payload: TemplateIn, manager: User = Depends(get_current_manager), db: AsyncSession = Depends(get_db)) -> TemplateOut:
    template = EmailTemplate(**payload.model_dump(), created_by_id=manager.id)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return await _template_out(db, template)


@router.patch("/email-templates/{template_id}", response_model=TemplateOut)
async def update_template(template_id: uuid.UUID, payload: TemplateIn, db: AsyncSession = Depends(get_db)) -> TemplateOut:
    template = await db.get(EmailTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Esa plantilla ya no existe.")
    for field, value in payload.model_dump().items():
        setattr(template, field, value)
    await db.commit()
    await db.refresh(template)
    return await _template_out(db, template)


@router.delete("/email-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    template = await db.get(EmailTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Esa plantilla ya no existe.")
    # Las campañas ya enviadas NO se borran: su template_id queda en NULL
    # (ondelete SET NULL) y conservan su propia copia del texto. Borrar la
    # plantilla no puede borrar el registro de lo que se envió.
    await db.delete(template)
    await db.commit()


@router.post("/email-templates/preview", response_model=TemplatePreviewOut)
async def preview_template(payload: TemplateIn, manager: User = Depends(get_current_manager)) -> TemplatePreviewOut:
    """El correo tal cual, sin guardar nada: es lo que se ve mientras se
    escribe. Se personaliza con el nombre de quien está mirando, para que
    se note dónde cae el {nombre}."""
    email = campaigns.build_email(payload.model_dump(), manager)
    baja = f"{settings.frontend_base_url.rstrip('/')}/api/notifications/baja?token=ejemplo"
    # En el correo de verdad el logotipo va adjunto con un Content-ID, que
    # un navegador no resuelve; para el <iframe> del panel se manda el
    # mismo PNG incrustado.
    logo = settings.email_logo_url or f"data:image/png;base64,{logo_base64()}"
    return TemplatePreviewOut(subject=email.subject, html=render_html(email, baja, logo_url=logo), text=render_text(email, baja))


@router.post("/email-templates/{template_id}/test", status_code=status.HTTP_202_ACCEPTED)
async def send_test(template_id: uuid.UUID, manager: User = Depends(get_current_manager), db: AsyncSession = Depends(get_db)) -> dict:
    """Se lo manda a quien está en el panel, a su propia dirección. El
    paso obligatorio antes de enviárselo a nadie más: en el navegador todo
    se ve bien, y es en Gmail donde se descubre el asunto cortado.

    Lleva clave de deduplicación distinta cada vez (con la hora) para
    poder probar una plantilla las veces que haga falta.
    """
    template = await db.get(EmailTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Esa plantilla ya no existe.")
    if not resend_client.is_configured():
        raise HTTPException(status_code=503, detail="Falta la clave de Resend (RESEND_API_KEY) para poder enviar.")
    if not manager.notifications_enabled:
        # Una campaña respeta la baja, y la prueba va por el mismo camino:
        # sin esto el envío se omitiría en silencio y el panel diría un
        # "no se pudo enviar" que no explica nada.
        raise HTTPException(
            status_code=409,
            detail="Tienes desactivados los recordatorios por correo en tu perfil, así que la prueba no te llegaría. Actívalos para probar.",
        )

    contenido = {
        "subject": template.subject, "preheader": template.preheader, "eyebrow": template.eyebrow,
        "title": template.title, "body": template.body,
        "button_label": template.button_label, "button_url": template.button_url,
    }
    marca = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    enviado = await service.send(
        db, manager, campaigns.KIND,
        dedupe_key=f"prueba:{template.id}:{marca}",
        context={"template_id": str(template.id), "prueba": True},
        builder=lambda u: campaigns.build_email(contenido, u),
    )
    if not enviado:
        raise HTTPException(status_code=502, detail="No se pudo enviar la prueba. Revisa la pestaña Sistema.")
    return {"sent_to": settings.email_sandbox_to or manager.email}


# --- Campañas ---------------------------------------------------------------


@router.get("/email-audiences", response_model=list[AudienceOut])
async def list_audiences(db: AsyncSession = Depends(get_db)) -> list[AudienceOut]:
    return [AudienceOut(**a) for a in await audiences.counts(db)]


def _campaign_out(campaign: EmailCampaign, sender: User | None) -> CampaignOut:
    grupo = audiences.AUDIENCES.get(campaign.audience)
    return CampaignOut(
        id=campaign.id, name=campaign.name, subject=campaign.subject, audience=campaign.audience,
        audience_label=grupo.label if grupo else campaign.audience,
        status=campaign.status, recipients=campaign.recipients, sent=campaign.sent,
        skipped=campaign.skipped, failed=campaign.failed,
        sender_name=sender.full_name if sender else None,
        created_at=_local(campaign.created_at), finished_at=_local(campaign.finished_at),
    )


@router.get("/email-campaigns", response_model=list[CampaignOut])
async def list_campaigns(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)) -> list[CampaignOut]:
    sender = aliased(User)
    rows = (
        await db.execute(
            select(EmailCampaign, sender)
            .outerjoin(sender, sender.id == EmailCampaign.sent_by_id)
            .order_by(EmailCampaign.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [_campaign_out(c, s) for c, s in rows]


@router.post("/email-campaigns", response_model=CampaignOut, status_code=status.HTTP_202_ACCEPTED)
async def start_campaign(
    payload: CampaignIn,
    background: BackgroundTasks,
    manager: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    if payload.audience not in audiences.AUDIENCES:
        raise HTTPException(status_code=400, detail="Ese grupo de destinatarios no existe.")
    if not resend_client.is_configured():
        raise HTTPException(status_code=503, detail="Falta la clave de Resend (RESEND_API_KEY) para poder enviar.")
    template = await db.get(EmailTemplate, payload.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Esa plantilla ya no existe.")

    campaign = EmailCampaign(
        template_id=template.id, name=template.name, subject=template.subject, audience=payload.audience,
        # Copia del texto: la plantilla puede cambiar mañana, esto no.
        content={
            "subject": template.subject, "preheader": template.preheader, "eyebrow": template.eyebrow,
            "title": template.title, "body": template.body,
            "button_label": template.button_label, "button_url": template.button_url,
        },
        status="enviando", sent_by_id=manager.id,
        recipients=len(await audiences.user_ids(db, payload.audience)),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    # El envío sigue por detrás; la pantalla enseña el avance.
    background.add_task(campaigns.run, campaign.id)
    return _campaign_out(campaign, manager)


@router.post("/email-campaigns/{campaign_id}/resume", response_model=CampaignOut, status_code=status.HTTP_202_ACCEPTED)
async def resume_campaign(
    campaign_id: uuid.UUID,
    background: BackgroundTasks,
    manager: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    """Termina un envío que se quedó a medias (un reinicio del backend en
    mitad de la cola). Es seguro pulsarlo: a quien ya le llegó no le
    vuelve a llegar."""
    campaign = await db.get(EmailCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Esa campaña ya no existe.")
    background.add_task(campaigns.run, campaign.id)
    return _campaign_out(campaign, manager)
