from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.repositories import enrollment_repository
from app.schemas.progress import ProgressModuleOut, ProgressOut, SkillBreakdownOut

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("/progress", response_model=ProgressOut)
async def get_my_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressOut:
    """Vista agregada de progreso: nivel actual del alumno + estado de
    cada módulo en el que se ha inscrito. Pensado para pintar de un solo
    fetch el dashboard/pantalla de inicio, sin que el frontend tenga que
    combinar /levels, /modules/{id} y N llamadas más por su cuenta."""
    enrollments = await enrollment_repository.list_for_user(db, current_user.id)

    modules = [
        ProgressModuleOut(
            module_id=enrollment.module_id,
            module_title=enrollment.module.title,
            level_code=enrollment.module.level.code,
            status=enrollment.status,
            mastery_score=enrollment.mastery_score,
        )
        for enrollment in enrollments
    ]

    return ProgressOut(
        current_level_code=current_user.current_level.code if current_user.current_level else None,
        modules=modules,
    )


@router.get("/progress/skills", response_model=SkillBreakdownOut)
async def get_my_skill_breakdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillBreakdownOut:
    """Desglose por destreza CEFR (listening/speaking/reading/writing),
    para el gráfico de barras de la pantalla de Progreso."""
    skills = await enrollment_repository.get_skill_breakdown(db, current_user.id)
    skills_pct = {skill: round(mastery * 100, 1) for skill, mastery in skills.items()}
    average = round(sum(skills_pct.values()) / len(skills_pct), 1) if skills_pct else 0.0

    return SkillBreakdownOut(skills=skills_pct, average=average)
