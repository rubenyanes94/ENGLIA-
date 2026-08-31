import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import User
from app.repositories import subscription_repository, user_repository

# tokenUrl es solo informativo (lo usa /docs para dibujar el botón
# "Authorize"): le dice a Swagger dónde se consigue el token, aunque
# nosotros no dependemos de este objeto para el intercambio en sí.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar la credencial.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user_id = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token expiró, inicia sesión de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise CREDENTIALS_EXCEPTION

    try:
        user = await user_repository.get_by_id(db, uuid.UUID(user_id))
    except ValueError:
        raise CREDENTIALS_EXCEPTION

    if user is None:
        raise CREDENTIALS_EXCEPTION
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario deshabilitado.")

    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Depende de get_current_user (no lo duplica): primero exige un
    token válido, y ENCIMA exige rol admin. Un token inválido da 401
    (como siempre); un token válido de un alumno normal da 403 — son
    fallos distintos y el código de estado ya lo comunica sin leer el detail."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permisos de administrador.")
    return current_user


async def require_active_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """El candado de pago, listo para enganchar — pero a propósito TODAVÍA
    NO está en ningún router (curriculum, chat...). Se decidió así
    mientras seguimos construyendo/probando el resto del backend sin que
    cada request de prueba necesite antes una suscripción real de por
    medio. Para activarlo en un endpoint: cambia
    `Depends(get_current_user)` por `Depends(require_active_subscription)`
    (ya incluye la autenticación, no hace falta encadenar las dos).

    402 Payment Required en vez de 403: son casos distintos a propósito
    — 403 es "no tienes permiso aunque pagues", 402 es literalmente
    "esto se resuelve pagando".
    """
    subscription = await subscription_repository.get_active(db, current_user.id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Necesitas una suscripción activa para acceder a este contenido.",
        )
    return current_user
