"""Siembra el plan único de suscripción: $10/mes, acceso a todo el contenido.

Uso:
    python -m app.scripts.seed_plans

Idempotente: si "premium_monthly" ya existe, no hace nada.
"""

import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import Plan


async def seed_plans() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Plan).where(Plan.code == "premium_monthly"))
        if result.scalars().first() is not None:
            print("El plan 'premium_monthly' ya existía. Nada que insertar.")
            return

        plan = Plan(
            code="premium_monthly",
            name="Premium Mensual",
            price_cents=1000,  # $10.00 — nunca en float, ver comentario en el modelo
            currency="USD",
            interval="month",
            is_active=True,
        )
        session.add(plan)
        await session.commit()
        print(f"Plan creado: {plan.name} (${plan.price_cents / 100:.2f}/{plan.interval})")


if __name__ == "__main__":
    asyncio.run(seed_plans())
