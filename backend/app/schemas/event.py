import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventIn(BaseModel):
    """`event_type` es texto libre a propósito (ver el modelo UserEvent:
    esta tabla existe PARA registrar cosas que todavía no sabemos que
    vamos a necesitar). Convención: snake_case, verbo en pasado — ej.
    "video_played", "lesson_opened", "app_backgrounded". Consistente con
    los eventos que ya emite el propio backend (ver las llamadas a
    event_repository.record() en routers/modules.py y routers/chat.py)."""

    event_type: str
    payload: dict = {}


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    payload: dict
    created_at: datetime
