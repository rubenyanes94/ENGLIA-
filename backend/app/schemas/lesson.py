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


class LessonAdminOut(LessonSummaryOut):
    """Respuesta de crear/editar una lección desde admin: incluye el
    contenido pero NO `exercises` — esa relación no viene cargada tras un
    create/update, y forzar su lectura aquí rompería en async
    (MissingGreenlet). Para ver la lección completa, GET
    /modules/{id}/lessons/{id} (el endpoint público)."""

    content: dict


class LessonCreate(BaseModel):
    title: str
    content: dict = {}
    order: int


class LessonUpdate(BaseModel):
    title: str | None = None
    content: dict | None = None
    order: int | None = None
