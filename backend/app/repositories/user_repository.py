import uuid

from sqlalchemy import select
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
