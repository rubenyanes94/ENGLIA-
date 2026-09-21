import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import User
from app.repositories import user_repository
from app.services.access import access_status

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


# Quién puede entrar al panel de gerencia. "admin" entra también: quien
# puede editar el currículo no tiene por qué pedir otra cuenta para ver las
# cifras. "manager" LEE la analítica y, como única escritura, revisa pagos
# (aprobar/rechazar Pago Móvil y Binance, en routers/payment_review.py).
# get_current_admin lo sigue rechazando: no puede tocar contenido, planes
# ni nada más de /admin.
MANAGEMENT_ROLES = ("manager", "admin")


async def get_current_manager(current_user: User = Depends(get_current_user)) -> User:
    """Guarda del panel de gerencia (routers/management.py). Mismo patrón
    que get_current_admin: 401 si el token no vale, 403 si vale pero el
    rol no es de gerencia."""
    if current_user.role not in MANAGEMENT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere acceso de gerencia.")
    return current_user


async def require_access(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """El candado de pago de la app de alumno: 402 si el usuario no tiene
    acceso (ver la regla completa en app/services/access.py — suscripción,
    exento, equipo, o pago manual pendiente de verificar).

    Se engancha a nivel de router (chat, módulos, biblioteca, juego,
    pronunciación, /users/me) y no solo en el frontend: sin esto, el
    candado de la pantalla se saltaba llamando a la API directamente.

    402 Payment Required y no 403: son casos distintos a propósito — 403
    es "no tienes permiso aunque pagues", 402 es "esto se resuelve pagando".
    Incluye la autenticación: no hace falta encadenar get_current_user.
    """
    status_ = await access_status(db, current_user)
    if not status_.has_access:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Necesitas una suscripción activa para usar la app.",
        )
    return current_user
