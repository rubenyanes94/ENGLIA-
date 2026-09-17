import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class SentenceGameProgress(Base):
    """Progreso de un alumno en el juego de completar oraciones del inicio.

    Una fila por alumno, en la base de datos y no en el navegador: el nivel
    del juego es progreso real, y guardado en localStorage se perdería al
    cambiar de celular o de navegador.
    """

    __tablename__ = "sentence_game_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    # Aciertos acumulados en el nivel actual, hacia el siguiente. Un fallo
    # resta uno (sin bajar de cero): subir de nivel pide acertar con
    # constancia, no solo acumular respuestas.
    level_progress: Mapped[int] = mapped_column(Integer, default=0)
    total_answered: Mapped[int] = mapped_column(Integer, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    # La oración que se le mostró y aún no respondió. Solo esa se puede
    # contestar: sin esto, repetir la respuesta de una oración ya conocida
    # sumaría aciertos gratis hasta subir de nivel.
    pending_item_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Últimas oraciones vistas, para no repetirlas enseguida.
    recent_item_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
