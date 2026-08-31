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


async def create(db: AsyncSession, level_id: uuid.UUID, title: str, skill_focus: str, order: int) -> Module:
    module = Module(level_id=level_id, title=title, skill_focus=skill_focus, order=order)
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


async def update(
    db: AsyncSession,
    module: Module,
    title: str | None = None,
    skill_focus: str | None = None,
    order: int | None = None,
) -> Module:
    """PATCH parcial: solo toca los campos que vienen distintos de None
    (el schema ModuleUpdate ya solo envía lo que el admin quiso cambiar)."""
    if title is not None:
        module.title = title
    if skill_focus is not None:
        module.skill_focus = skill_focus
    if order is not None:
        module.order = order

    await db.commit()
    await db.refresh(module)
    return module


async def delete(db: AsyncSession, module: Module) -> None:
    # ON DELETE por defecto de SQLAlchemy/Postgres aquí es RESTRICT: si el
    # módulo tiene lecciones (o inscripciones) todavía, esto lanzará un
    # IntegrityError en vez de borrar en cascada silenciosamente — a
    # propósito, para no destruir progreso de alumnos por accidente. El
    # router traduce ese error a un 409 explicable.
    await db.delete(module)
    await db.commit()
