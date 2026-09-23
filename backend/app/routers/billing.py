"""Todo lo que el ALUMNO ve/hace de facturación: consultar planes, ver su
propia suscripción, iniciar un checkout, o declarar un pago por Pago
Móvil. La confirmación automática (webhooks) vive en routers/webhooks.py
— separado a propósito, porque esos endpoints NO llevan autenticación de
usuario (los llama la pasarela, no un alumno con JWT)."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import bcv_rate, binance_pay, paypal, stripe_gateway
from app.billing.period import period_end
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import Payment, Subscription, User
from app.repositories import payment_repository, plan_repository, subscription_repository
from app.schemas.billing import (
    BillingOptionsOut,
    BinancePersonalClaimRequest,
    BinancePersonalInfoOut,
    CheckoutRequest,
    CheckoutResponse,
    MySubscriptionOut,
    PagoMovilClaimRequest,
    PagoMovilInfoOut,
    PaymentMethodOut,
    PaymentOut,
    PlanOut,
    ProviderLiteral,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)) -> list[PlanOut]:
    return await plan_repository.list_active(db)


@router.get("/options", response_model=BillingOptionsOut)
async def billing_options(plan_code: str = "premium_monthly", db: AsyncSession = Depends(get_db)) -> BillingOptionsOut:
    """El plan y qué métodos de pago están operativos. Público: no dice
    nada que no diga ya la portada, y permite pintar las opciones antes de
    que el alumno termine de registrarse.

    "Disponible" = puede cobrar de verdad, no solo "tiene clave": la
    tarjeta necesita además el price_id del plan en Stripe, y PayPal su
    plan_id — sin ellos start_checkout respondería 503 al pulsar."""
    plan = await plan_repository.get_by_code(db, plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"El plan '{plan_code}' no existe.")
    return BillingOptionsOut(
        plan=plan,
        test_mode=_test_mode(),
        methods=[
            PaymentMethodOut(id="credit_card", available=stripe_gateway.is_configured() and bool(plan.stripe_price_id)),
            PaymentMethodOut(id="paypal", available=paypal.is_configured() and bool(plan.paypal_plan_id)),
            # Binance: la integración de comerciante si hay claves; si no, el
            # envío a la cuenta personal de la academia (verificación manual).
            PaymentMethodOut(
                id="binance_pay",
                available=binance_pay.is_configured() or _binance_personal_configured(),
                mode="merchant" if binance_pay.is_configured() else "personal",
            ),
            PaymentMethodOut(id="pago_movil", available=_pago_movil_configured()),
        ],
    )


def _test_mode() -> bool:
    """El atajo de pruebas solo existe en desarrollo. Es la ÚNICA condición:
    en producción (ENVIRONMENT distinto de "development") el botón no se
    muestra y el endpoint responde 404, aunque alguien lo llame a mano."""
    return settings.environment == "development"


@router.post("/test-payment", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def report_test_payment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Payment:
    """"Reportar pago" de PRUEBA: activa la suscripción sin pagar, para
    recorrer el flujo registro → pago aceptado → aula mientras las
    pasarelas no están configuradas.

    Va por el camino real, no por un atajo: crea un pago APROBADO de $0
    (provider "test", payload.test = true) y una suscripción de un periodo,
    así que prueba la misma regla de acceso que un pago de verdad. $0 para
    no inflar los ingresos del panel de gerencia; en Pagos sale como "Prueba".
    """
    if not _test_mode():
        raise HTTPException(status_code=404, detail="Not Found")
    plan = await plan_repository.get_by_code(db, "premium_monthly")
    if plan is None:
        raise HTTPException(status_code=404, detail="El plan 'premium_monthly' no existe.")

    now = datetime.utcnow()
    subscription = Subscription(
        user_id=current_user.id, plan_id=plan.id, provider="test", status="active",
        auto_renew=False, current_period_start=now, current_period_end=period_end(now),
    )
    db.add(subscription)
    await db.flush()
    payment = Payment(
        user_id=current_user.id, subscription_id=subscription.id, provider="test",
        amount_cents=0, currency=plan.currency, status="approved",
        payload={"test": True, "plan_code": plan.code}, reviewed_at=now,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


def _binance_personal_configured() -> bool:
    return bool(settings.binance_personal_qr_url and (settings.binance_personal_email or settings.binance_personal_pay_id or settings.binance_personal_nickname))


def _plan_amount(plan) -> str:
    """"10" y no "10.00" (pero "9.99" si toca): es lo que el alumno teclea en Binance."""
    return format((Decimal(plan.price_cents) / 100).normalize(), "f")


@router.get("/binance-info", response_model=BinancePersonalInfoOut)
async def get_binance_personal_info(
    plan_code: str = "premium_monthly",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BinancePersonalInfoOut:
    """Los datos de la cuenta de Binance de la academia para pagar a mano.
    Detrás de sesión, igual que los de Pago Móvil: son de una cuenta real."""
    plan = await plan_repository.get_by_code(db, plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"El plan '{plan_code}' no existe.")
    return BinancePersonalInfoOut(
        configured=_binance_personal_configured(),
        qr_url=settings.binance_personal_qr_url,
        nickname=settings.binance_personal_nickname,
        email=settings.binance_personal_email,
        pay_id=settings.binance_personal_pay_id,
        amount=_plan_amount(plan),
        asset=settings.binance_personal_asset,
    )


@router.post("/payments/binance", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def submit_binance_claim(
    payload: BinancePersonalClaimRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Payment:
    """El alumno ya envió los USDT a la cuenta personal y declara la orden.
    Entra en "pending_verification", como Pago Móvil: lo aprueba un admin
    tras encontrar la orden en el historial de Binance.

    El ID de la orden no se puede declarar dos veces: sin esto, dos
    alumnos podrían reclamar el mismo pago (o uno, varias veces)."""
    if not _binance_personal_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Binance todavía no está disponible.")
    plan = await plan_repository.get_by_code(db, payload.plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"El plan '{payload.plan_code}' no existe.")
    order_id = payload.order_id.strip()
    if await payment_repository.get_by_external_reference(db, "binance_pay", order_id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa orden de Binance ya fue declarada. Si crees que es un error, escríbenos.")

    return await payment_repository.create(
        db,
        user_id=current_user.id,
        provider="binance_pay",
        amount_cents=plan.price_cents,
        currency=plan.currency,
        external_reference=order_id,
        payload={
            "mode": "personal",
            "plan_code": plan.code,
            "order_id": order_id,
            "payer_account": payload.payer_account.strip(),
            "expected_amount": _plan_amount(plan),
            "asset": settings.binance_personal_asset,
            "paid_at": payload.paid_at.isoformat(),
        },
        status="pending_verification",
    )


def _pago_movil_configured() -> bool:
    return all([settings.pago_movil_bank, settings.pago_movil_document, settings.pago_movil_phone])


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


@router.get("/pago-movil-info", response_model=PagoMovilInfoOut)
async def get_pago_movil_info(
    plan_code: str = "premium_monthly",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PagoMovilInfoOut:
    """Los datos bancarios de la academia, para que el alumno transfiera.

    Salen de la configuración y no del código: son datos reales de una
    cuenta real, y quemarlos en el frontend obligaría a un despliegue para
    corregir un dígito de una cédula — con transferencias perdidas
    mientras tanto.
    """
    plan = await plan_repository.get_by_code(db, plan_code)
    rate = await bcv_rate.ensure_rate(db)
    return PagoMovilInfoOut(
        configured=_pago_movil_configured(),
        bank=settings.pago_movil_bank,
        document=settings.pago_movil_document,
        phone=settings.pago_movil_phone,
        amount_bs=_amount_bs(plan, rate),
        bs_per_usd=float(rate.rate) if rate else None,
        rate_date=rate.value_date if rate else None,
        rate_source=rate.source if rate else None,
    )


def _amount_bs(plan, rate: bcv_rate.ApplicableRate | None) -> float | None:
    """Precio del plan en bolívares, redondeado a céntimos como lo cobra el banco."""
    if plan is None or rate is None:
        return None
    return float((Decimal(plan.price_cents) / 100 * rate.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


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

    # Lo que la app le PIDIÓ pagar al alumno en ese momento: quien verifique
    # el pago compara el monto declarado contra este, no contra la tasa del
    # día en que lo revisa (que puede ser otra).
    rate = await bcv_rate.rate_for_today(db)

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
            "expected_amount_bs": _amount_bs(plan, rate),
            "bs_per_usd": str(rate.rate) if rate else None,
            "rate_value_date": rate.value_date.isoformat() if rate else None,
        },
        status="pending_verification",
    )
