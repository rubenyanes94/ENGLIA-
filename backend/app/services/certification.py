"""Evaluación del gate de salida de nivel + la acción de certificar.

Vive fuera de routers/users.py (donde nació) porque a partir de ahora
TRES sitios necesitan disparar esta lógica, no solo un alumno pidiéndolo
a mano:

- routers/users.py: GET .../level-exit (solo consulta) y
  POST .../certify/{code} (certificación explícita, a petición).
- routers/modules.py: tras un intento de examen que evidencia un descriptor.
- routers/chat.py: tras completar una tarea de chat con descriptor asociado.

Antes de este archivo, certificar dependía de que ALGUIEN llamara a
POST /certify — un alumno podía cumplir el gate y quedarse ahí
indefinidamente si nadie (ni un frontend, que todavía no existe) hacía
esa llamada. `try_auto_certify_from_descriptor` es el enganche que lo
resuelve: cualquier evidencia que TOQUE un descriptor dispara
automáticamente la comprobación del nivel al que pertenece.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CEFRLevel, Descriptor
from app.repositories import (
    descriptor_evidence_repository,
    descriptor_repository,
    event_repository,
    level_repository,
    user_repository,
)
from app.repositories.descriptor_evidence_repository import DEFAULT_EVIDENCE_REQUIRED, DEFAULT_THRESHOLD
from app.schemas.descriptor import CertificationResultOut, ExitCriterionOut

logger = logging.getLogger(__name__)


async def load_descriptor_mastery(
    db: AsyncSession, user_id: uuid.UUID, level_code: str
) -> tuple[CEFRLevel, list[Descriptor], dict[str, float], float] | None:
    """None si el nivel no existe — a diferencia de un endpoint HTTP, esto
    no puede lanzar HTTPException: lo llama tanto un router (que sí sabe
    traducir "None" a 404) como un disparo automático en segundo plano
    (que no tiene a quién devolverle un código de estado)."""
    level = await level_repository.get_by_code(db, level_code)
    if level is None:
        return None

    rule = level.mastery_rule or {}
    threshold = rule.get("threshold", DEFAULT_THRESHOLD)
    evidence_required = rule.get("evidence_required", DEFAULT_EVIDENCE_REQUIRED)

    descriptors = await descriptor_repository.list_by_level_code(db, level_code)
    mastery_by_code = await descriptor_evidence_repository.get_mastery_for_level(
        db, user_id, level.id, threshold, evidence_required
    )

    return level, descriptors, mastery_by_code, threshold


async def build_exit_criteria(
    db: AsyncSession,
    user_id: uuid.UUID,
    level: CEFRLevel,
    descriptors: list[Descriptor],
    mastery_by_code: dict[str, float],
    threshold: float,
) -> list[ExitCriterionOut]:
    """Evalúa los 3 criterios de CEFRLevel.exit_gate (versión ejecutable
    de Module.assessment.level_exit_criteria) para UN alumno. Única
    implementación — consulta manual, certificación manual y
    auto-certificación la comparten, así nunca pueden divergir sobre qué
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


async def certify(
    db: AsyncSession, user_id: uuid.UUID, level: CEFRLevel, source: str = "manual"
) -> CertificationResultOut:
    """Aplica la certificación. Asume que YA se comprobó que el gate está
    cumplido — no vuelve a evaluar los criterios, eso es responsabilidad
    de quien llama (certify_level o try_auto_certify_from_descriptor).

    Mueve User.current_level_id al SIGUIENTE nivel de la progresión
    (certificar A1 dice "ya estás trabajando en A2", no "te quedas
    parado en A1"). Idempotente: si el alumno ya estaba en ese nivel
    siguiente, no reescribe ni duplica el UserEvent — solo confirma.
    `source` queda en el evento para poder distinguir en analítica una
    certificación pedida a mano de una disparada sola tras un ejercicio o
    una tarea de chat.
    """
    next_level = await level_repository.get_by_order(db, level.order + 1)
    target_level = next_level if next_level is not None else level

    user = await user_repository.get_by_id(db, user_id)
    if user.current_level_id != target_level.id:
        await user_repository.set_current_level(db, user, target_level.id)
        await event_repository.record(
            db,
            user_id,
            "level_certified",
            {"level_code": level.code, "next_level_code": target_level.code if next_level else None, "source": source},
        )

    return CertificationResultOut(
        level_code=level.code,
        certified=True,
        next_level_code=next_level.code if next_level else None,
        certified_at=datetime.now(timezone.utc),
    )


async def try_auto_certify_from_descriptor(
    db: AsyncSession, user_id: uuid.UUID, descriptor_code: str
) -> CertificationResultOut | None:
    """Tras registrar evidencia para `descriptor_code` (un intento de
    examen o una tarea de chat superada), comprueba si eso alcanza para
    certificar el nivel al que pertenece — y si es así, certifica, sin
    que nadie tenga que llamar a POST /certify a mano.

    El nivel se deriva del propio código ("A1.SI.01" -> "A1"): es la
    misma convención que ya usan Module.code y Descriptor.code en todo
    el currículo, no una suposición nueva de este archivo.

    Devuelve None tanto si no certificó (lo normal — la mayoría de
    evidencias no cierran un nivel) como si algo falló evaluando: nunca
    lanza, porque esto se llama desde el camino caliente de un turno de
    chat o un envío de ejercicio, y un fallo aquí no debe tumbar esa
    respuesta — como máximo, el alumno certifica un poco más tarde, en el
    siguiente intento que sí dispare la comprobación con éxito.
    """
    level_code = descriptor_code.split(".", 1)[0]
    try:
        loaded = await load_descriptor_mastery(db, user_id, level_code)
        if loaded is None:
            return None
        level, descriptors, mastery_by_code, threshold = loaded

        criteria = await build_exit_criteria(db, user_id, level, descriptors, mastery_by_code, threshold)
        if not all(c.met for c in criteria):
            return None

        return await certify(db, user_id, level, source="auto")
    except Exception:
        logger.warning(
            "No se pudo evaluar la auto-certificación para descriptor=%s user=%s", descriptor_code, user_id,
            exc_info=True,
        )
        return None
