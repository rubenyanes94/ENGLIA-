from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos SQLAlchemy.
    Alembic la usa (vía Base.metadata) para saber qué tablas deberían existir."""

    pass


# El "engine" es la conexión (en realidad, un pool de conexiones) a PostgreSQL.
engine = create_async_engine(settings.database_url, echo=False)

# Fábrica de sesiones: cada request de FastAPI pedirá una sesión nueva.
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: abre una sesión de base de datos por request
    y la cierra automáticamente al terminar, incluso si hay un error."""
    async with AsyncSessionLocal() as session:
        yield session
