import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.lesson import LessonSummaryOut


class ModuleOut(BaseModel):
    """Lo que se ve al listar los módulos de un nivel: sin lecciones."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    skill_focus: str
    order: int


class ModuleDetailOut(ModuleOut):
    """Lo que se ve al abrir UN módulo: ya con su índice de lecciones
    (solo el resumen de cada una, no su contenido — eso es un fetch aparte)."""

    lessons: list[LessonSummaryOut]
