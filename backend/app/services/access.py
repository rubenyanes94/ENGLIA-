"""¿Puede este usuario usar la app de alumno? La regla, en un solo sitio.

La usan el candado de los endpoints (core/deps.require_access) y /auth/me,
para que el frontend decida a dónde mandar al usuario con la MISMA
respuesta que luego aplicará el backend.

Tiene acceso quien cumpla cualquiera de estas, en este orden:
1. Es del equipo (admin o gerencia).
2. Está exento (access_exempt): las cuentas que ya existían cuando se
   activó el cobro, o a quien se le regale el acceso.
3. Tiene una suscripción vigente.
4. Tiene un pago MANUAL (Pago Móvil o Binance personal) declarado y aún
   sin revisar: acceso provisional mientras se verifica. Si se rechaza,
   deja de estar pendiente y el acceso se va en la siguiente petición.
   (Decisión de negocio: el alumno no espera horas a que alguien revise.)
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, User
from app.repositories import subscription_repository

STAFF_ROLES = ("admin", "manager")
MANUAL_PROVIDERS = ("pago_movil", "binance_pay")


@dataclass(frozen=True)
class AccessStatus:
    has_access: bool
    # staff | exempt | subscription | pending_payment | None (sin acceso)
    reason: str | None
    # Si el último pago se rechazó: el motivo, para explicárselo en la
    # pantalla de pago en vez de devolverlo ahí sin decir por qué.
    last_rejection_reason: str | None = None


async def access_status(db: AsyncSession, user: User) -> AccessStatus:
    if user.role in STAFF_ROLES:
        return AccessStatus(True, "staff")
    if user.access_exempt:
        return AccessStatus(True, "exempt")
    if await subscription_repository.get_active(db, user.id) is not None:
        return AccessStatus(True, "subscription")

    latest = (
        await db.execute(
            select(Payment)
            .where(Payment.user_id == user.id, Payment.provider.in_(MANUAL_PROVIDERS))
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if latest is not None and latest.status == "pending_verification":
        return AccessStatus(True, "pending_payment")
    rejection = (latest.payload or {}).get("rejection_reason") if latest is not None and latest.status == "rejected" else None
    return AccessStatus(False, None, rejection)
