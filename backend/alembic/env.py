import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Importamos Settings y Base + TODOS los modelos. Esto es lo que le permite
# a "alembic revision --autogenerate" comparar lo que hay en la base de
# datos contra lo que dicen nuestras clases Python y generar el diff solo.
from app.core.config import settings
from app.core.db import Base
from app.models import *  # noqa: F401,F403  (registra los modelos contra Base)

config = context.config

# En vez de depender de la URL escrita en alembic.ini, la tomamos de
# nuestra configuración centralizada (que a su vez lee la variable de
# entorno DATABASE_URL). Así solo hay UN sitio donde vive esa cadena.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse a una base de datos real (para revisar
    el script antes de aplicarlo, o generar un .sql para otro entorno)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Nuestro engine es async (asyncpg), así que Alembic necesita este
    puente: abre una conexión async y ejecuta las migraciones (que son
    código síncrono) dentro de ella vía run_sync()."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
