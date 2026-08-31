import uuid
from datetime import datetime

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


async def get_by_id(db: AsyncSession, lesson_id: uuid.UUID) -> Lesson | None:
    """Existencia simple, sin relaciones — para admin (editar/borrar),
    donde no hace falta la lista de ejercicios."""
    return await db.get(Lesson, lesson_id)


async def create(db: AsyncSession, module_id: uuid.UUID, title: str, content: dict, order: int) -> Lesson:
    lesson = Lesson(module_id=module_id, title=title, content=content, order=order)
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def update(
    db: AsyncSession,
    lesson: Lesson,
    title: str | None = None,
    content: dict | None = None,
    order: int | None = None,
) -> Lesson:
    if title is not None:
        lesson.title = title
    if content is not None:
        lesson.content = content
    if order is not None:
        lesson.order = order

    await db.commit()
    await db.refresh(lesson)
    return lesson


async def delete(db: AsyncSession, lesson: Lesson) -> None:
    await db.delete(lesson)
    await db.commit()


async def set_narration(db: AsyncSession, lesson: Lesson, script: str, audio_url: str, audio_duration_seconds: float) -> Lesson:
    """Lo llama el router de admin tras generar el guión (Ollama) y el
    audio (Piper) — separado de `update()` porque conceptualmente es un
    resultado de un pipeline, no un campo que un admin edita a mano
    directamente."""
    lesson.script = script
    lesson.audio_url = audio_url
    lesson.audio_duration_seconds = audio_duration_seconds
    lesson.audio_generated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(lesson)
    return lesson
