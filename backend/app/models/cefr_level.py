import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class CEFRLevel(Base):
    """Catálogo FIJO de los 6 niveles del Marco Común Europeo de Referencia
    (A1, A2, B1, B2, C1, C2). Se siembra una única vez; no lo edita el usuario."""

    __tablename__ = "cefr_levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(2), unique=True, index=True)  # "A1".."C2"
    name: Mapped[str] = mapped_column(String(50))  # "Acceso", "Plataforma", "Maestría"...
    order: Mapped[int] = mapped_column(Integer, unique=True)  # 1..6, define la progresión
    description: Mapped[str] = mapped_column(Text)

    modules: Mapped[list["Module"]] = relationship(back_populates="level")
    personas: Mapped[list["AgentPersona"]] = relationship(back_populates="level")

    def __repr__(self) -> str:
        return f"<CEFRLevel {self.code}>"
