from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.repositories import enrollment_repository
from app.schemas.descriptor import CertificationResultOut, DescriptorMasteryOut, DescriptorMasterySummaryOut, LevelExitGateOut
from app.schemas.progress import ProgressModuleOut, ProgressOut, SkillBreakdownOut
from app.services import certification as certification_service

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
    app.services.certification.load_descriptor_mastery.
    """
    loaded = await certification_service.load_descriptor_mastery(db, current_user.id, level_code)
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")
    level, descriptors, mastery_by_code, threshold = loaded

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


@router.get("/progress/level-exit/{level_code}", response_model=LevelExitGateOut)
async def get_my_level_exit_gate(
    level_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LevelExitGateOut:
    """¿Puede el alumno autenticado certificar este nivel? Evalúa los
    `level_exit_criteria` en texto libre del módulo de cierre (documento
    de currículo) contra su versión ejecutable (CEFRLevel.exit_gate):

    1. Todos los descriptores `priority: critical` con mastery >= threshold.
    2. Al menos `min_ratio` del total de descriptores con mastery >= `min_mastery`
       (una barra MÁS BAJA que "dominado" a propósito: el documento pide
       amplitud de cobertura, no que TODO llegue al umbral de dominio pleno).
    3. Las tareas de cierre (`exit_gate.exit_tasks`) superadas en al menos
       `times_required` SESIONES distintas — más estricto que "el
       descriptor está dominado", porque exige repetición en ESA tarea
       puntual.

    No hay certificación parcial: `eligible` es el AND de los tres. Esto
    es solo CONSULTA — no certifica nada por sí mismo (para eso, POST
    .../certify/{level_code}, o espera: cualquier evidencia nueva que
    cierre el gate certifica sola, ver app.services.certification).
    """
    loaded = await certification_service.load_descriptor_mastery(db, current_user.id, level_code)
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")
    level, descriptors, mastery_by_code, threshold = loaded

    criteria = await certification_service.build_exit_criteria(
        db, current_user.id, level, descriptors, mastery_by_code, threshold
    )

    return LevelExitGateOut(
        level_code=level.code,
        eligible=all(c.met for c in criteria),
        criteria=criteria,
    )


@router.post("/certify/{level_code}", response_model=CertificationResultOut, status_code=201)
async def certify_level(
    level_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CertificationResultOut:
    """Certifica el nivel si (y SOLO si) el gate de salida da `eligible`.

    En la práctica, la mayoría de certificaciones ya habrán ocurrido
    SOLAS antes de que nadie llame esto (ver app.services.certification.
    try_auto_certify_from_descriptor, disparado desde cada intento de
    examen y cada tarea de chat) — este endpoint sigue existiendo para el
    caso explícito ("quiero comprobar/forzar ahora mismo") y como
    fallback si por lo que sea el auto-chequeo no llegó a dispararse.

    Si no es elegible: 409, con el mismo detalle por criterio que
    LevelExitGateOut (qué falta, no solo que falta algo).
    """
    loaded = await certification_service.load_descriptor_mastery(db, current_user.id, level_code)
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")
    level, descriptors, mastery_by_code, threshold = loaded

    criteria = await certification_service.build_exit_criteria(
        db, current_user.id, level, descriptors, mastery_by_code, threshold
    )

    if not all(c.met for c in criteria):
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Todavía no se cumplen los requisitos para certificar {level.code}.",
                "eligible": False,
                "criteria": [c.model_dump() for c in criteria],
            },
        )

    return await certification_service.certify(db, current_user.id, level, source="manual")
