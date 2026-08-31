import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AgentPersona(Base):
    """Configuración de un tutor IA para un nivel MCER concreto.

    Vive en base de datos (no hardcodeada en el código) a propósito: así
    podemos ajustar el prompt de un tutor de nivel B1, o cambiarlo de
    modelo, con un simple UPDATE y sin necesidad de desplegar código.
    `prompt_version` deja rastro de qué versión del prompt generó cada
    conversación pasada.
    """

    __tablename__ = "agent_personas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cefr_levels.id"))
    name: Mapped[str] = mapped_column(String(100))  # ej. "Tutor Emma"
    system_prompt: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[int] = mapped_column(Integer, default=1)
    model_id: Mapped[str] = mapped_column(String(255))  # ej. "meta-llama/Llama-3.1-8B-Instruct"
    temperature: Mapped[float] = mapped_column(Float, default=0.6)
    is_active: Mapped[bool] = mapped_column(default=True)

    level: Mapped["CEFRLevel"] = relationship(back_populates="personas")

    def __repr__(self) -> str:
        return f"<AgentPersona {self.name} (v{self.prompt_version})>"
