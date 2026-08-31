import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Lesson


async def get_with_exercises(db: AsyncSession, module_id: uuid.UUID, lesson_id: uuid.UUID) -> Lesson | None:
    """Filtramos también por module_id, no solo por lesson_id: así una
    URL como /modules/{A}/lessons/{lección-de-B} da 404 en vez de servir
    la lección igual solo porque el UUID por sí solo era válido."""
    result = await db.execute(
        select(Lesson)
        .options(joinedload(Lesson.exercises))
        .where(Lesson.id == lesson_id, Lesson.module_id == module_id)
    )
    return result.unique().scalars().first()
