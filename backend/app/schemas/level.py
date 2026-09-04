import uuid

from pydantic import BaseModel, ConfigDict


class TutorOut(BaseModel):
    """Ficha pública del tutor de un nivel (GET /levels/{code}/tutor).

    Deliberadamente NO expone system_prompt ni model_id: son la receta
    pedagógica y la infraestructura, no información de alumno. El
    frontend solo necesita saber a quién le va a hablar, sin tener que
    abrir una sesión de chat (que crea una fila en base de datos) solo
    para averiguar un nombre.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    level_code: str


class CEFRLevelOut(BaseModel):
    """Lo que devuelve la API. Nunca exponemos el modelo SQLAlchemy
    directamente: este schema es el contrato público, independiente de
    cómo esté modelada la tabla por dentro."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    order: int
    description: str
    target_hours_min: int
    target_hours_max: int
