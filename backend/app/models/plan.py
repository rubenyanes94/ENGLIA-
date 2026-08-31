import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Plan(Base):
    """Catálogo de planes de suscripción. Hoy solo hay uno ($10/mes,
    acceso a todo), pero es tabla (no una constante en código) porque un
    SaaS de precios casi siempre termina necesitando un segundo plan
    (anual, con descuento, etc.) — mejor no tener que migrar cuando pase.

    price_cents en vez de un Float: nunca representes dinero como punto
    flotante (errores de redondeo binario). $10.00 = 1000.
    """

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # "premium_monthly"
    name: Mapped[str] = mapped_column(String(100))  # "Premium Mensual"
    price_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    interval: Mapped[str] = mapped_column(String(10), default="month")  # "month" | "year"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # IDs del MISMO plan en cada pasarela que maneja "suscripciones" del
    # lado del proveedor (PayPal y Stripe sí; Binance Pay y Pago Móvil no
    # tienen ese concepto, se cobran orden a orden). Nullable: un plan
    # puede no estar dado de alta todavía en una pasarela concreta.
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paypal_plan_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Plan {self.code}>"
