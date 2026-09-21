from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models import User
from app.repositories import user_repository
from app.schemas.auth import AccessOut, RegisterRequest, TokenResponse, UserOut
from app.services.access import access_status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await user_repository.get_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una cuenta con ese email.")

    user = await user_repository.create_user(
        db, email=payload.email, password=payload.password, full_name=payload.full_name
    )
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
