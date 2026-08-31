import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExerciseAttempt


async def create(
    db: AsyncSession,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    answer: str,
    score: float,
    feedback: str,
) -> ExerciseAttempt:
    # `response` es JSONB a propósito (ver el modelo): guardamos {"answer": ...}
    # en vez de una columna de texto plana para poder añadir más adelante
    # otros campos (ej. audio_url en ejercicios de speaking) sin migración.
    attempt = ExerciseAttempt(
        user_id=user_id,
        exercise_id=exercise_id,
        response={"answer": answer},
        score=score,
        ai_feedback=feedback,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


async def list_for_exercise(db: AsyncSession, user_id: uuid.UUID, exercise_id: uuid.UUID) -> list[ExerciseAttempt]:
    """Solo los intentos del PROPIO alumno — nunca de otros, ni con un
    parámetro para pedirlo, por diseño (mismo criterio que _get_owned_session
    en chat.py: cada quien ve sus propios intentos, punto)."""
    result = await db.execute(
        select(ExerciseAttempt)
        .where(ExerciseAttempt.user_id == user_id, ExerciseAttempt.exercise_id == exercise_id)
        .order_by(ExerciseAttempt.attempted_at)
    )
    return list(result.scalars().all())
