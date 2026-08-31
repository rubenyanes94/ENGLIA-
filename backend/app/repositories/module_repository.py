import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import CEFRLevel, Module


async def list_by_level_code(db: AsyncSession, level_code: str) -> list[Module]:
    result = await db.execute(
        select(Module).join(CEFRLevel).where(CEFRLevel.code == level_code.upper()).order_by(Module.order)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, module_id: uuid.UUID) -> Module | None:
    """Existencia simple, sin relaciones — para checks rápidos (ej. antes
    de inscribir a un alumno) que no necesitan pintar nada."""
    return await db.get(Module, module_id)


async def get_with_lessons(db: AsyncSession, module_id: uuid.UUID) -> Module | None:
    result = await db.execute(
        select(Module).options(joinedload(Module.lessons)).where(Module.id == module_id)
    )
    # .unique() es obligatorio aquí: joinedload sobre una relación *-a-muchos
    # duplica la fila del padre (Module) una vez por cada Lesson en el JOIN.
    return result.unique().scalars().first()
