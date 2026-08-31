"""Notificaciones asíncronas de las pasarelas — NINGÚN endpoint aquí
lleva autenticación de usuario (los llama el servidor de PayPal/Stripe/
Binance, no un alumno con JWT). La autenticidad se verifica con la firma
propia de cada proveedor, siempre ANTES de tocar la base de datos: un
webhook sin verificar es "cualquiera en internet puede activarse una
suscripción gratis con un POST".

AVISO GENERAL: ninguno de los tres handlers ha corrido contra un webhook
real todavía (no hay cuentas/sandboxes conectados en este entorno).
Siguen la forma documentada por cada proveedor — necesitan una pasada de
verificación con credenciales reales antes de producción.

Idempotencia: las tres pasarelas REINTENTAN un webhook si no reciben un
200 a tiempo (o incluso a veces sin motivo aparente) — por eso cada
handler comprueba payment_repository.get_by_external_reference() antes
de crear nada, para que procesar el mismo evento dos veces no active la
suscripción "por partida doble" ni duplique el pago en el ledger.
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import binance_pay, paypal, stripe_gateway
from app.core.db import get_db
from app.repositories import payment_repository, plan_repository, subscription_repository
from app.repositories.subscription_repository import BILLING_PERIOD

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw_body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        await stripe_gateway.verify_webhook(raw_body, sig_header)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Firma de webhook inválida.")

    # Usamos el JSON crudo ya verificado, no el objeto stripe.Event del
    # SDK, para guardar en `payload` un dict plano sin envolturas propias
    # del SDK (StripeObject) que compliquen la serialización a JSONB.
    event = json.loads(raw_body)
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        subscription_id = data.get("client_reference_id")
        checkout_session_id = data.get("id")
        if subscription_id and checkout_session_id:
            subscription = await subscription_repository.get_by_id(db, uuid.UUID(subscription_id))
            existing = await payment_repository.get_by_external_reference(db, "credit_card", checkout_session_id)
            if subscription is not None and existing is None:
                plan = await plan_repository.get_by_id(db, subscription.plan_id)
                period_start = datetime.utcnow()
                activated = await subscription_repository.activate(
                    db,
                    subscription,
                    period_start,
                    period_start + BILLING_PERIOD,
                    provider_subscription_id=data.get("subscription"),
                )
                await payment_repository.create(
                    db,
                    user_id=subscription.user_id,
                    provider="credit_card",
                    amount_cents=plan.price_cents,
                    currency=plan.currency,
                    payload=event,
                    external_reference=checkout_session_id,
                    status="approved",
                    subscription_id=activated.id,
                )

    elif event_type == "invoice.paid":
        # Dispara en CADA cobro recurrente, no solo el primero — esto es
        # lo que renueva el período mes a mes sin que el alumno haga nada.
        stripe_subscription_id = data.get("subscription")
        invoice_id = data.get("id")
        if stripe_subscription_id and invoice_id:
            subscription = await subscription_repository.get_by_provider_subscription_id(
                db, "credit_card", stripe_subscription_id
            )
            existing = await payment_repository.get_by_external_reference(db, "credit_card", invoice_id)
            if subscription is not None and existing is None:
                plan = await plan_repository.get_by_id(db, subscription.plan_id)
                period_start = datetime.utcnow()
                await subscription_repository.activate(db, subscription, period_start, period_start + BILLING_PERIOD)
                await payment_repository.create(
                    db,
                    user_id=subscription.user_id,
                    provider="credit_card",
                    amount_cents=plan.price_cents,
                    currency=plan.currency,
                    payload=event,
                    external_reference=invoice_id,
                    status="approved",
                    subscription_id=subscription.id,
                )

    elif event_type == "customer.subscription.deleted":
        stripe_subscription_id = data.get("id")
        if stripe_subscription_id:
            subscription = await subscription_repository.get_by_provider_subscription_id(
                db, "credit_card", stripe_subscription_id
            )
            if subscription is not None:
                await subscription_repository.cancel(db, subscription)

    return {"received": True}


@router.post("/paypal")
async def paypal_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw_body = await request.body()

    if not await paypal.verify_webhook_signature(dict(request.headers), raw_body):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Firma de webhook inválida.")

    event = json.loads(raw_body)
    event_type = event.get("event_type")
    resource = event.get("resource", {})

    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        subscription_id = resource.get("custom_id")
        paypal_subscription_id = resource.get("id")
        if subscription_id and paypal_subscription_id:
            subscription = await subscription_repository.get_by_id(db, uuid.UUID(subscription_id))
            # ":activated" en la referencia: PAYMENT.SALE.COMPLETED reusa
            # este mismo paypal_subscription_id como billing_agreement_id
            # más abajo — sin el sufijo, un cobro real podría chocar
            # contra este evento de activación en la deduplicación.
            reference = f"{paypal_subscription_id}:activated"
            existing = await payment_repository.get_by_external_reference(db, "paypal", reference)
            if subscription is not None and existing is None:
                plan = await plan_repository.get_by_id(db, subscription.plan_id)
                period_start = datetime.utcnow()
                activated = await subscription_repository.activate(
                    db,
                    subscription,
                    period_start,
                    period_start + BILLING_PERIOD,
                    provider_subscription_id=paypal_subscription_id,
                )
                await payment_repository.create(
                    db,
                    user_id=subscription.user_id,
                    provider="paypal",
                    amount_cents=plan.price_cents,
                    currency=plan.currency,
                    payload=event,
                    external_reference=reference,
                    status="approved",
                    subscription_id=activated.id,
                )

    elif event_type == "PAYMENT.SALE.COMPLETED":
        # Dispara en CADA cobro recurrente — renueva el período.
        billing_agreement_id = resource.get("billing_agreement_id")
        sale_id = resource.get("id")
        if billing_agreement_id and sale_id:
            subscription = await subscription_repository.get_by_provider_subscription_id(
                db, "paypal", billing_agreement_id
            )
            existing = await payment_repository.get_by_external_reference(db, "paypal", sale_id)
            if subscription is not None and existing is None:
                plan = await plan_repository.get_by_id(db, subscription.plan_id)
                period_start = datetime.utcnow()
                await subscription_repository.activate(db, subscription, period_start, period_start + BILLING_PERIOD)
                await payment_repository.create(
                    db,
                    user_id=subscription.user_id,
                    provider="paypal",
                    amount_cents=plan.price_cents,
                    currency=plan.currency,
                    payload=event,
                    external_reference=sale_id,
                    status="approved",
                    subscription_id=subscription.id,
                )

    elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
        paypal_subscription_id = resource.get("id")
        if paypal_subscription_id:
            subscription = await subscription_repository.get_by_provider_subscription_id(
                db, "paypal", paypal_subscription_id
            )
            if subscription is not None:
                await subscription_repository.cancel(db, subscription)

    return {"received": True}


@router.post("/binance")
async def binance_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw_body = await request.body()
    timestamp = request.headers.get("binancepay-timestamp", "")
    nonce = request.headers.get("binancepay-nonce", "")
    signature = request.headers.get("binancepay-signature", "")

    if not binance_pay.verify_webhook_signature(timestamp, nonce, raw_body.decode(), signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Firma de webhook inválida.")

    event = json.loads(raw_body)

    # Binance Pay espera este formato de respuesta exacto (no un 200
    # genérico como Stripe/PayPal) — lo mandamos en todos los caminos.
    ack = {"returnCode": "SUCCESS", "returnMessage": None}

    if event.get("bizStatus") == "PAY_SUCCESS":
        data = event.get("data", {})
        merchant_trade_no = data.get("merchantTradeNo")
        transaction_id = data.get("transactionId")
        if merchant_trade_no:
            subscription = await subscription_repository.get_by_id(db, uuid.UUID(merchant_trade_no))
            reference = transaction_id or merchant_trade_no
            existing = await payment_repository.get_by_external_reference(db, "binance_pay", reference)
            if subscription is not None and existing is None:
                plan = await plan_repository.get_by_id(db, subscription.plan_id)
                period_start = datetime.utcnow()
                # auto_renew=False para binance_pay (ver el modelo): esto
                # activa/renueva EL período pagado, no crea un cobro futuro.
                activated = await subscription_repository.activate(
                    db, subscription, period_start, period_start + BILLING_PERIOD
                )
                await payment_repository.create(
                    db,
                    user_id=subscription.user_id,
                    provider="binance_pay",
                    amount_cents=plan.price_cents,
                    currency=plan.currency,
                    payload=event,
                    external_reference=reference,
                    status="approved",
                    subscription_id=activated.id,
                )

    return ack
