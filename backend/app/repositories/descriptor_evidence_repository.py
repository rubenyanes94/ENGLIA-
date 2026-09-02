import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DescriptorEvidence
from app.repositories import descriptor_repository

# Defaults si CEFRLevel.mastery_rule viniera vacío (nivel sin currículo
# desarrollado todavía) — los valores reales de A1 vienen sembrados
# (documento § "mastery_rule": threshold 0.8, evidence_required 3).
DEFAULT_THRESHOLD = 0.8
DEFAULT_EVIDENCE_REQUIRED = 3


async def record(
    db: AsyncSession,
    user_id: uuid.UUID,
    descriptor_code: str,
    context: str,
    session_key: str,
    success: bool,
    source: str,
    scaffolded: bool = False,
) -> DescriptorEvidence:
    evidence = DescriptorEvidence(
        user_id=user_id,
        descriptor_code=descriptor_code,
        context=context,
        session_key=session_key,
        scaffolded=scaffolded,
        success=success,
        source=source,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return evidence


def _compute_mastery(
    ordered_rows: list[tuple[str, str, bool]], threshold: float, evidence_required: int
) -> float:
    """Aplica la regla de dominio (documento § 1.6) a las evidencias
    EXITOSAS de un solo descriptor, ya ordenadas cronológicamente:

    - Selecciona greedily hasta `evidence_required` evidencias cuyo
      `context` y `session_key` NO se hayan usado ya en la selección —
      así una evidencia con contexto o sesión repetidos respecto a una ya
      contada simplemente no suma (no rompe nada, solo no cuenta dos veces
      lo mismo como si fueran demostraciones distintas).
    - Si junta las requeridas Y al menos una fue sin andamiaje directo
      (`scaffolded=False`) -> dominado, mastery = threshold.
    - Si junta las requeridas pero TODAS tuvieron andamiaje -> le falta
      justo esa condición; se devuelve un poco por debajo del umbral
      (threshold - 0.05) en vez de threshold, para que sea visible en el
      progreso que está "casi" sin marcarlo como dominado.
    - Si no llega, mastery crece proporcional a cuánta evidencia válida
      lleva acumulada: threshold * (seleccionadas / requeridas).
    """
    if evidence_required <= 0:
        return 0.0

    used_contexts: set[str] = set()
    used_sessions: set[str] = set()
    selected_scaffolded: list[bool] = []

    for context, session_key, scaffolded in ordered_rows:
        if context in used_contexts or session_key in used_sessions:
            continue
        used_contexts.add(context)
        used_sessions.add(session_key)
        selected_scaffolded.append(scaffolded)
        if len(selected_scaffolded) >= evidence_required:
            break

    if len(selected_scaffolded) >= evidence_required:
        if any(not scaffolded for scaffolded in selected_scaffolded):
            return threshold
        return max(threshold - 0.05, 0.0)

    if not selected_scaffolded:
        return 0.0

    return round(threshold * (len(selected_scaffolded) / evidence_required), 3)


async def get_mastery_for_level(
    db: AsyncSession, user_id: uuid.UUID, level_id: uuid.UUID, threshold: float, evidence_required: int
) -> dict[str, float]:
    """mastery (0.0-threshold) por cada descriptor del nivel, para UN
    alumno — en una sola query (no N+1 por descriptor): trae toda la
    evidencia exitosa de los descriptores del nivel y agrupa en Python.
    Los descriptores sin ninguna evidencia quedan en 0.0 explícitamente
    (no se omiten): así el frontend puede pintar "27 de 27", no solo los
    que ya tienen algo.
    """
    codes = await descriptor_repository.list_codes_by_level_id(db, level_id)
    if not codes:
        return {}

    result = await db.execute(
        select(DescriptorEvidence.descriptor_code, DescriptorEvidence.context, DescriptorEvidence.session_key, DescriptorEvidence.scaffolded)
        .where(
            DescriptorEvidence.user_id == user_id,
            DescriptorEvidence.descriptor_code.in_(codes),
            DescriptorEvidence.success.is_(True),
        )
        .order_by(DescriptorEvidence.recorded_at)
    )

    rows_by_descriptor: dict[str, list[tuple[str, str, bool]]] = defaultdict(list)
    for descriptor_code, context, session_key, scaffolded in result.all():
        rows_by_descriptor[descriptor_code].append((context, session_key, scaffolded))

    return {
        code: _compute_mastery(rows_by_descriptor.get(code, []), threshold, evidence_required) for code in codes
    }
