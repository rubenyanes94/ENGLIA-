"""Todo lo que el ALUMNO ve/hace de facturación: consultar planes, ver su
propia suscripción, iniciar un checkout, o declarar un pago por Pago
Móvil. La confirmación automática (webhooks) vive en routers/webhooks.py
— separado a propósito, porque esos endpoints NO llevan autenticación de
usuario (los llama la pasarela, no un alumno con JWT)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import binance_pay, paypal, stripe_gateway
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import Payment, User
from app.repositories import payment_repository, plan_repository, subscription_repository
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    MySubscriptionOut,
    PagoMovilClaimRequest,
    PaymentOut,
    PlanOut,
    ProviderLiteral,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)) -> list[PlanOut]:
    return await plan_repository.list_active(db)


@router.get("/subscription", response_model=MySubscriptionOut)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MySubscriptionOut:
    subscription = await subscription_repository.get_active(db, current_user.id)
    return MySubscriptionOut(has_access=subscription is not None, subscription=subscription)


@router.get("/payments/me", response_model=list[PaymentOut])
async def list_my_payments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Payment]:
    return await payment_repository.list_for_user(db, current_user.id)


@router.post("/checkout/{provider}", response_model=CheckoutResponse)
async def start_checkout(
    provider: ProviderLiteral,
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Inicia el pago con una pasarela que REDIRIGE al alumno a completarlo
    (PayPal, Stripe, Binance Pay). Pago Móvil no pasa por aquí — no hay
    redirección, es una declaración directa (POST /billing/payments/pago-movil).

    Para las tres, el patrón es el mismo: creamos una Subscription en
    "pending" ANTES de llamar a la pasarela, y le pasamos su id — así el
    webhook que confirme el pago sabe EXACTAMENTE qué fila activar, sin
    tener que adivinar ni cruzar por email.
    """
    plan = await plan_repository.get_by_code(db, payload.plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"El plan '{payload.plan_code}' no existe.")

    if provider == "paypal":
        if not paypal.is_configured():
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PayPal no está configurado todavía.")
        subscription = await subscription_repository.create_pending(db, current_user.id, plan, "paypal")
        try:
            result = await paypal.create_subscription(str(subscription.id), current_user.email, plan)
        except ValueError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
        subscription.provider_subscription_id = result["provider_subscription_id"]
        await db.commit()
        return CheckoutResponse(checkout_url=result["approval_url"], provider="paypal")

    if provider == "credit_card":
        if not stripe_gateway.is_configured():
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "El pago con tarjeta no está configurado todavía.")
        subscription = await subscription_repository.create_pending(db, current_user.id, plan, "credit_card")
        try:
            checkout_url = await stripe_gateway.create_checkout_session(str(subscription.id), current_user.email, plan)
        except ValueError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
        return CheckoutResponse(checkout_url=checkout_url, provider="credit_card")

    # provider == "binance_pay"
    if not binance_pay.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Binance Pay no está configurado todavía.")
    subscription = await subscription_repository.create_pending(db, current_user.id, plan, "binance_pay")
    result = await binance_pay.create_order(str(subscription.id), plan)
    subscription.provider_subscription_id = str(subscription.id)  # ver nota en binance_pay.create_order
    await db.commit()
    return CheckoutResponse(checkout_url=result["checkout_url"], provider="binance_pay")


@router.post("/payments/pago-movil", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def submit_pago_movil_claim(
    payload: PagoMovilClaimRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Payment:
    """El alumno ya transfirió por Pago Móvil y declara los datos para que
    lo verifiquemos: cédula, teléfono y banco de origen + la referencia.

    Entra SIEMPRE en "pending_verification" — no hay atajo de
    auto-aprobación aquí todavía (la automatización que confirma pagos al
    instante está por confirmar del lado del negocio; cuando esté lista,
    el cambio es en routers/webhooks.py, no aquí: este endpoint sigue
    siendo "el alumno declara", solo cambiaría quién lo revisa después).
    """
    plan = await plan_repository.get_by_code(db, payload.plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"El plan '{payload.plan_code}' no existe.")

    return await payment_repository.create(
        db,
        user_id=current_user.id,
        provider="pago_movil",
        amount_cents=plan.price_cents,
        currency=plan.currency,
        payload={
            "plan_code": plan.code,
            "payer_cedula": payload.payer_cedula,
            "payer_phone": payload.payer_phone,
            "payer_bank": payload.payer_bank,
            "reference_number": payload.reference_number,
            "amount_bs": payload.amount_bs,
            "paid_at": payload.paid_at.isoformat(),
        },
        status="pending_verification",
    )
