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
