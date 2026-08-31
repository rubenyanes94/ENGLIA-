import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Module(Base):
    """Un módulo temático dentro de un nivel MCER (ej.: "Presentarse", dentro de A1)."""

    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cefr_levels.id"))
    title: Mapped[str] = mapped_column(String(255))
    skill_focus: Mapped[str] = mapped_column(String(50))  # listening|speaking|grammar|vocabulary|writing
    order: Mapped[int] = mapped_column(Integer)

    level: Mapped["CEFRLevel"] = relationship(back_populates="modules")
    # order_by aquí (no en cada query): así "lessons" viene ordenado sin
    # importar desde dónde se cargue la relación.
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", order_by="Lesson.order")

    def __repr__(self) -> str:
        return f"<Module {self.title}>"
