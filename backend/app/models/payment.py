import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Payment(Base):
    """Ledger de transacciones, una fila por intento de cobro — genérico
    entre las 4 pasarelas a propósito, igual que UserEvent: los detalles
    que varían por proveedor (cédula/teléfono/banco de Pago Móvil, el
    payload crudo de un webhook de PayPal/Stripe/Binance) van en
    `payload` JSONB en vez de columnas específicas por proveedor, para no
    tener que migrar el esquema cada vez que agregamos una pasarela nueva.

    NUNCA se sobreescribe una fila para "corregir" un pago — un
    reembolso, un rechazo posterior, etc. son filas/estados nuevos. Esta
    tabla es la fuente de verdad de auditoría de dinero: se apila, no se edita.
    """

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    # Nullable: se enlaza a una Subscription cuando el pago se aprueba y
    # activa (o renueva) el acceso — al crear el Payment todavía no existe
    # necesariamente esa Subscription (ej. Pago Móvil recién declarado).
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True
    )

    provider: Mapped[str] = mapped_column(String(20))  # paypal|credit_card|binance_pay|pago_movil
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # pending_verification: Pago Móvil recién declarado, esperando que un
    #   admin (o la automatización, cuando esté confirmada) lo revise.
    # approved: pago confirmado, activó/renovó una Subscription.
    # rejected: un admin lo revisó y NO correspondía a un pago real.
    # failed: la pasarela reportó el intento de cobro como fallido
    #   (tarjeta rechazada, etc.) — nunca llegó a haber dinero.
    # refunded: se aprobó y luego se devolvió.
    status: Mapped[str] = mapped_column(String(25), default="pending_verification")

    # Id de la transacción en la pasarela (order id de PayPal, payment_intent
    # de Stripe, id de transacción de Binance). Nulo en Pago Móvil hasta que
    # exista una automatización real que lo rellene.
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    payload: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Quién y cuándo lo revisó — solo aplica a la verificación MANUAL
    # (Pago Móvil hoy). Un pago aprobado automáticamente por un webhook
    # de PayPal/Stripe/Binance deja esto en null: no lo "revisó" un humano.
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    subscription: Mapped["Subscription | None"] = relationship()
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_id])

    def __repr__(self) -> str:
        return f"<Payment {self.provider} user={self.user_id} status={self.status}>"
