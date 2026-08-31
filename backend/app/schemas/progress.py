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
