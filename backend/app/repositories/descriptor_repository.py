import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CEFRLevel, Descriptor


async def list_by_level_code(db: AsyncSession, level_code: str) -> list[Descriptor]:
    result = await db.execute(
        select(Descriptor).join(CEFRLevel).where(CEFRLevel.code == level_code.upper()).order_by(Descriptor.code)
    )
    return list(result.scalars().all())


async def get_by_code(db: AsyncSession, code: str) -> Descriptor | None:
    result = await db.execute(select(Descriptor).where(Descriptor.code == code))
    return result.scalars().first()


async def list_codes_by_level_id(db: AsyncSession, level_id: uuid.UUID) -> list[str]:
    """Solo los códigos (sin cargar el objeto completo) — es lo único que
    necesita descriptor_evidence_repository.get_mastery_for_level para
    saber qué descriptores computar."""
    result = await db.execute(select(Descriptor.code).where(Descriptor.level_id == level_id))
    return [row[0] for row in result.all()]
