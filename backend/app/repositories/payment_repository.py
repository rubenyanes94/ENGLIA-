import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from app.models import Payment


async def create(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    amount_cents: int,
    currency: str,
    payload: dict,
    external_reference: str | None = None,
    status: str = "pending_verification",
    subscription_id: uuid.UUID | None = None,
) -> Payment:
    # subscription_id casi siempre None al crear: para Pago Móvil todavía
    # no existe la Subscription (se enlaza al aprobar). Los webhooks de
    # PayPal/Stripe/Binance sí lo pasan de una vez porque para cuando
    # crean el Payment, la Subscription pending ya existía (se creó al
    # iniciar el checkout).
    payment = Payment(
        user_id=user_id,
        provider=provider,
        amount_cents=amount_cents,
        currency=currency,
        payload=payload,
        external_reference=external_reference,
        status=status,
        subscription_id=subscription_id,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def get_by_id(db: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return await db.get(Payment, payment_id)


async def get_by_external_reference(db: AsyncSession, provider: str, external_reference: str) -> Payment | None:
    """Para que un webhook que llega dos veces (los reintentan todos:
    PayPal, Stripe, Binance) no cree dos Payment/active Subscription
    duplicadas — se busca por esto ANTES de crear, en cada handler de webhook."""
    result = await db.execute(
        select(Payment).where(Payment.provider == provider, Payment.external_reference == external_reference)
    )
    return result.scalars().first()


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Payment]:
    result = await db.execute(select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()))
    return list(result.scalars().all())


async def list_pending_verification(db: AsyncSession) -> list[Payment]:
    """La cola de Pago Móvil por revisar — trae el usuario ya cargado
    (el admin necesita ver a quién pertenece cada declaración de pago)."""
    result = await db.execute(
        select(Payment)
        .options(joinedload(Payment.user))
        .where(Payment.status == "pending_verification")
        .order_by(Payment.created_at)
    )
    return list(result.unique().scalars().all())


async def mark_approved(
    db: AsyncSession,
    payment: Payment,
    subscription_id: uuid.UUID,
    reviewed_by_id: uuid.UUID | None = None,
) -> Payment:
    """reviewed_by_id es None cuando aprueba un webhook automático
    (PayPal/Stripe/Binance), y el id del admin cuando es Pago Móvil
    revisado a mano — ver el comentario en el modelo Payment."""
    payment.status = "approved"
    payment.subscription_id = subscription_id
    payment.reviewed_by_id = reviewed_by_id
    payment.reviewed_at = func.now()
    await db.commit()
    await db.refresh(payment)
    return payment


async def mark_rejected(db: AsyncSession, payment: Payment, reviewed_by_id: uuid.UUID, reason: str) -> Payment:
    payment.status = "rejected"
    payment.reviewed_by_id = reviewed_by_id
    payment.reviewed_at = func.now()
    payment.payload = {**payment.payload, "rejection_reason": reason}
    await db.commit()
    await db.refresh(payment)
    return payment


async def mark_status(db: AsyncSession, payment: Payment, status: str) -> Payment:
    """Transición genérica para eventos de webhook que no son
    aprobación/rechazo humano (ej. "failed" cuando Stripe reporta una
    tarjeta rechazada, "refunded" cuando llega un reembolso)."""
    payment.status = status
    await db.commit()
    await db.refresh(payment)
    return payment
