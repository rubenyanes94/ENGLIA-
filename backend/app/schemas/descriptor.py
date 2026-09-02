import uuid

from pydantic import BaseModel, ConfigDict


class DescriptorOut(BaseModel):
    """El catálogo tal cual (GET /levels/{code}/descriptors): sin nada
    personalizado por alumno — eso es DescriptorMasteryOut, aparte."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    skill: str
    statement_en: str
    statement_es: str
    modules: list[str]
    priority: str | None
    l1_specific: bool
    note: str | None
    target: str | None


class DescriptorMasteryOut(BaseModel):
    """Un descriptor + el dominio acumulado del alumno autenticado sobre
    él (GET /users/me/progress/descriptors/{level_code}) — construido a
    mano cruzando Descriptor con descriptor_evidence_repository, no viene
    de un solo modelo (por eso no hereda from_attributes)."""

    code: str
    skill: str
    statement_es: str
    priority: str | None
    mastery: float  # 0.0 - threshold (0.8 en A1)
    is_mastered: bool  # mastery >= threshold del nivel


class DescriptorMasterySummaryOut(BaseModel):
    """Resumen agregado para pintar un solo número/barra (ej. "18/35
    descriptores dominados") sin que el frontend tenga que recorrer la
    lista completa — mismo espíritu que SkillBreakdownOut."""

    level_code: str
    threshold: float
    total: int
    mastered: int
    percentage: float  # mastered / total * 100, redondeado
    descriptors: list[DescriptorMasteryOut]


class ExitCriterionOut(BaseModel):
    """Un criterio del gate de salida de nivel (Module.assessment.
    level_exit_criteria, en texto libre) ya EVALUADO para el alumno que
    llama. `detail` trae los números crudos detrás de `met`, para que el
    frontend pueda explicar por qué falta (ej. qué descriptores critical
    siguen sin dominar) sin que el backend tenga que redactar el mensaje."""

    key: str  # "critical_descriptors_mastered" | "descriptor_mastery_ratio" | "exit_tasks_completed"
    label: str
    met: bool
    detail: dict


class LevelExitGateOut(BaseModel):
    """¿Puede este alumno certificar el nivel? `eligible` es el AND de
    todos los criterios — no hay certificación parcial: como con
    mastery_rule (documento § 1.6), una condición sin cumplir basta para
    que el nivel no esté listo."""

    level_code: str
    eligible: bool
    criteria: list[ExitCriterionOut]
