import uuid

from pydantic import BaseModel, ConfigDict


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
