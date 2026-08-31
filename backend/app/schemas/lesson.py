import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.exercise import ExerciseOut


class LessonSummaryOut(BaseModel):
    """Lo que se ve al listar las lecciones de un módulo: sin `content`
    (puede ser JSON pesado) ni ejercicios, solo para armar el índice."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    order: int


class LessonDetailOut(LessonSummaryOut):
    """Lo que se ve al abrir UNA lección: ya con el contenido y los
    ejercicios (sin sus respuestas, ver ExerciseOut)."""

    content: dict
    exercises: list[ExerciseOut]
