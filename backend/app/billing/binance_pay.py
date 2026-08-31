"""Integración con Binance Pay (cripto).

AVISO: sigue el flujo documentado por Binance, pero no ha corrido contra
una cuenta Binance Pay real todavía — no hay credenciales configuradas
en este entorno. Trátalo como "compila y sigue el contrato documentado",
no como "probado end-to-end".

A diferencia de PayPal/Stripe, Binance Pay NO tiene "suscripciones"
recurrentes: no hay forma de autorizar un cargo mensual automático a
una wallet cripto. Cada mes es una ORDEN nueva que el alumno paga a
mano (escanea un QR o abre el link) — por eso Subscription.auto_renew
es False para este proveedor, y el frontend debe avisar "renueva antes
de que venza" en vez de asumir que se cobra solo.
"""

import hashlib
import hmac
import json
import time
import uuid

import httpx

from app.core.config import settings
from app.models import Plan


def is_configured() -> bool:
    return bool(settings.binance_pay_api_key and settings.binance_pay_api_secret)


def _sign(timestamp: str, nonce: str, body: str) -> str:
    payload = f"{timestamp}\n{nonce}\n{body}\n"
    return hmac.new(settings.binance_pay_api_secret.encode(), payload.encode(), hashlib.sha512).hexdigest().upper()


async def create_order(subscription_id: str, plan: Plan) -> dict:
    """Devuelve {"checkout_url": ...}.

    `subscription_id` (NUESTRA Subscription, ya creada en "pending" por
    el router) se manda tal cual como merchantTradeNo — es único de por
    sí (es nuestra propia primary key), así que no hace falta generar
    otro identificador aparte; el webhook lo usa para encontrar la fila.
    """
    body = {
        "env": {"terminalType": "WEB"},
        "merchantTradeNo": subscription_id,
        "orderAmount": round(plan.price_cents / 100, 2),
        "currency": plan.currency,
        "goods": {
            "goodsType": "02",  # "02" = servicio/bien virtual (no físico)
            "goodsCategory": "D000",  # categoría "Education" del catálogo de Binance Pay
            "referenceGoodsId": plan.code,
            "goodsName": plan.name,
        },
    }
    body_json = json.dumps(body)
    timestamp = str(int(time.time() * 1000))
    nonce = uuid.uuid4().hex

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.binance_pay_api_base}/binancepay/openapi/v3/order",
            headers={
                "Content-Type": "application/json",
                "BinancePay-Timestamp": timestamp,
                "BinancePay-Nonce": nonce,
                "BinancePay-Certificate-SN": settings.binance_pay_api_key,
                "BinancePay-Signature": _sign(timestamp, nonce, body_json),
            },
            content=body_json,
        )
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "SUCCESS":
        raise RuntimeError(f"Binance Pay rechazó la orden: {data}")

    return {"checkout_url": data["data"]["checkoutUrl"]}


def verify_webhook_signature(timestamp: str, nonce: str, raw_body: str, signature: str) -> bool:
    """Recalcula la firma con NUESTRO secreto y la compara contra la que
    mandó Binance — hmac.compare_digest en vez de `==` a propósito (
    comparación en tiempo constante, para no filtrar la firma correcta
    byte a byte vía un ataque de timing)."""
    expected = _sign(timestamp, nonce, raw_body)
    return hmac.compare_digest(expected, signature)
