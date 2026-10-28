import logging
import time
import uuid
from urllib.parse import quote

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import AsyncSessionLocal, get_db
from app.core.deps import get_current_user
from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    password_reset_matches,
    verify_password,
)
from app.models import User
from app.notifications import messages
from app.notifications import service as notifications
from app.repositories import user_repository
from app.schemas.auth import (
    AccessOut,
    ForgotPasswordRequest,
    MessageOut,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services.access import access_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Un correo de "cambiar contraseña" por dirección cada tanto: sin esto,
# cualquiera podría llenarle el buzón a otro pulsando el botón en bucle.
RESET_COOLDOWN_SECONDS = 60

RESET_REQUESTED = (
    "Si hay una cuenta con ese correo, te acabamos de enviar un enlace para cambiar la contraseña. "
    "Revisa también la carpeta de spam."
)
INVALID_RESET_LINK = "El enlace no es válido o ya caducó. Pide uno nuevo desde «¿Olvidaste tu contraseña?»."


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await user_repository.get_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una cuenta con ese email.")

    user = await user_repository.create_user(
        db, email=payload.email, password=payload.password, full_name=payload.full_name
    )
    # Correo de bienvenida. Va aquí y no en segundo plano porque son
    # ~300 ms y falla en silencio: si Resend no responde, el registro se
    # completa igual (ver app/notifications/service.py).
    await notifications.send(db, user, "bienvenida")

    # Auto-login al registrarse: el alumno no tiene que hacer dos pasos.
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # OAuth2PasswordRequestForm exige el campo "username" por estándar,
    # aunque aquí en la práctica el alumno inicia sesión con su email.
    user = await user_repository.get_by_email(db, form_data.username)

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def read_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """El usuario y si puede usar la app (el candado de pago). El frontend
    decide con esto a dónde mandarlo: al aula o a la pantalla de pago."""
    access = await access_status(db, current_user)
    user = UserOut.model_validate(current_user)
    user.access = AccessOut(**access.__dict__)
    return user


@router.post("/password/forgot", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(payload: ForgotPasswordRequest, background: BackgroundTasks) -> MessageOut:
    """Pide el correo con el botón para cambiar la contraseña.

    Responde SIEMPRE lo mismo, exista o no la cuenta: si no, este
    formulario serviría para averiguar quién es alumno de Espikin. Por la
    misma razón el trabajo va en segundo plano — buscar al usuario y
    hablar con Resend tarda, y esa diferencia de tiempo también delataría
    si la cuenta existe."""
    background.add_task(_send_reset_email, payload.email.lower())
    return MessageOut(message=RESET_REQUESTED)


async def _send_reset_email(email: str) -> None:
    try:
        # SET NX: solo el primero de la ventana pasa. Si Redis no responde,
        # se envía igual — mejor un correo de más que dejar a alguien fuera
        # de su cuenta.
        if not await redis_client.set(f"password_reset:{email}", "1", nx=True, ex=RESET_COOLDOWN_SECONDS):
            return
    except Exception:  # noqa: BLE001
        logger.warning("Redis no responde: se envía el correo de contraseña sin límite de frecuencia")

    # Sesión propia: la de get_db ya se cerró cuando corre esta tarea.
    async with AsyncSessionLocal() as db:
        user = await user_repository.get_by_email(db, email)
        if user is None or not user.is_active:
            return
        token = create_password_reset_token(str(user.id), user.hashed_password)
        enlace = f"{settings.frontend_base_url.rstrip('/')}/restablecer?token={quote(token)}"
        minutos = settings.password_reset_expire_minutes
        await notifications.send(
            db, user, "restablecer_clave",
            # Una fila por petición: si pide otro enlace, tiene que salir.
            dedupe_key=f"restablecer_clave:{int(time.time())}",
            context={"minutos": minutos},  # el enlace NO: esto queda guardado
            builder=lambda u: messages.build(
                "restablecer_clave", full_name=u.full_name, app_url=settings.frontend_base_url.rstrip("/"),
                context={"enlace": enlace, "minutos": minutos},
            ),
        )


@router.post("/password/reset", response_model=TokenResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Guarda la contraseña nueva y deja al alumno con la sesión iniciada:
    acaba de demostrar que es el dueño del correo, pedirle que la escriba
    otra vez en el login no aporta nada."""
    try:
        user_id, fingerprint = decode_password_reset_token(payload.token)
        user = await user_repository.get_by_id(db, uuid.UUID(user_id))
    except (jwt.PyJWTError, ValueError):
        user = None
    # Huella distinta = la contraseña ya cambió desde que se pidió el
    # enlace (este mismo u otro): el enlace ya se usó.
    if user is None or not user.is_active or not password_reset_matches(fingerprint, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESET_LINK)

    await user_repository.set_password(db, user, payload.password)
    return TokenResponse(access_token=create_access_token(subject=str(user.id)))
