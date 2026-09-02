import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CEFRLevel


async def list_levels(db: AsyncSession) -> list[CEFRLevel]:
    """El repositorio es la ÚNICA capa que sabe escribir SQL/ORM.
    Routers y services nunca importan `select`/`CEFRLevel` directamente:
    así, si mañana cambiamos de ORM o añadimos caché, solo tocamos aquí."""
    result = await db.execute(select(CEFRLevel).order_by(CEFRLevel.order))
    return list(result.scalars().all())


async def get_by_code(db: AsyncSession, code: str) -> CEFRLevel | None:
    result = await db.execute(select(CEFRLevel).where(CEFRLevel.code == code.upper()))
    return result.scalars().first()


async def get_by_id(db: AsyncSession, level_id: uuid.UUID) -> CEFRLevel | None:
    return await db.get(CEFRLevel, level_id)


async def get_by_order(db: AsyncSession, order: int) -> CEFRLevel | None:
    """El nivel EN esa posición de la progresión (1..6) — lo usa la
    certificación (routers/users.py, certify_level) para encontrar "el
    siguiente nivel" tras certificar uno. None si `order` se sale del
    rango (ej. pedir el siguiente de C2, que ya es el último)."""
    result = await db.execute(select(CEFRLevel).where(CEFRLevel.order == order))
    return result.scalars().first()
