import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import Enrollment, User
from app.repositories import enrollment_repository, lesson_repository, module_repository
from app.schemas.enrollment import EnrollmentOut
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

    response.status_code = status.HTTP_201_CREATED
    return await enrollment_repository.create(db, current_user.id, module_id)
