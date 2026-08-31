import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.exercise import ExerciseOut


class LessonSummaryOut(BaseModel):
    """Lo que se ve al listar las lecciones de un módulo: sin `content`
    (puede ser JSON pesado) ni ejercicios, solo para armar el índice.
    `audio_duration_seconds` sí va aquí (es un float suelto, barato) —
    útil para pintar duraciones en el índice sin pedir cada lección entera."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    order: int
    audio_duration_seconds: float | None


class LessonDetailOut(LessonSummaryOut):
    """Lo que se ve al abrir UNA lección: ya con el contenido, el audio
    narrado (si existe) y los ejercicios (sin sus respuestas, ver ExerciseOut).

    `script` SÍ se expone (a diferencia de `answer_key` en ExerciseOut):
    es el texto de lo que James está diciendo, útil como subtítulos/
    transcripción — no es información que deba ocultarse del alumno."""

    content: dict
    script: str | None
    audio_url: str | None
    exercises: list[ExerciseOut]


class LessonAdminOut(LessonSummaryOut):
    """Respuesta de crear/editar una lección desde admin: incluye el
    contenido y el estado de la narración, pero NO `exercises` — esa
    relación no viene cargada tras un create/update, y forzar su lectura
    aquí rompería en async (MissingGreenlet). Para ver la lección
    completa, GET /modules/{id}/lessons/{id} (el endpoint público)."""

    content: dict
    script: str | None
    audio_url: str | None


class LessonCreate(BaseModel):
    title: str
    content: dict = {}
    order: int

    # Para la narración de James — ambos opcionales, y mutuamente
    # excluyentes en la práctica (ver el router): si mandas `script`, se
    # usa tal cual (sin pasar por el LLM); si mandas `topic`, el LLM
    # genera el guión a partir de ese tema. Si no mandas ninguno, la
    # lección queda sin audio (ej. una lección puramente de lectura).
    topic: str | None = None
    script: str | None = None


class LessonUpdate(BaseModel):
    title: str | None = None
    content: dict | None = None
    order: int | None = None
    topic: str | None = None
    script: str | None = None
