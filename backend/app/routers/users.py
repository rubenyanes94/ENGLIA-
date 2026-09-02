import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import CEFRLevel, Descriptor, User
from app.repositories import (
    descriptor_evidence_repository,
    descriptor_repository,
    enrollment_repository,
    event_repository,
    level_repository,
    user_repository,
)
from app.repositories.descriptor_evidence_repository import DEFAULT_EVIDENCE_REQUIRED, DEFAULT_THRESHOLD
from app.schemas.descriptor import (
    CertificationResultOut,
    DescriptorMasteryOut,
    DescriptorMasterySummaryOut,
    ExitCriterionOut,
    LevelExitGateOut,
)
from app.schemas.progress import ProgressModuleOut, ProgressOut, SkillBreakdownOut

router = APIRouter(prefix="/users/me", tags=["users"])


async def _load_descriptor_mastery(
    db: AsyncSession, user_id: uuid.UUID, level_code: str
) -> tuple[CEFRLevel, list[Descriptor], dict[str, float], float]:
    """Carga compartida por get_my_descriptor_mastery y
    get_my_level_exit_gate: ambos necesitan el nivel, su catálogo de
    descriptores y el mastery de CADA UNO para este alumno — evita
    calcularlo dos veces si un frontend pide primero uno y luego otro
    en la misma pantalla, y evita que los dos endpoints diverjan en cómo
    leen threshold/evidence_required de CEFRLevel.mastery_rule."""
    level = await level_repository.get_by_code(db, level_code)
    if level is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")

    rule = level.mastery_rule or {}
    threshold = rule.get("threshold", DEFAULT_THRESHOLD)
    evidence_required = rule.get("evidence_required", DEFAULT_EVIDENCE_REQUIRED)

    descriptors = await descriptor_repository.list_by_level_code(db, level_code)
    mastery_by_code = await descriptor_evidence_repository.get_mastery_for_level(
        db, user_id, level.id, threshold, evidence_required
    )

    return level, descriptors, mastery_by_code, threshold


