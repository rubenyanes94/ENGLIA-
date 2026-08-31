import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Module(Base):
    """Un módulo temático dentro de un nivel MCER (ej.: "Presentarse", dentro de A1)."""

    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cefr_levels.id"))
    title: Mapped[str] = mapped_column(String(255))
    # Las 4 destrezas CEFR estándar (listening|speaking|reading|writing) —
    # es la dimensión sobre la que se agrega el desglose de habilidades
    # del alumno (ver enrollment_repository.get_skill_breakdown). Un
    # módulo de gramática o vocabulario se clasifica bajo la destreza que
    # más practica (ej.: gramática de tiempos verbales -> "writing").
    skill_focus: Mapped[str] = mapped_column(String(50))
    order: Mapped[int] = mapped_column(Integer)

    # "Peso" en horas de este módulo dentro del total de certificación del
    # nivel (CEFRLevel.target_hours_*). Las horas "certificadas" de un
    # alumno en este módulo = estimated_hours * su mastery_score — es un
    # PROXY del progreso, no tiempo real cronometrado (ver la discusión en
    # enrollment_repository.get_certified_hours): determinista, no se
    # puede inflar dejando una pestaña abierta.
    estimated_hours: Mapped[float] = mapped_column(Float, default=10.0)

    level: Mapped["CEFRLevel"] = relationship(back_populates="modules")
    # order_by aquí (no en cada query): así "lessons" viene ordenado sin
    # importar desde dónde se cargue la relación.
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", order_by="Lesson.order")

    def __repr__(self) -> str:
        return f"<Module {self.title}>"
