from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.repositories import descriptor_evidence_repository, descriptor_repository, enrollment_repository, level_repository
from app.repositories.descriptor_evidence_repository import DEFAULT_EVIDENCE_REQUIRED, DEFAULT_THRESHOLD
from app.schemas.descriptor import DescriptorMasteryOut, DescriptorMasterySummaryOut
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


@router.get("/progress/descriptors/{level_code}", response_model=DescriptorMasterySummaryOut)
async def get_my_descriptor_mastery(
    level_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DescriptorMasterySummaryOut:
    """Dominio acumulado del alumno autenticado sobre cada descriptor MCER
    de un nivel (documento § 1.6): no es la nota de un ejercicio, es el
    resultado de aplicar la regla de evidencia (threshold/evidence_required
    de CEFRLevel.mastery_rule) sobre TODA su evidencia acumulada — ver
    descriptor_evidence_repository.get_mastery_for_level.
    """
    level = await level_repository.get_by_code(db, level_code)
    if level is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")

    rule = level.mastery_rule or {}
    threshold = rule.get("threshold", DEFAULT_THRESHOLD)
    evidence_required = rule.get("evidence_required", DEFAULT_EVIDENCE_REQUIRED)

    descriptors = await descriptor_repository.list_by_level_code(db, level_code)
    mastery_by_code = await descriptor_evidence_repository.get_mastery_for_level(
        db, current_user.id, level.id, threshold, evidence_required
    )

    out = [
        DescriptorMasteryOut(
            code=d.code,
            skill=d.skill,
            statement_es=d.statement_es,
            priority=d.priority,
            mastery=mastery_by_code.get(d.code, 0.0),
            is_mastered=mastery_by_code.get(d.code, 0.0) >= threshold,
        )
        for d in descriptors
    ]
    mastered_count = sum(1 for d in out if d.is_mastered)

    return DescriptorMasterySummaryOut(
        level_code=level.code,
        threshold=threshold,
        total=len(out),
        mastered=mastered_count,
        percentage=round((mastered_count / len(out)) * 100, 1) if out else 0.0,
        descriptors=out,
    )
