from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.repositories import descriptor_repository, enrollment_repository, level_repository, module_repository
from app.schemas.certification import CertificationProgressOut
from app.schemas.descriptor import DescriptorOut
from app.schemas.level import CEFRLevelOut
from app.schemas.module import ModuleOut, ModuleProgressOut

router = APIRouter(prefix="/levels", tags=["levels"])


@router.get("", response_model=list[CEFRLevelOut])
async def get_levels(db: AsyncSession = Depends(get_db)) -> list[CEFRLevelOut]:
    """Devuelve los 6 niveles MCER, ordenados de A1 a C2."""
    levels = await level_repository.list_levels(db)
    return levels


@router.get("/{level_code}/modules", response_model=list[ModuleOut])
async def get_level_modules(level_code: str, db: AsyncSession = Depends(get_db)) -> list[ModuleOut]:
    """Índice de módulos de un nivel (ej. GET /levels/A1/modules).

    Comprobamos que el nivel exista antes de listar para poder distinguir
    "nivel inválido" (404) de "nivel válido pero sin módulos todavía" ([]).
    """
    level = await level_repository.get_by_code(db, level_code)
    if level is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")

    return await module_repository.list_by_level_code(db, level_code)


@router.get("/{level_code}/descriptors", response_model=list[DescriptorOut])
async def get_level_descriptors(level_code: str, db: AsyncSession = Depends(get_db)) -> list[DescriptorOut]:
    """Catálogo de descriptores MCER ("can-do") de un nivel — la unidad
    atómica de progreso (documento de currículo § 1.6), sin nada
    personalizado por alumno (ver /users/me/progress/descriptors/{code}
    para el dominio acumulado de QUIEN llama)."""
    level = await level_repository.get_by_code(db, level_code)
    if level is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")

    return await descriptor_repository.list_by_level_code(db, level_code)


@router.get("/{level_code}/certification-progress", response_model=CertificationProgressOut)
async def get_certification_progress(
    level_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CertificationProgressOut:
    """El mapa de progreso hacia certificar un nivel: estado de cada
    módulo (locked/available/in_progress/completed) y horas certificadas
    del rango objetivo (CEFRLevel.target_hours_*).

    El bloqueo se camina secuencialmente por Module.order: el primer
    módulo siempre está "available"; a partir de ahí, un módulo está
    "locked" si el anterior no quedó "completed" — el mismo criterio que
    ya aplica POST /modules/{id}/enroll (ver module_repository.get_previous_in_level),
    solo que aquí se calcula para LOS 8 de una vez en vez de uno por uno.
    """
    level = await level_repository.get_by_code(db, level_code)
    if level is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{level_code}' no existe.")

    modules = await module_repository.list_by_level_code(db, level_code)
    enrollments = await enrollment_repository.list_for_user(db, current_user.id)
    enrollment_by_module_id = {e.module_id: e for e in enrollments}

    modules_out: list[ModuleProgressOut] = []
    hours_completed = 0.0
    previous_completed = True  # el primer módulo del nivel siempre está disponible

    for module in modules:
        enrollment = enrollment_by_module_id.get(module.id)

        if not previous_completed:
            module_status = "locked"
        elif enrollment is None:
            module_status = "available"
        else:
            module_status = enrollment.status  # "in_progress" | "completed"
            hours_completed += module.estimated_hours * enrollment.mastery_score

        modules_out.append(
            ModuleProgressOut(
                id=module.id,
                code=module.code,
                title=module.title,
                title_es=module.title_es,
                skill_focus=module.skill_focus,
                order=module.order,
                estimated_hours=module.estimated_hours,
                descriptors=module.descriptors,
                communicative_objectives=module.communicative_objectives,
                status=module_status,
            )
        )
        previous_completed = enrollment is not None and enrollment.status == "completed"

    percentage = round((hours_completed / level.target_hours_max) * 100, 1) if level.target_hours_max else 0.0

    return CertificationProgressOut(
        level_code=level.code,
        target_hours_min=level.target_hours_min,
        target_hours_max=level.target_hours_max,
        hours_completed=round(hours_completed, 1),
        percentage=min(percentage, 100.0),
        modules=modules_out,
    )
