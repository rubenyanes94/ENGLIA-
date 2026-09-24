"""Revisión manual de pagos: aprobar o rechazar los que entran en
"pending_verification" (Pago Móvil y Binance a la cuenta personal).

Un solo sitio para esta lógica, que usan tanto /admin como el panel de
gerencia (routers/payment_review.py): aprobar un pago da acceso de pago,
y no puede comportarse distinto según desde qué pantalla se pulse.

Dos garantías que antes no había:

1. **Aprobar dos veces no crea dos suscripciones.** Todo ocurre en UNA
   transacción que bloquea la fila del pago (SELECT ... FOR UPDATE) hasta
   el final. Antes había varios commits intermedios: dos personas que
   pulsaban "Aprobar" a la vez pasaban las dos la comprobación de
   "pendiente" y el alumno acababa con dos suscripciones.

2. **Renovar antes de que venza no hace perder días.** Pago Móvil y
   Binance no se renuevan solos: el alumno paga cada mes. Si paga cuando
   aún le quedan días, el periodo nuevo empieza al terminar el vigente,
   no hoy — si no, pagar a tiempo castigaría al que paga a tiempo.
"""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.period import local_date, period_end
from app.models import Payment, Subscription, User
from app.notifications import service as notifications
from app.notifications.messages import fecha_larga
from app.repositories import payment_repository, plan_repository, subscription_repository


async def _locked_pending(db: AsyncSession, payment_id: uuid.UUID) -> Payment:
    payment = (await db.execute(select(Payment).where(Payment.id == payment_id).with_for_update())).scalars().first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")
    if payment.status != "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Este pago ya fue revisado (estado actual: '{payment.status}').",
        )
    return payment


async def approve(db: AsyncSession, payment_id: uuid.UUID, reviewer_id: uuid.UUID) -> Payment:
    """Aprueba el pago y activa (o prolonga) el acceso del alumno un periodo."""
    payment = await _locked_pending(db, payment_id)

    plan_code = payment.payload.get("plan_code", "premium_monthly")
    plan = await plan_repository.get_by_code(db, plan_code)
    if plan is None:
        raise HTTPException(status_code=500, detail=f"El plan '{plan_code}' de este pago ya no existe.")

    now = datetime.utcnow()
    current = await subscription_repository.get_active(db, payment.user_id)
    start = max(now, current.current_period_end) if current is not None and current.current_period_end else now

    # Directo a "active" y sin pasar por create_pending/activate: esas
    # funciones hacen commit cada una y soltarían el bloqueo del pago.
    subscription = Subscription(
        user_id=payment.user_id,
        plan_id=plan.id,
        provider=payment.provider,
        status="active",
        auto_renew=False,  # revisión manual = el alumno vuelve a pagar a mano
        current_period_start=start,
        current_period_end=period_end(start),
    )
    db.add(subscription)
    await db.flush()

    payment.status = "approved"
    payment.subscription_id = subscription.id
    payment.reviewed_by_id = reviewer_id
    payment.reviewed_at = func.now()
    await db.commit()
    await db.refresh(payment)

    # "Ya puedes entrar y hasta cuándo". Se envía después del commit: el
    # acceso ya está dado, así que un fallo del correo no puede dejar al
    # alumno pagado y sin suscripción.
    await _avisar(db, payment.user_id, "pago_aprobado", payment.id, {"hasta": fecha_larga(local_date(subscription.current_period_end))})
    return payment


async def reject(db: AsyncSession, payment_id: uuid.UUID, reviewer_id: uuid.UUID, reason: str) -> Payment:
    payment = await _locked_pending(db, payment_id)
    rejected = await payment_repository.mark_rejected(db, payment, reviewer_id, reason)

    # Un rechazo sin avisar es la peor versión de esto: el alumno pierde
    # el acceso provisional de un momento a otro sin saber por qué.
    await _avisar(db, rejected.user_id, "pago_rechazado", rejected.id, {"motivo": reason})
    return rejected


async def _avisar(db: AsyncSession, user_id: uuid.UUID, kind: str, payment_id: uuid.UUID, context: dict) -> None:
    user = await db.get(User, user_id)
    if user is not None:
        # El id del pago en la clave: si el alumno reporta otro pago y
        # también se revisa, es un correo distinto y debe salir.
        await notifications.send(db, user, kind, dedupe_key=f"{kind}:{payment_id}", context=context)
