import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    level_code: str = Field(examples=["A1"])


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    persona_name: str
    level_code: str


class SendMessageRequest(BaseModel):
    message: str = Field(examples=["Hello! How do I say 'buenos días'?"])


class CorrectionItem(BaseModel):
    error: str
    correction: str
    rule: str


class SendMessageResponse(BaseModel):
    session_id: uuid.UUID
    reply: str
    persona_name: str
    corrections: list[CorrectionItem] = []


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime
    corrections: list[CorrectionItem] | None = None


class EndSessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str = "ended"
