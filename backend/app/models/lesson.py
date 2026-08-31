import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Lesson(Base):
    """Una lección concreta dentro de un módulo. El contenido va en JSONB
    a propósito: cada lección puede tener una forma distinta (texto,
    audio, preguntas) sin obligarnos a migrar el esquema cada vez."""

    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("modules.id"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    order: Mapped[int] = mapped_column(Integer)

    module: Mapped["Module"] = relationship(back_populates="lessons")
    exercises: Mapped[list["Exercise"]] = relationship(back_populates="lesson")

    def __repr__(self) -> str:
        return f"<Lesson {self.title}>"
