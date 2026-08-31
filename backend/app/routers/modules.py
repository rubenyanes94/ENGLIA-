import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.grading import CLOSED_EXERCISE_TYPES, grade_closed_exercise, grade_open_exercise
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import Enrollment, ExerciseAttempt, User
from app.repositories import (
    enrollment_repository,
    event_repository,
    exercise_attempt_repository,
    exercise_repository,
    lesson_repository,
    module_repository,
)
from app.schemas.enrollment import EnrollmentOut
from app.schemas.exercise import ExerciseAttemptOut, SubmitExerciseAttemptRequest
from app.schemas.lesson import LessonDetailOut
from app.schemas.module import ModuleDetailOut

router = APIRouter(prefix="/modules", tags=["curriculum"])


@router.get("/{module_id}", response_model=ModuleDetailOut)
async def get_module(module_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ModuleDetailOut:
    """Detalle de un módulo con el índice de sus lecciones (resumen, sin
    contenido — para eso está GET .../lessons/{lesson_id})."""
    module = await module_repository.get_with_lessons(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")
    return module


@router.get("/{module_id}/lessons/{lesson_id}", response_model=LessonDetailOut)
async def get_lesson(module_id: uuid.UUID, lesson_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> LessonDetailOut:
    lesson = await lesson_repository.get_with_exercises(db, module_id, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lección no encontrada.")
    return lesson


@router.post("/{module_id}/enroll", response_model=EnrollmentOut)
async def enroll_in_module(
    module_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Enrollment:
    """Inscribe al alumno autenticado en el módulo.

    Idempotente a propósito: si ya estaba inscrito, devuelve la
    inscripción existente tal cual (200) en vez de fallar o resetear su
    progreso — un doble click en "Empezar módulo" en el frontend no
    debe tener efectos secundarios.
    """
    module = await module_repository.get_by_id(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")

    existing = await enrollment_repository.get(db, current_user.id, module_id)
    if existing is not None:
        return existing

    # Bloqueo secuencial: para certificar un nivel en orden, no se puede
    # empezar el módulo N sin haber completado (examen aprobado) el N-1
    # del MISMO nivel. Solo se compara contra el inmediato anterior, no
    # contra todos los previos — si esos ya se completaron en su momento,
    # encadenar la comprobación hacia atrás sería redundante.
    previous_module = await module_repository.get_previous_in_level(db, module)
    if previous_module is not None:
        previous_enrollment = await enrollment_repository.get(db, current_user.id, previous_module.id)
        if previous_enrollment is None or previous_enrollment.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Debes completar el módulo '{previous_module.title}' antes de inscribirte en este.",
            )

    response.status_code = status.HTTP_201_CREATED
    new_enrollment = await enrollment_repository.create(db, current_user.id, module_id)
    await event_repository.record(db, current_user.id, "module_enrolled", {"module_id": str(module_id)})
    return new_enrollment


@router.post(
    "/{module_id}/lessons/{lesson_id}/exercises/{exercise_id}/attempts",
    response_model=ExerciseAttemptOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_exercise_attempt(
    module_id: uuid.UUID,
    lesson_id: uuid.UUID,
    exercise_id: uuid.UUID,
    payload: SubmitExerciseAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExerciseAttempt:
    """Envía una respuesta, la corrige (determinista o con IA según el
    tipo) y actualiza el progreso del módulo con el resultado."""
    exercise = await exercise_repository.get_for_lesson(db, module_id, lesson_id, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado.")

    # Exigimos inscripción previa a propósito: mastery_score se calcula
    # sobre una Enrollment que tiene que existir ya (ver
    # enrollment_repository.recompute_mastery) — sin esto, un intento
    # "huérfano" no tendría dónde reflejar el progreso.
    enrollment = await enrollment_repository.get(db, current_user.id, module_id)
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Debes inscribirte en el módulo antes de hacer sus ejercicios.",
        )

    if exercise.exercise_type in CLOSED_EXERCISE_TYPES:
        result = grade_closed_exercise(exercise.exercise_type, payload.answer, exercise.answer_key)
    else:
        result = await grade_open_exercise(
            prompt=exercise.prompt,
            student_answer=payload.answer,
            level_code=exercise.lesson.module.level.code,
            model_id=settings.llm_model,
        )

    attempt = await exercise_attempt_repository.create(
        db, current_user.id, exercise_id, payload.answer, result.score, result.feedback
    )
    await event_repository.record(
        db,
        current_user.id,
        "exercise_attempt_submitted",
        {"exercise_id": str(exercise_id), "exercise_type": exercise.exercise_type, "score": result.score},
    )

    # Recalcula mastery_score/estado del módulo con este intento ya
    # incluido — el progreso se actualiza solo, sin que el frontend tenga
    # que saber cuándo pedirlo aparte.
    was_completed = enrollment.status == "completed"
    updated_enrollment = await enrollment_repository.recompute_mastery(db, current_user.id, module_id)

    # Evento aparte (no fusionado con exercise_attempt_submitted): un
    # dashboard de producto quiere poder contar "módulos completados" sin
    # tener que reconstruir esa transición a partir de scores sueltos.
    if updated_enrollment is not None and updated_enrollment.status == "completed" and not was_completed:
        await event_repository.record(
            db,
            current_user.id,
            "module_completed",
            {"module_id": str(module_id), "mastery_score": updated_enrollment.mastery_score},
        )

    return attempt


@router.get(
    "/{module_id}/lessons/{lesson_id}/exercises/{exercise_id}/attempts",
    response_model=list[ExerciseAttemptOut],
)
async def list_exercise_attempts(
    module_id: uuid.UUID,
    lesson_id: uuid.UUID,
    exercise_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ExerciseAttempt]:
    """Historial de intentos del PROPIO alumno sobre este ejercicio (útil
    para repintar el feedback si recarga la página, o para mostrar el
    progreso de reintentos)."""
    exercise = await exercise_repository.get_for_lesson(db, module_id, lesson_id, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado.")

    return await exercise_attempt_repository.list_for_exercise(db, current_user.id, exercise_id)