async def _build_exit_criteria(
    db: AsyncSession,
    user_id: uuid.UUID,
    level: CEFRLevel,
    descriptors: list[Descriptor],
    mastery_by_code: dict[str, float],
    threshold: float,
) -> list[ExitCriterionOut]:
    """Evalúa los 3 criterios de CEFRLevel.exit_gate (versión ejecutable
    de Module.assessment.level_exit_criteria) para UN alumno. Compartida
    por get_my_level_exit_gate (solo consulta) y certify_level (decide si
    certificar de verdad) — para que nunca puedan divergir sobre qué
    cuenta como "elegible"."""
    exit_gate = level.exit_gate or {}
    criteria: list[ExitCriterionOut] = []

    # --- Criterio 1: descriptores críticos dominados ---
    critical_descriptors = [d for d in descriptors if d.priority == "critical"]
    missing_critical = [d.code for d in critical_descriptors if mastery_by_code.get(d.code, 0.0) < threshold]
    criteria.append(
        ExitCriterionOut(
            key="critical_descriptors_mastered",
            label=f"Todos los descriptores marcados priority: critical con mastery >= {threshold}",
            met=not missing_critical,
            detail={"total_critical": len(critical_descriptors), "missing": missing_critical},
        )
    )

    # --- Criterio 2: cobertura mínima del catálogo completo ---
    ratio_cfg = exit_gate.get("descriptor_mastery_ratio", {})
    min_ratio = ratio_cfg.get("min_ratio", 0.8)
    min_mastery = ratio_cfg.get("min_mastery", 0.7)
    total = len(descriptors)
    passing = sum(1 for d in descriptors if mastery_by_code.get(d.code, 0.0) >= min_mastery)
    actual_ratio = round(passing / total, 3) if total else 0.0
    criteria.append(
        ExitCriterionOut(
            key="descriptor_mastery_ratio",
            label=f"Al menos {round(min_ratio * 100)}% de los descriptores con mastery >= {min_mastery}",
            met=actual_ratio >= min_ratio,
            detail={"total": total, "passing": passing, "actual_ratio": actual_ratio, "min_ratio": min_ratio},
        )
    )

    # --- Criterio 3: tareas de cierre superadas en sesiones distintas ---
    exit_tasks_cfg = exit_gate.get("exit_tasks", [])
    if exit_tasks_cfg:
        tasks_detail = []
        for task_cfg in exit_tasks_cfg:
            task_id = task_cfg["task_id"]
            times_required = task_cfg.get("times_required", 1)
            times_completed = await descriptor_evidence_repository.count_distinct_successful_sessions(
                db, user_id, context=task_id
            )
            tasks_detail.append(
                {
                    "task_id": task_id,
                    "times_required": times_required,
                    "times_completed": times_completed,
                    "met": times_completed >= times_required,
                }
            )
        criteria.append(
            ExitCriterionOut(
                key="exit_tasks_completed",
                label="Tareas de cierre de nivel superadas en sesiones distintas",
                met=all(t["met"] for t in tasks_detail),
                detail={"tasks": tasks_detail},
            )
        )

    return criteria


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
    level, descriptors, mastery_by_code, threshold = await _load_descriptor_mastery(db, current_user.id, level_code)

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
       puntual (ver descriptor_evidence_repository.count_distinct_successful_sessions).

    No hay certificación parcial: `eligible` es el AND de los tres.
    """
    level, descriptors, mastery_by_code, threshold = await _load_descriptor_mastery(db, current_user.id, level_code)
    criteria = await _build_exit_criteria(db, current_user.id, level, descriptors, mastery_by_code, threshold)

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
    """Certifica el nivel si (y SOLO si) el gate de salida da `eligible`
    — reutiliza exactamente la misma evaluación que GET .../level-exit
    (_build_exit_criteria), así los dos endpoints nunca pueden divergir
    sobre qué cuenta como "listo".

    Si no es elegible: 409, con el mismo detalle por criterio que
    LevelExitGateOut (qué falta, no solo que falta algo), para que el
    frontend pueda explicarlo sin adivinar.

    Si es elegible: mueve User.current_level_id al SIGUIENTE nivel de la
    progresión (certificar A1 dice "ya estás trabajando en A2", no "te
    quedas parado en A1") y deja constancia en UserEvent. Idempotente: si
    el alumno ya estaba en ese nivel siguiente (ej. llamó dos veces, o ya
    lo habían certificado por otra vía), no vuelve a escribir ni a
    duplicar el evento — simplemente confirma que sigue certificado.
    """
    level, descriptors, mastery_by_code, threshold = await _load_descriptor_mastery(db, current_user.id, level_code)
    criteria = await _build_exit_criteria(db, current_user.id, level, descriptors, mastery_by_code, threshold)

    if not all(c.met for c in criteria):
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Todavía no se cumplen los requisitos para certificar {level.code}.",
                "eligible": False,
                "criteria": [c.model_dump() for c in criteria],
            },
        )

    # Nivel siguiente en la progresión (order + 1). Si `level` ya es el
    # último (C2), no hay "siguiente" — el alumno se queda certificado
    # EN el que acaba de completar, no hay dónde más moverlo.
    next_level = await level_repository.get_by_order(db, level.order + 1)
    target_level = next_level if next_level is not None else level

    if current_user.current_level_id != target_level.id:
        await user_repository.set_current_level(db, current_user, target_level.id)
        await event_repository.record(
            db,
            current_user.id,
            "level_certified",
            {"level_code": level.code, "next_level_code": target_level.code if next_level else None},
        )

    return CertificationResultOut(
        level_code=level.code,
        certified=True,
        next_level_code=next_level.code if next_level else None,
        certified_at=datetime.now(timezone.utc),
    )
