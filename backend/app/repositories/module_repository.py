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


async def create(
    db: AsyncSession, level_id: uuid.UUID, title: str, skill_focus: str, order: int, estimated_hours: float = 10.0
) -> Module:
    module = Module(level_id=level_id, title=title, skill_focus=skill_focus, order=order, estimated_hours=estimated_hours)
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
    estimated_hours: float | None = None,
) -> Module:
    """PATCH parcial: solo toca los campos que vienen distintos de None
    (el schema ModuleUpdate ya solo envía lo que el admin quiso cambiar)."""
    if title is not None:
        module.title = title
    if skill_focus is not None:
        module.skill_focus = skill_focus
    if order is not None:
        module.order = order
    if estimated_hours is not None:
        module.estimated_hours = estimated_hours

    await db.commit()
    await db.refresh(module)
    return module


async def get_previous_in_level(db: AsyncSession, module: Module) -> Module | None:
    """El módulo justo antes de este en el mismo nivel (mismo level_id,
    order - 1) — es contra el que se compara para el bloqueo secuencial
    (ver POST /modules/{id}/enroll). None si este ya es el primero."""
    if module.order <= 1:
        return None

    result = await db.execute(select(Module).where(Module.level_id == module.level_id, Module.order == module.order - 1))
    return result.scalars().first()


async def delete(db: AsyncSession, module: Module) -> None:
    # ON DELETE por defecto de SQLAlchemy/Postgres aquí es RESTRICT: si el
    # módulo tiene lecciones (o inscripciones) todavía, esto lanzará un
    # IntegrityError en vez de borrar en cascada silenciosamente — a
    # propósito, para no destruir progreso de alumnos por accidente. El
    # router traduce ese error a un 409 explicable.
    await db.delete(module)
    await db.commit()
