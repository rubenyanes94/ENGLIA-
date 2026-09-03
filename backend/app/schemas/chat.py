import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    level_code: str = Field(examples=["A1"])
    # Módulo que el alumno va a practicar en esta sesión — opcional: sin
    # él, la sesión es chat libre del nivel (comportamiento anterior, sin
    # cambios). Con él, el tutor aplica tutor_config/l1_interference de
    # ESE módulo (ver app/agents/prompt_builder.py) y se pueden marcar
    # tareas activas turno a turno (ver SendMessageRequest.task_id).
    module_id: uuid.UUID | None = None


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    persona_name: str
    level_code: str
    module_title: str | None = None


class SendMessageRequest(BaseModel):
    message: str = Field(examples=["Hello! How do I say 'buenos días'?"])
    # id de una tarea de Module.tasks (ej. "a1-01-t1") que el alumno está
    # practicando EN ESTE turno — requiere que la sesión tenga módulo
    # (ver CreateSessionRequest.module_id). Si se manda, el tutor evalúa
    # si el turno cumple la tarea y, de ser así, registra evidencia hacia
    # el descriptor MCER que esa tarea declara (ver routers/chat.py).
    task_id: str | None = None


class CorrectionItem(BaseModel):
    error: str
    correction: str
    rule: str


class SendMessageResponse(BaseModel):
    session_id: uuid.UUID
    reply: str
    persona_name: str
    corrections: list[CorrectionItem] = []
    # None si el turno no tenía tarea activa (no se envió task_id); si la
    # tenía, dice si el tutor consideró que el alumno la cumplió en este turno.
    task_completed: bool | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime
    corrections: list[CorrectionItem] | None = None


class EndSessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str = "ended"
