from pydantic import BaseModel

from app.schemas.module import ModuleProgressOut


class CertificationProgressOut(BaseModel):
    """El mapa de progreso hacia certificar un nivel: rango de horas
    objetivo, cuántas lleva "certificadas" el alumno (proxy por
    mastery_score, ver enrollment_repository) y el estado de cada
    módulo — locked/available/in_progress/completed, en orden."""

    level_code: str
    target_hours_min: int
    target_hours_max: int
    hours_completed: float
    percentage: float  # hours_completed / target_hours_max * 100, redondeado
    modules: list[ModuleProgressOut]
