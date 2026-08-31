"""Integración con la PayPal Subscriptions API.

AVISO: sigue el flujo documentado por PayPal, pero no ha corrido contra
una cuenta PayPal real todavía — no hay credenciales configuradas en
este entorno. Trátalo como "compila y sigue el contrato documentado",
no como "probado end-to-end". Antes de aceptar el primer pago real:
  1. Crear la cuenta PayPal Business + un Product y un Plan de $10/mes
     (vía su dashboard o su API — es un paso previo obligatorio, un
     Plan de PayPal no se crea "al vuelo" en cada checkout) y guardar
     ese id en Plan.paypal_plan_id.
  2. Configurar PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET y
     PAYPAL_WEBHOOK_ID (este último sale de configurar el webhook en
     el dashboard de PayPal, apuntando a POST /webhooks/paypal).
  3. Probar contra el entorno sandbox de PayPal (PAYPAL_API_BASE ya
     apunta ahí por defecto).
"""

import json

import httpx

from app.core.config import settings
from app.models import Plan


def is_configured() -> bool:
    return bool(settings.paypal_client_id and settings.paypal_client_secret)


async def _get_access_token() -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.paypal_api_base}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(settings.paypal_client_id, settings.paypal_client_secret),
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def create_subscription(subscription_id: str, user_email: str, plan: Plan) -> dict:
    """Devuelve {"approval_url": ..., "provider_subscription_id": ...}.

    `subscription_id` (NUESTRA Subscription, ya creada en "pending" por
    el router) va en `custom_id` — PayPal lo devuelve tal cual en cada
    evento de webhook, así no hay que adivinar a qué fila corresponde.
    """
    if not plan.paypal_plan_id:
        raise ValueError(f"El plan '{plan.code}' no tiene paypal_plan_id configurado en PayPal todavía.")

    token = await _get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.paypal_api_base}/v1/billing/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "plan_id": plan.paypal_plan_id,
                "subscriber": {"email_address": user_email},
                "custom_id": subscription_id,
                "application_context": {
                    "brand_name": "English Academy",
                    "return_url": f"{settings.frontend_base_url}/billing/success",
                    "cancel_url": f"{settings.frontend_base_url}/billing/cancel",
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    approval_url = next(link["href"] for link in data["links"] if link["rel"] == "approve")
    return {"approval_url": approval_url, "provider_subscription_id": data["id"]}


async def verify_webhook_signature(headers: dict, raw_body: bytes) -> bool:
    """Delega la verificación al endpoint oficial de PayPal en vez de
    reimplementar la validación criptográfica de firmas nosotros mismos
    (PayPal firma con un certificado X.509 que rota — es justo el tipo
    de cosa que NO conviene reinventar)."""
    token = await _get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.paypal_api_base}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "auth_algo": headers.get("paypal-auth-algo"),
                "cert_url": headers.get("paypal-cert-url"),
                "transmission_id": headers.get("paypal-transmission-id"),
                "transmission_sig": headers.get("paypal-transmission-sig"),
                "transmission_time": headers.get("paypal-transmission-time"),
                "webhook_id": settings.paypal_webhook_id,
                "webhook_event": json.loads(raw_body),
            },
        )
        response.raise_for_status()
        return response.json().get("verification_status") == "SUCCESS"
