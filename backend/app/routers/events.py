from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User, UserEvent
from app.repositories import event_repository
from app.schemas.event import EventIn, EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventOut, status_code=201)
async def track_event(
    payload: EventIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserEvent:
    """Tracking genérico: para todo lo que el FRONTEND observa pero el
    backend no "sabe" por sí mismo (ej. "video_played", "lesson_opened",
    tiempo en pantalla). Las acciones que YA pasan por el backend
    (inscribirse, intentar un ejercicio, cerrar una sesión de chat) se
    registran solas — no las dupliques llamando aquí también."""
    return await event_repository.record(db, current_user.id, payload.event_type, payload.payload)


@router.get("/me", response_model=list[EventOut])
async def list_my_events(
    event_type: str | None = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserEvent]:
    """Historial propio, más reciente primero — útil para un panel de
    "actividad reciente" o para depurar qué se registró. `limit` con tope
    duro: que un cliente pida ?limit=999999 no debe poder tirar de toda
    la tabla de un jalón."""
    return await event_repository.list_for_user(db, current_user.id, event_type=event_type, limit=min(limit, 500))
