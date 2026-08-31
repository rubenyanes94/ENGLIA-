import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plan


async def list_active(db: AsyncSession) -> list[Plan]:
    result = await db.execute(select(Plan).where(Plan.is_active.is_(True)))
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    return await db.get(Plan, plan_id)


async def get_by_code(db: AsyncSession, code: str) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.code == code))
    return result.scalars().first()


async def update_gateway_ids(
    db: AsyncSession,
    plan: Plan,
    stripe_price_id: str | None = None,
    paypal_plan_id: str | None = None,
) -> Plan:
    """Para cuando un admin da de alta el Product/Price de Stripe o el
    Product/Plan de PayPal del lado del proveedor y necesita pegar aquí
    el id resultante — ninguna de las dos pasarelas deja crear ese
    objeto "al vuelo" en cada checkout, es un paso previo manual."""
    if stripe_price_id is not None:
        plan.stripe_price_id = stripe_price_id
    if paypal_plan_id is not None:
        plan.paypal_plan_id = paypal_plan_id

    await db.commit()
    await db.refresh(plan)
    return plan
