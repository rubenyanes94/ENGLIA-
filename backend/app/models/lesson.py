import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Lesson(Base):
    """Una lección concreta dentro de un módulo. El contenido va en JSONB
    a propósito: cada lección puede tener una forma distinta (texto,
    audio, preguntas) sin obligarnos a migrar el esquema cada vez.

    `script`/`audio_*` son columnas propias (no parte de `content`) a
    propósito: son el resultado de un pipeline real (Ollama genera el
    guión → Piper TTS lo narra → se guarda el archivo), no contenido
    libre que un admin escribe a mano — ameritan un contrato tipado, no
    quedar enterrados en un JSONB genérico.
    """

    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("modules.id"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    order: Mapped[int] = mapped_column(Integer)

    # El guión que James narra — generado por el LLM a partir de un
    # "topic" (o escrito a mano por un admin, si lo prefiere). Nullable:
    # no toda lección necesita audio (ej. una lección puramente de lectura).
    script: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Para saber si el audio quedó desactualizado respecto al script
    # (ej. un admin editó el guión pero la regeneración falló) — no se
    # usa todavía para invalidar nada automáticamente, pero es la señal
    # que necesitaríamos para hacerlo.
    audio_generated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    module: Mapped["Module"] = relationship(back_populates="lessons")
    exercises: Mapped[list["Exercise"]] = relationship(back_populates="lesson")

    def __repr__(self) -> str:
        return f"<Lesson {self.title}>"
