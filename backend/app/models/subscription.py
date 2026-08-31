import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Subscription(Base):
    """El derecho de acceso de un alumno, con vigencia. Se permite más de
    una fila por alumno a lo largo del tiempo (historial: canceló,
    volvió a pagar, cambió de pasarela...) — "la suscripción activa
    actual" es una QUERY (ver subscription_repository.get_active), no
    una relación 1-a-1 forzada por el esquema.
    """

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"))

    # pending: se creó pero todavía no hay pago confirmado (ej. esperando
    #   verificación manual de Pago Móvil, o el alumno no completó el
    #   checkout de PayPal/Stripe).
    # active: acceso vigente.
    # past_due: una pasarela recurrente (PayPal/Stripe) avisó que el cobro
    #   del mes falló, pero todavía no cancelamos el acceso (grace period).
    # canceled: el alumno canceló, o el pago fue rechazado.
    # expired: se venció current_period_end y no hubo renovación (típico
    #   de Binance Pay / Pago Móvil, que no cobran solos cada mes).
    status: Mapped[str] = mapped_column(String(20), default="pending")

    provider: Mapped[str] = mapped_column(String(20))  # paypal|credit_card|binance_pay|pago_movil

    # Solo tiene sentido para PayPal/Stripe: el id de SU suscripción
    # recurrente, para poder cancelarla del lado del proveedor o cruzar
    # eventos de webhook contra esta fila. Nulo en Binance Pay/Pago Móvil.
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Si la pasarela recobra sola el mes que viene (PayPal/Stripe) o si
    # el alumno tiene que volver a pagar a mano (Binance Pay/Pago Móvil).
    # El frontend lo usa para avisar "tu acceso vence el X, renuévalo" en
    # vez de asumir que se renueva solo.
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)

    current_period_start: Mapped[datetime | None] = mapped_column(nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship()
    plan: Mapped["Plan"] = relationship()

    def __repr__(self) -> str:
        return f"<Subscription user={self.user_id} status={self.status} provider={self.provider}>"
