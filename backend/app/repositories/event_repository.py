import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserEvent


async def record(db: AsyncSession, user_id: uuid.UUID, event_type: str, payload: dict | None = None) -> UserEvent:
    """No hace `db.refresh()` a propósito: nadie necesita leer el evento
    de vuelta en el mismo request que lo generó (a diferencia de crear un
    Enrollment, por ejemplo). Evita un roundtrip extra en el path caliente
    de endpoints que ya hacen otro trabajo (ej. calificar un ejercicio) y
    solo "de paso" registran el evento."""
    event = UserEvent(user_id=user_id, event_type=event_type, payload=payload or {})
    db.add(event)
    await db.commit()
    return event


async def list_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
) -> list[UserEvent]:
    query = select(UserEvent).where(UserEvent.user_id == user_id)
    if event_type is not None:
        query = query.where(UserEvent.event_type == event_type)
    if since is not None:
        query = query.where(UserEvent.created_at >= since)

    query = query.order_by(UserEvent.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
