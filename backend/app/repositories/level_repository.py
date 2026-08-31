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
