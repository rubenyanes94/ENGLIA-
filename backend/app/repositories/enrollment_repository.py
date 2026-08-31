import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from app.models import Enrollment, Module


async def get(db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID) -> Enrollment | None:
    result = await db.execute(
        select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.module_id == module_id)
    )
    return result.scalars().first()


async def create(db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID) -> Enrollment:
    enrollment = Enrollment(
        user_id=user_id,
        module_id=module_id,
        status="in_progress",
        started_at=func.now(),
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Enrollment]:
    """Trae module + level ya cargados: el endpoint de progreso necesita
    module.title y module.level.code para cada inscripción, y sin este
    joinedload encadenado sería un N+1 (o un MissingGreenlet) por fila."""
    result = await db.execute(
        select(Enrollment)
        .options(joinedload(Enrollment.module).joinedload(Module.level))
        .where(Enrollment.user_id == user_id)
        .order_by(Enrollment.started_at)
    )
    return list(result.unique().scalars().all())
