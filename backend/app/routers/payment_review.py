"""Panel de gerencia → Pagos: el registro de todos los pagos y la cola de
los que hay que verificar a mano (Pago Móvil y Binance a la cuenta personal).

La ÚNICA escritura que puede hacer gerencia: aprobar o rechazar pagos.
Todo lo demás de /management es solo lectura, y /admin (contenido,
planes) sigue cerrado para gerencia. Cada revisión guarda quién la hizo.
"""

import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_manager
from app.models import Payment, Subscription, User
from app.repositories.analytics_repository import local_now
from app.schemas.management import (
    PaymentReviewList,
    PaymentReviewRow,
    PaymentReviewSummary,
    RejectRequest,
)
from app.services import payment_review

router = APIRouter(prefix="/management/payments", tags=["management"], dependencies=[Depends(get_current_manager)])

STATUSES = ("pending_verification", "approved", "rejected", "failed", "refunded")


def _local(value: datetime | None) -> datetime | None:
    """La BD guarda UTC; el panel entero habla en hora de Caracas. Sin esto
    un pago de las 6 de la tarde se vería "a las 10 de la noche"."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(settings.analytics_timezone)).replace(tzinfo=None)


def _row(payment: Payment, customer: User, reviewer: User | None, subscription: Subscription | None) -> PaymentReviewRow:
    return PaymentReviewRow(
        id=payment.id,
        provider=payment.provider,
        status=payment.status,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        external_reference=payment.external_reference,
        payload=payment.payload or {},
        created_at=_local(payment.created_at),
        reviewed_at=_local(payment.reviewed_at),
        reviewer_name=reviewer.full_name if reviewer else None,
        customer={"id": customer.id, "full_name": customer.full_name, "email": customer.email},
        access_until=_local(subscription.current_period_end) if subscription else None,
    )


@router.get("", response_model=PaymentReviewList)
async def list_payments(
    status: str = Query("pending_verification", description="Estado, o 'all' para todos"),
    provider: str | None = Query(None),
    search: str | None = Query(None, max_length=100, description="Cliente, email, referencia u orden"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaymentReviewList:
    """Todos los pagos, con sus datos declarados. Los pendientes salen del
    más ANTIGUO al más nuevo (quien espera más, primero); el resto, del más
    reciente al más antiguo, como un historial."""
    if status != "all" and status not in STATUSES:
        raise HTTPException(status_code=422, detail=f"status debe ser 'all' o uno de {STATUSES}.")
    reviewer = aliased(User)
    query = (
        select(Payment, User, reviewer, Subscription)
        .join(User, User.id == Payment.user_id)
        .outerjoin(reviewer, reviewer.id == Payment.reviewed_by_id)
        .outerjoin(Subscription, Subscription.id == Payment.subscription_id)
    )
    if status != "all":
        query = query.where(Payment.status == status)
    if provider:
        query = query.where(Payment.provider == provider)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                Payment.external_reference.ilike(pattern),
                Payment.payload["reference_number"].astext.ilike(pattern),
                Payment.payload["order_id"].astext.ilike(pattern),
            )
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    order = Payment.created_at.asc() if status == "pending_verification" else Payment.created_at.desc()
    rows = (await db.execute(query.order_by(order, Payment.id).limit(limit).offset(offset))).all()
    return PaymentReviewList(items=[_row(*r) for r in rows], total=total, as_of=local_now())


@router.get("/summary", response_model=PaymentReviewSummary)
async def payments_summary(db: AsyncSession = Depends(get_db)) -> PaymentReviewSummary:
    """Para el contador de la pestaña y la cabecera de la cola."""
    pending = (
        await db.execute(
            select(Payment.provider, func.count(), func.min(Payment.created_at))
            .where(Payment.status == "pending_verification")
            .group_by(Payment.provider)
        )
    ).all()
    # "Hoy" en hora de Caracas, no en UTC: a las 8 de la noche UTC ya es mañana.
    local_midnight = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    approved = (
        await db.execute(
            select(func.count(), func.coalesce(func.sum(Payment.amount_cents), 0)).where(
                Payment.status == "approved",
                func.timezone(settings.analytics_timezone, func.timezone("UTC", Payment.reviewed_at)) >= local_midnight,
            )
        )
    ).one()
    return PaymentReviewSummary(
        pending=sum(n for _, n, _ in pending),
        pending_by_provider={p: n for p, n, _ in pending},
        oldest_pending_at=_local(min((t for _, _, t in pending), default=None)),
        approved_today=approved[0],
        approved_today_cents=approved[1],
    )


@router.post("/{payment_id}/approve", response_model=PaymentReviewRow)
async def approve_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
) -> PaymentReviewRow:
    """Aprueba el pago y da acceso al alumno por un periodo (o lo prolonga si
    aún tenía días). Ver services/payment_review.py."""
    payment = await payment_review.approve(db, payment_id, current_user.id)
    return await _reload(db, payment.id)


@router.post("/{payment_id}/reject", response_model=PaymentReviewRow)
async def reject_payment(
    payment_id: uuid.UUID,
    payload: RejectRequest,
    current_user: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
) -> PaymentReviewRow:
    payment = await payment_review.reject(db, payment_id, current_user.id, payload.reason.strip())
    return await _reload(db, payment.id)


async def _reload(db: AsyncSession, payment_id: uuid.UUID) -> PaymentReviewRow:
    reviewer = aliased(User)
    row = (
        await db.execute(
            select(Payment, User, reviewer, Subscription)
            .join(User, User.id == Payment.user_id)
            .outerjoin(reviewer, reviewer.id == Payment.reviewed_by_id)
            .outerjoin(Subscription, Subscription.id == Payment.subscription_id)
            .where(Payment.id == payment_id)
        )
    ).one()
    return _row(*row)
