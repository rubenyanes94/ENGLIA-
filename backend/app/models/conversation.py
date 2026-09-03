import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base

# Dimensión del modelo de embeddings (nomic-embed-text, servido vía
# Ollama — el mismo motor que el LLM del tutor). Si cambiamos de modelo
# de embeddings más adelante, este valor cambia y toca una migración nueva.
EMBEDDING_DIM = 768


class ConversationSession(Base):
    """Una sesión de chat entre un alumno y su tutor IA.

    `summary` + `summary_embedding` son la memoria de LARGO plazo del
    agente (persistida en Postgres vía pgvector): al cerrar la sesión, un
    worker de Celery resume la conversación y genera su embedding, para
    que sesiones futuras puedan recuperar "de qué hablamos la última vez"
    por similitud semántica, sin cargar el historial completo en el prompt.
    """

    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    persona_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_personas.id"))

    # Módulo que el alumno está practicando en esta sesión — nullable:
    # una sesión de chat libre (sin módulo) sigue siendo válida, solo que
    # el tutor no aplica tutor_config/l1_interference de ningún módulo ni
    # puede evaluar tareas (ver app/agents/prompt_builder.py y
    # routers/chat.py). Se fija al ABRIR la sesión, no cambia después:
    # practicar otro módulo es abrir otra sesión.
    module_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("modules.id"), nullable=True)

    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    user: Mapped["User"] = relationship()
    persona: Mapped["AgentPersona"] = relationship()
    module: Mapped["Module | None"] = relationship()
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="session", order_by="ConversationMessage.created_at"
    )

    def __repr__(self) -> str:
        return f"<ConversationSession {self.id}>"


class ConversationMessage(Base):
    """Un turno individual (usuario o tutor) dentro de una sesión.
    Es la memoria de CORTO plazo persistida; la copia "en caliente" de la
    conversación activa vive en Redis mientras la sesión está abierta."""

    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))  # user|assistant|system
    content: Mapped[str] = mapped_column(Text)

    # Errores detectados por el agente en ESTE mensaje (solo aplica a
    # mensajes de role="user"), ej.:
    # [{"error": "he go", "correction": "he goes", "rule": "..."}]
    corrections: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    session: Mapped["ConversationSession"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<ConversationMessage {self.role}>"
