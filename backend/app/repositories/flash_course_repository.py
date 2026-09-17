import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models import FlashCourse, FlashCourseProgress


async def list_all(db: AsyncSession) -> list[FlashCourse]:
    result = await db.execute(select(FlashCourse).order_by(FlashCourse.order, FlashCourse.title_es))
    return list(result.scalars().all())


async def get_by_slug(db: AsyncSession, slug: str) -> FlashCourse | None:
    result = await db.execute(select(FlashCourse).where(FlashCourse.slug == slug))
    return result.scalars().first()


async def progress_by_course(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, FlashCourseProgress]:
    """Todo el progreso del alumno en la Biblioteca, en una consulta: la
    portada pinta el avance de cada tarjeta y pedirlo curso a curso sería
    una consulta por tarjeta."""
    result = await db.execute(select(FlashCourseProgress).where(FlashCourseProgress.user_id == user_id))
    return {progress.course_id: progress for progress in result.scalars()}


async def mark_scenario_completed(
    db: AsyncSession, user_id: uuid.UUID, course: FlashCourse, scenario_id: str
) -> FlashCourseProgress:
    """Marca un escenario como logrado. Idempotente: repetir un escenario
    ya logrado no lo duplica ni mueve la fecha de finalización."""
    result = await db.execute(
        select(FlashCourseProgress).where(
            FlashCourseProgress.user_id == user_id, FlashCourseProgress.course_id == course.id
        )
    )
    progress = result.scalars().first()
    if progress is None:
        progress = FlashCourseProgress(user_id=user_id, course_id=course.id, completed_scenarios=[])
        db.add(progress)

    if scenario_id not in progress.completed_scenarios:
        # Lista nueva y no .append(): SQLAlchemy no detecta cambios DENTRO
        # de un ARRAY, solo que se asigna uno distinto.
        progress.completed_scenarios = [*progress.completed_scenarios, scenario_id]

    all_ids = {scenario["id"] for scenario in course.scenarios}
    if progress.completed_at is None and all_ids and all_ids.issubset(progress.completed_scenarios):
        progress.completed_at = func.now()

    await db.commit()
    await db.refresh(progress)
    return progress
