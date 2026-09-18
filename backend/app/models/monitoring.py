"""Registro técnico para el panel de gerencia → Sistema.

Tres tablas "de telemetría", aparte de las de negocio a propósito: se
escriben muchísimo, se leen agregadas y se podan pasados unos días (ver
app/monitoring/retention.py). Ninguna guarda contenido de alumnos: de una
llamada al modelo se guarda cuánto tardó y cuántos tokens gastó, nunca el
prompt ni la respuesta.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class LLMCall(Base):
    """Un INTENTO de llamada a un modelo (chat, embeddings o voz).

    Un reintento es una fila más con el mismo `call_id`: así se puede
    distinguir "falló y se recuperó al reintentar" (el alumno no lo notó)
    de "falló del todo" (al alumno le llegó un error)."""

    __tablename__ = "llm_calls"
    __table_args__ = (Index("ix_llm_calls_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    # chat | embedding | tts
    operation: Mapped[str] = mapped_column(String(20))
    # Para qué se llamó: tutor_reply, corrections, moderation... (ver
    # app/monitoring/llm_metrics.py). Es lo que dice QUÉ parte de la app es lenta.
    purpose: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(10))  # ok | error
    latency_ms: Mapped[int] = mapped_column(Integer)
    # Tiempo esperando turno en el semáforo de inferencia antes de llamar.
    queue_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Voz: no hay tokens; se mide en caracteres narrados.
    input_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "length" = la respuesta se cortó por max_tokens.
    finish_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RequestLog(Base):
    """Una petición HTTP a la API: ruta (la plantilla, no la URL con ids),
    código de respuesta y duración. Si reventó con una excepción, su tipo
    y las últimas líneas del traceback."""

    __tablename__ = "request_logs"
    __table_args__ = (Index("ix_request_logs_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    method: Mapped[str] = mapped_column(String(10))
    route: Mapped[str] = mapped_column(String(200))
    status_code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class ClientError(Base):
    """Un error de JavaScript en el navegador de un usuario: lo único que
    el servidor no ve por sí mismo (una pantalla en blanco no deja rastro
    en ningún log del backend)."""

    __tablename__ = "client_errors"
    __table_args__ = (Index("ix_client_errors_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(String(30))  # error | unhandledrejection
    message: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    in_app: Mapped[bool] = mapped_column(Boolean, default=True)
