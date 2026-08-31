import uuid

from pydantic import BaseModel


class ProgressModuleOut(BaseModel):
    """A diferencia de EnrollmentOut, este ya trae aplanados el título del
    módulo y el código del nivel — así el frontend no tiene que hacer un
    segundo fetch por cada módulo solo para pintar una lista de progreso."""

    module_id: uuid.UUID
    module_title: str
    level_code: str
    status: str
    mastery_score: float


class ProgressOut(BaseModel):
    current_level_code: str | None
    modules: list[ProgressModuleOut]


class SkillBreakdownOut(BaseModel):
    """Porcentajes 0-100 por destreza CEFR (listening/speaking/reading/
    writing), solo entre las que ya tienen al menos una inscripción —
    ver enrollment_repository.get_skill_breakdown. `average` es el
    promedio de esas destrezas, no de TODAS las posibles."""

    skills: dict[str, float]
    average: float
