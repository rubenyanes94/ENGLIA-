import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"))
    exercise_type: Mapped[str] = mapped_column(String(30))  # multiple_choice|fill_blank|speaking|writing

    # Códigos de Descriptor (ej. "A1.SI.02") que este ejercicio evidencia.
    # Nullable/vacío por defecto: un ejercicio de práctica genérico puede
    # no atarse a ningún descriptor — solo los que SÍ lo declaran alimentan
    # descriptor_evidence al calificarse (ver routers/modules.py).
    descriptor_codes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # "practice": ensayo libre, intentos ilimitados, NO cuenta para
    #   mastery_score — el alumno puede fallar sin que le baje el progreso.
    # "exam": SÍ cuenta para mastery_score/completar el módulo (ver
    #   enrollment_repository.recompute_mastery, que ahora solo promedia
    #   ejercicios de este stage).
    stage: Mapped[str] = mapped_column(String(10), default="practice")

    prompt: Mapped[str] = mapped_column(Text)
    answer_key: Mapped[dict] = mapped_column(JSONB)

    lesson: Mapped["Lesson"] = relationship(back_populates="exercises")

    def __repr__(self) -> str:
        return f"<Exercise {self.exercise_type}>"


class ExerciseAttempt(Base):
    """Cada intento de un alumno sobre un ejercicio, con la corrección/
    feedback que generó el agente IA (no solo la nota numérica)."""

    __tablename__ = "exercise_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercises.id"))
    response: Mapped[dict] = mapped_column(JSONB)
    score: Mapped[float] = mapped_column(Float)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship()
    exercise: Mapped["Exercise"] = relationship()

    def __repr__(self) -> str:
        return f"<ExerciseAttempt score={self.score}>"
