import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Exercise, Lesson, Module


async def get_for_lesson(
    db: AsyncSession, module_id: uuid.UUID, lesson_id: uuid.UUID, exercise_id: uuid.UUID
) -> Exercise | None:
    """Filtra por los tres ids (module/lesson/exercise), no solo por
    exercise_id: igual que lesson_repository.get_with_exercises, evita que
    una URL con ids "reales" pero de sitios distintos sirva contenido
    ajeno solo porque el UUID por sí solo era válido.

    Precarga la cadena lesson->module->level: la corrección de ejercicios
    abiertos necesita el nivel MCER para calibrar la exigencia, y así no
    hace falta una query aparte para conseguirlo.
    """
    result = await db.execute(
        select(Exercise)
        .join(Lesson, Exercise.lesson_id == Lesson.id)
        .options(joinedload(Exercise.lesson).joinedload(Lesson.module).joinedload(Module.level))
        .where(Exercise.id == exercise_id, Exercise.lesson_id == lesson_id, Lesson.module_id == module_id)
    )
    return result.scalars().first()
