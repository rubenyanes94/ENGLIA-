"""Examen de un módulo: aprobarlo completa el módulo y desbloquea el siguiente.

Es la vía rápida para avanzar. El alumno que ya sabe lo que enseña un
módulo no tiene por qué recorrerlo entero: se presenta al examen y, si
aprueba, pasa al siguiente.

Tres decisiones que conviene conocer antes de tocar esto:

- Se aprueba por CONVOCATORIA. La nota del módulo es la de la mejor
  convocatoria completa (ver enrollment_repository.recompute_mastery), no
  la suma de los mejores aciertos sueltos de varias.
- El resultado NO dice qué respuesta era la correcta. Con cuatro opciones
  por pregunta, devolverla convierte el examen en suspender una vez,
  apuntarse las respuestas y aprobar a la segunda. Se dice qué
  capacidades repasar, que es lo que sirve para aprender.
- Las preguntas de examen solo se responden aquí, todas juntas. El
  endpoint de intento suelto las rechaza: por él se podría ir probando
  pregunta a pregunta hasta dar con la respuesta.
"""

import math
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.grading import grade_closed_exercise
from app.models import Descriptor, Enrollment, Exercise, ExerciseAttempt, Lesson, Module
from app.repositories import (
    descriptor_evidence_repository,
    enrollment_repository,
    event_repository,
    exercise_attempt_repository,
    module_repository,
)
from app.repositories.enrollment_repository import MASTERY_COMPLETION_THRESHOLD
from app.services import certification as certification_service


class ModuleLockedError(Exception):
    """El alumno intenta un módulo sin haber completado el anterior."""

    def __init__(self, previous_module: Module):
        self.previous_module = previous_module
        super().__init__(f"Debes completar el módulo '{previous_module.title}' antes de inscribirte en este.")


class ExamNotAvailableError(Exception):
    """El módulo todavía no tiene examen generado."""


@dataclass
class ExamReviewItem:
    descriptor_code: str
    statement_es: str


@dataclass
class ExamResult:
    score: float
    correct: int
    total: int
    pass_count: int
    passed: bool
    module_completed: bool
    next_module_id: uuid.UUID | None
    review: list[ExamReviewItem] = field(default_factory=list)


def pass_count_for(total: int) -> int:
    """Aciertos necesarios para aprobar. Con 8 preguntas y un umbral de
    0.7 salen 6: se redondea hacia arriba, porque 5 de 8 (0.625) no llega."""
    return math.ceil(MASTERY_COMPLETION_THRESHOLD * total - 1e-9)


async def ensure_enrollment(db: AsyncSession, user_id: uuid.UUID, module: Module) -> Enrollment:
    """Devuelve la inscripción del alumno en el módulo, creándola si hace falta.

    Aquí vive el bloqueo secuencial: no se puede empezar el módulo N sin
    haber completado el N-1 del mismo nivel. Lo usan tanto "Empezar módulo"
    como el examen, para que la regla no pueda divergir entre los dos
    caminos. Solo se mira el inmediato anterior: si ese se completó, los
    previos también.
    """
    existing = await enrollment_repository.get(db, user_id, module.id)
    if existing is not None:
        return existing

    previous_module = await module_repository.get_previous_in_level(db, module)
    if previous_module is not None:
        previous_enrollment = await enrollment_repository.get(db, user_id, previous_module.id)
        if previous_enrollment is None or previous_enrollment.status != "completed":
            raise ModuleLockedError(previous_module)

    enrollment = await enrollment_repository.create(db, user_id, module.id)
    await event_repository.record(db, user_id, "module_enrolled", {"module_id": str(module.id)})
    return enrollment


async def list_exam_exercises(db: AsyncSession, module_id: uuid.UUID) -> list[Exercise]:
    # Ordenadas por id: un orden estable entre la consulta de las preguntas
    # y la corrección, sin necesitar una columna de posición.
    result = await db.execute(
        select(Exercise)
        .join(Lesson)
        .where(Lesson.module_id == module_id, Exercise.stage == "exam")
        .order_by(Exercise.id)
    )
    return list(result.scalars().all())


