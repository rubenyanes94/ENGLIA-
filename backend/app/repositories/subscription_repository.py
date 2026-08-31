import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from app.models import Plan, Subscription

# Pasarelas que SÍ cobran solas cada mes (tienen "suscripción" real del
# lado del proveedor). Las otras dos (Binance Pay, Pago Móvil) no tienen
# forma de cargar una tarjeta/cuenta sin intervención del alumno — cada
# período es un pago nuevo que él inicia.
AUTO_RENEWING_PROVIDERS = {"paypal", "credit_card"}

# 30 días en vez de "un mes calendario exacto" — simplificación deliberada
# para no añadir python-dateutil solo por esto. La usan tanto los
# webhooks (renovación automática) como la aprobación manual de Pago
# Móvil, para que un mes pagado dure lo mismo sin importar la pasarela.
BILLING_PERIOD = timedelta(days=30)


async def get_active(db: AsyncSession, user_id: uuid.UUID) -> Subscription | None:
    """La suscripción vigente AHORA, si existe. Comprobamos status Y
    current_period_end (no solo status) a propósito: todavía no hay un
    job que marque "expired" en el instante exacto en que vence una
    suscripción sin auto-renovación (Binance Pay/Pago Móvil) — así que
    "active" en la BD puede estar desactualizado, pero la fecha no miente."""
    result = await db.execute(
        select(Subscription)
        .options(joinedload(Subscription.plan))
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            (Subscription.current_period_end.is_(None)) | (Subscription.current_period_end >= func.now()),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def get_by_id(db: AsyncSession, subscription_id: uuid.UUID) -> Subscription | None:
    return await db.get(Subscription, subscription_id)


async def get_by_provider_subscription_id(db: AsyncSession, provider: str, provider_subscription_id: str) -> Subscription | None:
    """Para cruzar un webhook (que solo trae el id del lado del
    proveedor) contra nuestra fila."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.provider == provider,
            Subscription.provider_subscription_id == provider_subscription_id,
        )
    )
    return result.scalars().first()


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Subscription]:
    result = await db.execute(
        select(Subscription)
        .options(joinedload(Subscription.plan))
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
    )
    return list(result.unique().scalars().all())


async def create_pending(db: AsyncSession, user_id: uuid.UUID, plan: Plan, provider: str) -> Subscription:
    subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        provider=provider,
        status="pending",
        auto_renew=provider in AUTO_RENEWING_PROVIDERS,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def activate(
    db: AsyncSession,
    subscription: Subscription,
    period_start: datetime,
    period_end: datetime,
    provider_subscription_id: str | None = None,
) -> Subscription:
    subscription.status = "active"
    subscription.current_period_start = period_start
    subscription.current_period_end = period_end
    if provider_subscription_id is not None:
        subscription.provider_subscription_id = provider_subscription_id

    await db.commit()
    await db.refresh(subscription)
    return subscription


async def cancel(db: AsyncSession, subscription: Subscription) -> Subscription:
    subscription.status = "canceled"
    subscription.canceled_at = func.now()
    await db.commit()
    await db.refresh(subscription)
    return subscription
