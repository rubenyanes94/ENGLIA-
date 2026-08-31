from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.repositories import level_repository
from app.schemas.level import CEFRLevelOut

router = APIRouter(prefix="/levels", tags=["levels"])


@router.get("", response_model=list[CEFRLevelOut])
async def get_levels(db: AsyncSession = Depends(get_db)) -> list[CEFRLevelOut]:
    """Devuelve los 6 niveles MCER, ordenados de A1 a C2."""
    levels = await level_repository.list_levels(db)
    return levels
