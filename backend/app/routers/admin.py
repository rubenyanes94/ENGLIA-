"""Autoría de contenido: crear/editar/borrar módulos, lecciones y
ejercicios sin pasar por un script de seed. Todo detrás de
get_current_admin — ningún endpoint aquí es alcanzable por un alumno normal.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_admin
from app.models import Exercise, Lesson, Module, Payment, Plan, User
from app.repositories import (
    exercise_repository,
    lesson_repository,
    level_repository,
    module_repository,
    payment_repository,
    plan_repository,
    subscription_repository,
)
from app.repositories.subscription_repository import BILLING_PERIOD
from app.schemas.billing import PaymentAdminOut, PaymentOut, PlanGatewayUpdate, PlanOut, RejectPaymentRequest
from app.schemas.exercise import ExerciseAdminOut, ExerciseCreate, ExerciseUpdate
from app.schemas.lesson import LessonAdminOut, LessonCreate, LessonUpdate
from app.schemas.module import ModuleCreate, ModuleOut, ModuleUpdate

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


# --- Módulos ---------------------------------------------------------------


@router.post("/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
async def create_module(payload: ModuleCreate, db: AsyncSession = Depends(get_db)) -> Module:
    level = await level_repository.get_by_code(db, payload.level_code)
    if level is None:
        raise HTTPException(status_code=404, detail=f"El nivel '{payload.level_code}' no existe.")

    return await module_repository.create(db, level.id, payload.title, payload.skill_focus, payload.order)


@router.patch("/modules/{module_id}", response_model=ModuleOut)
async def update_module(module_id: uuid.UUID, payload: ModuleUpdate, db: AsyncSession = Depends(get_db)) -> Module:
    module = await module_repository.get_by_id(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")

    return await module_repository.update(db, module, **payload.model_dump(exclude_unset=True))


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(module_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    module = await module_repository.get_by_id(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")

    try:
        await module_repository.delete(db, module)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede borrar: el módulo tiene lecciones o inscripciones de alumnos. Bórralas primero.",
        )


# --- Lecciones ---------------------------------------------------------------


@router.post("/modules/{module_id}/lessons", response_model=LessonAdminOut, status_code=status.HTTP_201_CREATED)
async def create_lesson(module_id: uuid.UUID, payload: LessonCreate, db: AsyncSession = Depends(get_db)) -> Lesson:
    module = await module_repository.get_by_id(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")

    return await lesson_repository.create(db, module_id, payload.title, payload.content, payload.order)


@router.patch("/lessons/{lesson_id}", response_model=LessonAdminOut)
async def update_lesson(lesson_id: uuid.UUID, payload: LessonUpdate, db: AsyncSession = Depends(get_db)) -> Lesson:
    lesson = await lesson_repository.get_by_id(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lección no encontrada.")

    return await lesson_repository.update(db, lesson, **payload.model_dump(exclude_unset=True))


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(lesson_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    lesson = await lesson_repository.get_by_id(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lección no encontrada.")

    try:
        await lesson_repository.delete(db, lesson)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede borrar: la lección tiene ejercicios. Bórralos primero.",
        )


# --- Ejercicios ---------------------------------------------------------------


@router.post("/lessons/{lesson_id}/exercises", response_model=ExerciseAdminOut, status_code=status.HTTP_201_CREATED)
async def create_exercise(lesson_id: uuid.UUID, payload: ExerciseCreate, db: AsyncSession = Depends(get_db)) -> Exercise:
    lesson = await lesson_repository.get_by_id(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lección no encontrada.")

    return await exercise_repository.create(db, lesson_id, payload.exercise_type, payload.prompt, payload.answer_key)


@router.patch("/exercises/{exercise_id}", response_model=ExerciseAdminOut)
async def update_exercise(
    exercise_id: uuid.UUID, payload: ExerciseUpdate, db: AsyncSession = Depends(get_db)
) -> Exercise:
    exercise = await exercise_repository.get_by_id(db, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado.")

    return await exercise_repository.update(db, exercise, **payload.model_dump(exclude_unset=True))


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise(exercise_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    exercise = await exercise_repository.get_by_id(db, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado.")

    await exercise_repository.delete(db, exercise)


# --- Facturación ---------------------------------------------------------------


@router.get("/payments", response_model=list[PaymentAdminOut])
async def list_pending_payments(db: AsyncSession = Depends(get_db)) -> list[Payment]:
    """La cola de Pago Móvil por revisar (los pagos automáticos de
    PayPal/Stripe/Binance nunca llegan aquí: entran ya 'approved' desde
    su propio webhook, sin pasar por un humano)."""
    return await payment_repository.list_pending_verification(db)


@router.post("/payments/{payment_id}/approve", response_model=PaymentOut)
async def approve_payment(
    payment_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Payment:
    """Confirma manualmente un pago de Pago Móvil (el admin ya comprobó
    la referencia/cédula/monto contra el estado de cuenta del banco) y
    activa la suscripción del alumno por un período.

    Nota para cuando exista la automatización mencionada que confirma
    pagos al instante: este es el mismo camino que debería tomar —
    llamar a esta función (o factorizarla si hace falta), no reinventar
    la activación en otro lado.
    """
    payment = await payment_repository.get_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")
    if payment.status != "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Este pago ya fue revisado (estado actual: '{payment.status}').",
        )

    plan_code = payment.payload.get("plan_code", "premium_monthly")
    plan = await plan_repository.get_by_code(db, plan_code)
    if plan is None:
        raise HTTPException(status_code=500, detail=f"El plan '{plan_code}' de este pago ya no existe.")

    # A diferencia de PayPal/Stripe/Binance, Pago Móvil no tiene una
    # Subscription "pending" creada de antemano (no hay checkout
    # redirigido) — se crea aquí mismo, directo a activa.
    subscription = await subscription_repository.create_pending(db, payment.user_id, plan, "pago_movil")
    period_start = datetime.utcnow()
    activated = await subscription_repository.activate(db, subscription, period_start, period_start + BILLING_PERIOD)

    return await payment_repository.mark_approved(db, payment, activated.id, reviewed_by_id=current_admin.id)


@router.post("/payments/{payment_id}/reject", response_model=PaymentOut)
async def reject_payment(
    payment_id: uuid.UUID,
    payload: RejectPaymentRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Payment:
    payment = await payment_repository.get_by_id(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")
    if payment.status != "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Este pago ya fue revisado (estado actual: '{payment.status}').",
        )

    return await payment_repository.mark_rejected(db, payment, current_admin.id, payload.reason)


@router.patch("/plans/{plan_id}/gateway-ids", response_model=PlanOut)
async def update_plan_gateway_ids(
    plan_id: uuid.UUID, payload: PlanGatewayUpdate, db: AsyncSession = Depends(get_db)
) -> Plan:
    """Para pegar aquí el price_id de Stripe / plan_id de PayPal una vez
    creados del lado de cada pasarela (ninguna de las dos deja crearlos
    "al vuelo" en cada checkout — es un paso previo manual, ver los
    avisos en app/billing/stripe_gateway.py y app/billing/paypal.py)."""
    plan = await plan_repository.get_by_id(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan no encontrado.")

    return await plan_repository.update_gateway_ids(db, plan, **payload.model_dump(exclude_unset=True))
