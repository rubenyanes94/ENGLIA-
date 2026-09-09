import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    native_language: str
    current_level_id: uuid.UUID | None
    avatar_url: str | None = None


class UserAdminOut(BaseModel):
    """Ficha de alumno para el listado de admin (GET /admin/users).

    NO incluye `hashed_password` — obvio, pero merece estar dicho: el
    modelo User sí lo tiene, y devolver el ORM en crudo lo filtraría.
    Tampoco incluye progreso (nivel/horas/módulos): eso exige cruzar con
    enrollments y encarece un listado que puede tener miles de filas —
    si hace falta, va en un endpoint de detalle por alumno, no aquí.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str  # "student" | "admin"
    is_active: bool
    created_at: datetime


class UserListOut(BaseModel):
    """Envuelve la página de resultados junto al total.

    `total` va aparte (un COUNT propio, no len(users)) porque con
    limit/offset el frontend no puede saber cuántos alumnos hay en total
    a partir de la página que recibió — y sin ese número no puede pintar
    ni un paginador ni un "1.240 alumnos registrados".
    """

    total: int
    limit: int
    offset: int
    users: list[UserAdminOut]
