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


class ModuleCreate(BaseModel):
    level_code: str
    title: str
    skill_focus: str
    order: int


class ModuleUpdate(BaseModel):
    """Todo opcional: PATCH parcial — solo se actualizan los campos
    enviados. No incluye level_code a propósito: mover un módulo entre
    niveles arrastraría inscripciones/progreso de alumnos ya hechas
    contra ese nivel; si hace falta, que sea una operación explícita
    aparte, no un efecto secundario de "editar el título"."""

    title: str | None = None
    skill_focus: str | None = None
    order: int | None = None