async def record_descriptor_evidence(
    db: AsyncSession,
    user_id: uuid.UUID,
    exercise: Exercise,
    attempt: ExerciseAttempt,
    passed: bool,
    session_key: str,
) -> None:
    """Cuenta el intento como evidencia hacia los descriptores MCER que
    declara el ejercicio, y certifica el nivel si esa evidencia cierra su
    gate de salida.

    `context` es el ejercicio: repetir EL MISMO ejercicio no evidencia dos
    veces el mismo descriptor. `session_key` lo decide quien llama. En un
    examen es la convocatoria: dos preguntas del mismo descriptor en la
    misma convocatoria no pueden contar como dos sesiones distintas, que es
    lo que exige la regla de dominio. Nunca hay andamiaje en un ejercicio
    autocalificado, así que scaffolded es siempre False.
    """
    for descriptor_code in exercise.descriptor_codes:
        await descriptor_evidence_repository.record(
            db,
            user_id,
            descriptor_code,
            context=str(exercise.id),
            session_key=session_key,
            success=passed,
            source="exercise_attempt",
            scaffolded=False,
        )
        if passed:
            # Solo si acertó: un intento fallido no puede haber mejorado el
            # dominio de nadie.
            await certification_service.try_auto_certify_from_descriptor(db, user_id, descriptor_code)


async def submit_exam(
    db: AsyncSession, user_id: uuid.UUID, module: Module, answers: dict[str, str]
) -> ExamResult:
    exercises = await list_exam_exercises(db, module.id)
    if not exercises:
        raise ExamNotAvailableError()

    enrollment = await ensure_enrollment(db, user_id, module)
    was_completed = enrollment.status == "completed"
    sitting_id = uuid.uuid4()

    correct = 0
    failed_codes: list[str] = []
    for exercise in exercises:
        # Una pregunta sin responder se registra igual, con nota 0: la
        # convocatoria se puntúa sobre el examen entero, no sobre lo contestado.
        answer = answers.get(str(exercise.id), "")
        result = grade_closed_exercise(exercise.exercise_type, answer, exercise.answer_key)
        hit = result.score >= 1.0

        # Feedback neutro a propósito: grade_closed_exercise devuelve "La
        # respuesta esperada era...", y el alumno puede leer sus intentos
        # por GET .../attempts. Guardarlo filtraría la clave del examen.
        attempt = await exercise_attempt_repository.create(
            db,
            user_id,
            exercise.id,
            answer,
            result.score,
            "Correcta" if hit else "Incorrecta",
            exam_sitting=sitting_id,
        )
        await record_descriptor_evidence(db, user_id, exercise, attempt, hit, session_key=str(sitting_id))

        if hit:
            correct += 1
        else:
            failed_codes.extend(exercise.descriptor_codes)

    total = len(exercises)
    score = correct / total
    passed = score >= MASTERY_COMPLETION_THRESHOLD

    updated = await enrollment_repository.recompute_mastery(db, user_id, module.id)
    module_completed = updated is not None and updated.status == "completed"

    await event_repository.record(
        db,
        user_id,
        "module_exam_submitted",
        {"module_id": str(module.id), "sitting": str(sitting_id), "score": score, "passed": passed},
    )
    if module_completed and not was_completed:
        await event_repository.record(
            db, user_id, "module_completed", {"module_id": str(module.id), "mastery_score": updated.mastery_score}
        )

    next_module = await module_repository.get_next_in_level(db, module) if module_completed else None

    return ExamResult(
        score=score,
        correct=correct,
        total=total,
        pass_count=pass_count_for(total),
        passed=passed,
        module_completed=module_completed,
        next_module_id=next_module.id if next_module else None,
        review=await _review_items(db, failed_codes),
    )


async def _review_items(db: AsyncSession, codes: list[str]) -> list[ExamReviewItem]:
    unique_codes = list(dict.fromkeys(codes))
    if not unique_codes:
        return []
    result = await db.execute(select(Descriptor).where(Descriptor.code.in_(unique_codes)))
    statements = {descriptor.code: descriptor.statement_es for descriptor in result.scalars()}
    return [ExamReviewItem(descriptor_code=code, statement_es=statements.get(code, code)) for code in unique_codes]
