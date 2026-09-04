import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import hash_password
from app.models import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalars().first()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    # joinedload de current_level a propósito: get_current_user() usa esta
    # función en CADA request autenticado, y /users/me/progress necesita
    # leer current_user.current_level.code. Sin precargarla aquí, ese
    # acceso revienta (MissingGreenlet) en vez de fallar solo donde se usa.
    result = await db.execute(select(User).options(joinedload(User.current_level)).where(User.id == user_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, email: str, password: str, full_name: str) -> User:
    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
    role: str | None = None,
) -> tuple[list[User], int]:
    """Página de usuarios + total que cumple los filtros (para el panel de
    admin, ver routers/admin.py).

    Devuelve la tupla (página, total) y no solo la lista porque el total
    se calcula con un COUNT sobre los MISMOS filtros pero SIN limit/offset
    — el frontend no puede deducirlo de la página que recibe.

    Sin joinedload de current_level a propósito (a diferencia de
    get_by_id): el listado no muestra el nivel, y precargarlo aquí sería
    un JOIN extra por cada fila de cada página sin que nadie lo lea.
    """
    filters = []
    if search:
        # ilike sobre email Y nombre: quien busca en un panel no sabe (ni
        # le importa) en cuál de los dos campos está lo que escribió.
        pattern = f"%{search.strip()}%"
        filters.append(User.email.ilike(pattern) | User.full_name.ilike(pattern))
    if role:
        filters.append(User.role == role)

    total = await db.scalar(select(func.count()).select_from(User).where(*filters))

    result = await db.execute(
        select(User).where(*filters).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total or 0


async def set_avatar_url(db: AsyncSession, user: User, avatar_url: str | None) -> User:
    """Fija (o limpia, con None) la URL de la foto de perfil. Borrar el
    ARCHIVO anterior es responsabilidad de quien llama, no de aquí: este
    módulo solo sabe de la base de datos, no del disco."""
    user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)
    return user


async def set_current_level(db: AsyncSession, user: User, level_id: uuid.UUID) -> User:
    """Lo llama la certificación (routers/users.py, certify_level) al
    aprobar el gate de salida de un nivel: mueve al alumno al SIGUIENTE
    nivel de la progresión, no lo deja marcado en el que acaba de certificar."""
    user.current_level_id = level_id
    await db.commit()
    await db.refresh(user)
    return user
