import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Enrollment, Exercise, ExerciseAttempt, Lesson, Module

# A partir de qué mastery_score se considera "dominado" un módulo. 0.7 en
# vez de 1.0 a propósito: exigir el intento PERFECTO en cada ejercicio
# para marcar un módulo como completado sería frustrante y no refleja
# cómo se evalúa el dominio de un idioma en la práctica.
MASTERY_COMPLETION_THRESHOLD = 0.7


async def get(db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID) -> Enrollment | None:
    result = await db.execute(
        select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.module_id == module_id)
    )
    return result.scalars().first()


async def create(db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID) -> Enrollment:
    enrollment = Enrollment(
        user_id=user_id,
        module_id=module_id,
        status="in_progress",
        started_at=func.now(),
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Enrollment]:
    """Trae module + level ya cargados: el endpoint de progreso necesita
    module.title y module.level.code para cada inscripción, y sin este
    joinedload encadenado sería un N+1 (o un MissingGreenlet) por fila."""
    result = await db.execute(
        select(Enrollment)
        .options(joinedload(Enrollment.module).joinedload(Module.level))
        .where(Enrollment.user_id == user_id)
        .order_by(Enrollment.started_at)
    )
    return list(result.unique().scalars().all())


async def recompute_mastery(db: AsyncSession, user_id: uuid.UUID, module_id: uuid.UUID) -> Enrollment | None:
    """Recalcula mastery_score tras un nuevo intento de ejercicio.

    mastery_score = promedio del MEJOR intento de CADA ejercicio del
    módulo. Dos decisiones deliberadas:

    - La nota es la de la MEJOR CONVOCATORIA completa del examen, no el
      mejor intento de cada pregunta por separado. Antes se tomaba el
      máximo de cada pregunta entre todos los intentos, así que se podía
      acertar la mitad en una convocatoria, la otra mitad en otra, y
      completar el módulo sin haber aprobado nunca un examen. Con un
      examen que decide si el alumno avanza, eso lo convertía en un
      juego de ensayo y error.
    - "Mejor" convocatoria, no "última": volver a presentarse y sacar
      peor nota no debe quitarle al alumno un módulo que ya aprobó.
    - Las preguntas que no se respondieron en una convocatoria cuentan
      como 0: el denominador es el examen entero, no lo que se contestó.
    - Solo se promedian ejercicios stage="exam". Los de práctica se
      corrigen igual (el alumno ve su nota y feedback), pero
      deliberadamente NO mueven mastery_score — practicar y fallar no
      debe sentirse como retroceder en el progreso oficial del módulo.

    Llamar a esto es responsabilidad del router tras crear un
    ExerciseAttempt — no vive en exercise_attempt_repository.create()
    para no acoplar "guardar un intento" con "esto pertenece a un
    módulo con inscripción", que son conceptos separados.
    """
    enrollment = await get(db, user_id, module_id)
    if enrollment is None:
        return None

    result = await db.execute(
        select(Exercise.id).join(Lesson).where(Lesson.module_id == module_id, Exercise.stage == "exam")
    )
    exercise_ids = [row[0] for row in result.all()]
    if not exercise_ids:
        return enrollment

    sitting = ExerciseAttempt.response["exam_sitting"].astext
    result = await db.execute(
        select(sitting, func.sum(ExerciseAttempt.score))
        .where(
            ExerciseAttempt.user_id == user_id,
            ExerciseAttempt.exercise_id.in_(exercise_ids),
            # Un intento de examen sin convocatoria no debería existir (el
            # endpoint suelto rechaza las preguntas de examen); si apareciera,
            # no puede sumar a ninguna convocatoria.
            sitting.is_not(None),
        )
        .group_by(sitting)
    )
    sitting_totals = [total for _, total in result.all()]

    mastery = max(sitting_totals, default=0.0) / len(exercise_ids)

    enrollment.mastery_score = mastery
    if mastery >= MASTERY_COMPLETION_THRESHOLD:
        if enrollment.status != "completed":
            enrollment.status = "completed"
            enrollment.completed_at = func.now()
    elif enrollment.status == "not_started":
        enrollment.status = "in_progress"

    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def get_skill_breakdown(db: AsyncSession, user_id: uuid.UUID) -> dict[str, float]:
    """mastery_score promedio agrupado por Module.skill_focus, entre los
    módulos en los que el alumno está (o estuvo) inscrito — es lo que
    alimenta las barras "Listening/Speaking/Reading/Writing" del
    dashboard de progreso.

    A propósito solo promedia módulos CON inscripción, no todos los
    módulos del sistema: un alumno de A1 no debería ver su "Writing" en
    0% solo porque nunca tocó los módulos de writing de C1 — esa
    destreza sencillamente todavía no tiene datos (el router decide qué
    mostrar cuando una destreza no aparece aquí).
    """
    result = await db.execute(
        select(Module.skill_focus, func.avg(Enrollment.mastery_score))
        .join(Enrollment, Enrollment.module_id == Module.id)
        .where(Enrollment.user_id == user_id)
        .group_by(Module.skill_focus)
    )
    return {skill_focus: float(avg_mastery) for skill_focus, avg_mastery in result.all()}
