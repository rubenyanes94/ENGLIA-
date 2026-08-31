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


async def get_by_id(db: AsyncSession, exercise_id: uuid.UUID) -> Exercise | None:
    """Existencia simple, para admin (editar/borrar) — sin la cadena de
    joinedload que sí necesita la corrección (get_for_lesson)."""
    return await db.get(Exercise, exercise_id)


async def create(
    db: AsyncSession, lesson_id: uuid.UUID, exercise_type: str, stage: str, prompt: str, answer_key: dict
) -> Exercise:
    exercise = Exercise(
        lesson_id=lesson_id, exercise_type=exercise_type, stage=stage, prompt=prompt, answer_key=answer_key
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    return exercise


async def update(
    db: AsyncSession,
    exercise: Exercise,
    exercise_type: str | None = None,
    stage: str | None = None,
    prompt: str | None = None,
    answer_key: dict | None = None,
) -> Exercise:
    if exercise_type is not None:
        exercise.exercise_type = exercise_type
    if stage is not None:
        exercise.stage = stage
    if prompt is not None:
        exercise.prompt = prompt
    if answer_key is not None:
        exercise.answer_key = answer_key

    await db.commit()
    await db.refresh(exercise)
    return exercise


async def delete(db: AsyncSession, exercise: Exercise) -> None:
    await db.delete(exercise)
    await db.commit()
