"""Primitivas de seguridad: hashing de contraseñas y JWT.

Deliberadamente sin importar nada de SQLAlchemy/FastAPI aquí — esta capa
no sabe qué es un "usuario" ni una request HTTP, solo sabe hashear texto
y firmar/verificar tokens. Quien conecta esto con la base de datos y con
FastAPI es app/core/deps.py.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: str) -> str:
    """`subject` es el id del usuario (como string). Va en el claim `sub`,
    el estándar de JWT para "de quién es este token"."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Devuelve el `sub` (id del usuario) si el token es válido.
    Lanza jwt.PyJWTError (expirado, firma inválida, etc.) si no lo es —
    quien llama decide cómo traducir eso a una respuesta HTTP."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    return payload["sub"]
