import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class FlashCourse(Base):
    """Curso corto de la Biblioteca: un tema concreto (inglés para
    petroleros, para una entrevista de trabajo...) que se practica con el
    tutor en escenarios de role-play.

    Tabla propia y no un Module más, a propósito. Los módulos son el
    currículo MCER: van en orden, se desbloquean uno tras otro, suman
    horas hacia la certificación y tienen examen. Un curso de la Biblioteca
    no es nada de eso — se toma en cualquier orden y no certifica nivel.
    Metido entre los módulos, habría que acordarse de excluirlo en cada
    consulta de progresión, y la primera que se olvidara bloquearía o
    inflaría el nivel del alumno.

    Lo que SÍ comparte con Module es la forma que lee el tutor:
    `communicative_objectives`, `tutor_config` y `l1_interference` tienen
    el mismo significado y el mismo formato, así que
    agents/prompt_builder.py los aplica sin distinguir de dónde vienen.
    """

    __tablename__ = "flash_courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Identificador estable para URLs y para el archivo de contenido, que
    # no cambia si se reescribe el título.
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))  # en inglés, como Module.title
    title_es: Mapped[str] = mapped_column(String(255))
    description_es: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))  # trabajo | viajes | vida_diaria | social
    icon: Mapped[str] = mapped_column(String(40))  # nombre de icono FontAwesome, sin prefijo
    recommended_level: Mapped[str] = mapped_column(String(2))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    order: Mapped[int] = mapped_column(Integer, default=0)

    communicative_objectives: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    # [{"en": "...", "es": "..."}] — la chuleta que el alumno repasa antes
    # de practicar.
    key_phrases: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    # Los escenarios de role-play. Mismo formato que Module.tasks (id,
    # prompt, success_criteria) más `title` y `tutor_role`: el papel que
    # hace el tutor en ese escenario (el reclutador, el mesero...).
    scenarios: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    tutor_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    l1_interference: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    @property
    def tasks(self) -> list[dict]:
        """Alias con el nombre que usa el chat para resolver la tarea activa
        (ver routers/chat.py), para tratar módulos y cursos igual ahí."""
        return self.scenarios

    def __repr__(self) -> str:
        return f"<FlashCourse {self.slug}>"


class FlashCourseProgress(Base):
    """Qué escenarios de un curso ha completado un alumno.

    No suma evidencia MCER ni horas de certificación: los escenarios de la
    Biblioteca son de un dominio concreto (una entrevista, una plataforma
    petrolera), no descriptores del marco. Contarlos hacia el nivel
    certificaría a alguien por dominar el vocabulario de un taladro.
    """

    __tablename__ = "flash_course_progress"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_flash_course_progress_user_course"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("flash_courses.id"))
    completed_scenarios: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    course: Mapped["FlashCourse"] = relationship()
