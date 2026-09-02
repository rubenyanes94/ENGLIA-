import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.lesson import LessonSummaryOut


class ModuleOut(BaseModel):
    """Lo que se ve al listar los módulos de un nivel (incluida la
    certificación): sin lecciones ni el contenido "denso" (l1_interference,
    tasks, tutor_config) — eso es un fetch aparte vía ModuleDetailOut. Sí
    trae lo suficiente para pintar una tarjeta de módulo con sentido:
    título en ambos idiomas, objetivos y qué descriptores MCER desarrolla."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str | None
    title: str
    title_es: str | None
    skill_focus: str
    order: int
    estimated_hours: float
    descriptors: list[str]
    communicative_objectives: list[str]


class ModuleDetailOut(ModuleOut):
    """Lo que se ve al abrir UN módulo: el resto de la anatomía curricular
    (MCER § 3) — gramática, léxico, pronunciación, interferencia L1,
    tareas comunicativas y el contrato de comportamiento del tutor — más
    el índice de lecciones (solo el resumen, no su contenido)."""

    recycles: list[str]
    grammar: dict
    lexis: dict
    pronunciation: dict
    l1_interference: list[dict]
    tasks: list[dict]
    assessment: dict
    tutor_config: dict
    lessons: list[LessonSummaryOut]


class ModuleProgressOut(ModuleOut):
    """Lo que se ve en el mapa de progreso de un nivel (GET
    /levels/{code}/certification-progress): igual que ModuleOut, más el
    estado personalizado para EL ALUMNO que pide esto — no viene del
    modelo (por eso no hereda `from_attributes`, se construye a mano en
    el router), es el resultado de cruzar Module con su Enrollment."""

    status: str  # "locked" | "available" | "in_progress" | "completed"


class ModuleCreate(BaseModel):
    """Alta de módulo desde el admin: solo los campos "básicos". El
    contenido curricular rico (descriptors, l1_interference, tasks,
    tutor_config...) todavía no tiene formulario de autoría — hoy entra
    por script de seed (ver app/scripts/seed_a1_modules.py), no por API."""

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
