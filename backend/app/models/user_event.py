import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class UserEvent(Base):
    """Registro genérico de "todo lo que hace el alumno" — la materia
    prima de analítica de producto.

    A propósito NO es una tabla por tipo de evento (ExerciseAttempt ya es
    eso, y sirve para pintar UI). Esta es la contraparte "ancha": un
    `event_type` libre + `payload` JSONB, para poder registrar cosas
    nuevas (ej. "video_played", "lesson_opened", "streak_broken") sin
    migrar el esquema cada vez que a producto se le ocurre medir algo
    distinto. El coste es que hay que agregarla con código, no con SQL
    trivial — trade-off correcto para una tabla que existe PARA explorar
    patrones que todavía no sabemos que vamos a necesitar.

    Los eventos que sí necesitan queries rápidas y estables (progreso de
    un ejercicio, mastery_score de un módulo) siguen viviendo en sus
    propias tablas relacionales — esta no las reemplaza, las complementa.
    """

    __tablename__ = "user_events"
    __table_args__ = (
        # Cubre el patrón de consulta más común: "los eventos de tipo X
        # de este alumno, en orden cronológico" (ej. para calcular horas
        # de práctica o una racha diaria).
        Index("ix_user_events_user_type_time", "user_id", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<UserEvent {self.event_type} user={self.user_id}>"
