import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    native_language: Mapped[str] = mapped_column(String(10), default="es")

    # Nivel MCER actual del alumno. Nullable porque un usuario recién
    # registrado todavía no ha hecho el test de nivel inicial.
    current_level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cefr_levels.id"), nullable=True
    )
    current_level: Mapped["CEFRLevel | None"] = relationship()

    # URL pública (relativa) de la foto de perfil, ej. "/media/avatars/<id>-ab12cd34.jpg".
    # Guardamos la URL, no la ruta en disco: el día que esto se mueva a S3
    # o a un CDN, solo cambia app/media/storage.py (mismo criterio que el
    # audio de lecciones). Nullable: sin foto se pinta la inicial del nombre.
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # "student" | "admin". String en vez de un enum de Postgres: añadir un
    # rol nuevo más adelante (ej. "content_editor") es un UPDATE de texto,
    # no una migración de tipo enum.
    role: Mapped[str] = mapped_column(String(20), default="student")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
