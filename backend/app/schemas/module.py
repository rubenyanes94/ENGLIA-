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
    estimated_hours: float


class ModuleDetailOut(ModuleOut):
    """Lo que se ve al abrir UN módulo: ya con su índice de lecciones
    (solo el resumen de cada una, no su contenido — eso es un fetch aparte)."""

    lessons: list[LessonSummaryOut]


class ModuleProgressOut(ModuleOut):
    """Lo que se ve en el mapa de progreso de un nivel (GET
    /levels/{code}/certification-progress): igual que ModuleOut, más el
    estado personalizado para EL ALUMNO que pide esto — no viene del
    modelo (por eso no hereda `from_attributes`, se construye a mano en
    el router), es el resultado de cruzar Module con su Enrollment."""

    status: str  # "locked" | "available" | "in_progress" | "completed"


class ModuleCreate(BaseModel):
    level_code: str
    title: str
    skill_focus: str
    order: int
    estimated_hours: float = 10.0


class ModuleUpdate(BaseModel):
    """Todo opcional: PATCH parcial — solo se actualizan los campos
    enviados. No incluye level_code a propósito: mover un módulo entre
    niveles arrastraría inscripciones/progreso de alumnos ya hechas
    contra ese nivel; si hace falta, que sea una operación explícita
    aparte, no un efecto secundario de "editar el título"."""

    title: str | None = None
    skill_focus: str | None = None
    order: int | None = None
    estimated_hours: float | None = None
