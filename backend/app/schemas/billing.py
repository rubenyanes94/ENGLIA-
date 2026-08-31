import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.auth import UserOut


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    price_cents: int
    currency: str
    interval: str


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    provider: str
    auto_renew: bool
    current_period_start: datetime | None
    current_period_end: datetime | None
    canceled_at: datetime | None
    plan: PlanOut


class MySubscriptionOut(BaseModel):
    """`has_access` ya viene calculado (no solo status=="active" — también
    chequea la fecha, ver subscription_repository.get_active): el
    frontend no debería tener que reimplementar esa lógica."""

    has_access: bool
    subscription: SubscriptionOut | None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    amount_cents: int
    currency: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None


class CheckoutRequest(BaseModel):
    plan_code: str = "premium_monthly"


class CheckoutResponse(BaseModel):
    """A dónde redirigir al alumno para completar el pago (PayPal
    approval link, Stripe Checkout, o el checkout de Binance Pay).
    Pago Móvil no usa esto — no hay redirección, es un formulario propio."""

    checkout_url: str
    provider: str


class PagoMovilClaimRequest(BaseModel):
    """Lo que el alumno declara después de hacer la transferencia por
    Pago Móvil. Nada de esto se puede verificar automáticamente todavía
    (la automatización mencionada está por confirmar) — entra directo a
    la cola de revisión manual, ver GET /admin/payments."""

    plan_code: str = "premium_monthly"
    payer_cedula: str
    payer_phone: str
    payer_bank: str
    reference_number: str
    amount_bs: float  # monto en bolívares, tal cual lo ve el alumno en su comprobante
    paid_at: datetime  # fecha/hora que el alumno declara haber hecho la transferencia


class PaymentAdminOut(BaseModel):
    """Lo que ve un admin en la cola de revisión: a diferencia de
    PaymentOut, SÍ incluye `payload` (cédula/teléfono/banco/referencia
    de Pago Móvil) y quién es el alumno — sin esto no hay forma de
    verificar nada contra el estado de cuenta del banco."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    amount_cents: int
    currency: str
    status: str
    external_reference: str | None
    payload: dict
    created_at: datetime
    user: UserOut


class RejectPaymentRequest(BaseModel):
    reason: str


class PlanGatewayUpdate(BaseModel):
    """Separado de un ModuleUpdate-style genérico a propósito: estos dos
    campos son credenciales de integración, no contenido — solo tiene
    sentido tocarlos al conectar/reconectar una pasarela, nunca como
    parte de "editar el plan"."""

    stripe_price_id: str | None = None
    paypal_plan_id: str | None = None


ProviderLiteral = Literal["paypal", "credit_card", "binance_pay"]
