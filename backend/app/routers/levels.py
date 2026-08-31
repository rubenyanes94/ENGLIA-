from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.repositories import level_repository, module_repository
from app.schemas.level import CEFRLevelOut
from app.schemas.module import ModuleOut

router = APIRouter(prefix="/levels", tags=["levels"])


@router.get("", response_model=list[CEFRLevelOut])
async def get_levels(db: AsyncSession = Depends(get_db)) -> list[CEFRLevelOut]:
    """Devuelve los 6 niveles MCER, ordenados de A1 a C2."""
    levels = await level_repository.list_levels(db)
    return levels


@router.get("/{level_code}/modules", response_model=list[ModuleOut])
async def get_level_modules(level_code: str, db: AsyncSession = Depends(get_db)) -> list[ModuleOut]:
    """Índice de módulos de un nivel (ej. GET /levels/A1/modules).

    Comprobamos que el nivel exista antes de listar para poder distinguir
    "nivel inválido" (404) de "nivel válido pero sin módulos todavía" ([]).
    """
    level = await level_repository.get_by_code(db, level_code)
    if level is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")

    return await module_repository.list_by_level_code(db, level_code)
