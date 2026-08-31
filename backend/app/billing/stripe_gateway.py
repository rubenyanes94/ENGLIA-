"""Integración con Stripe (tarjetas: Mastercard/Visa/Amex).

AVISO: sigue la forma documentada de la API de Stripe (Checkout Sessions
en modo "subscription" + webhooks), pero no ha corrido contra una cuenta
Stripe real todavía — no hay credenciales configuradas en este entorno.
Trátalo como "compila y sigue el contrato documentado", no como
"probado end-to-end". Antes de aceptar el primer pago real, hace falta:
  1. Crear la cuenta Stripe + el Product/Price del plan ($10/mes) y
     guardar ese price_id en Plan.stripe_price_id.
  2. Configurar STRIPE_SECRET_KEY y STRIPE_WEBHOOK_SECRET en el entorno.
  3. Probar el flujo completo contra el modo test de Stripe (tienen
     tarjetas de prueba oficiales para esto).
"""

import asyncio

import stripe

from app.core.config import settings
from app.models import Plan


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


async def create_checkout_session(subscription_id: str, user_email: str, plan: Plan) -> str:
    """Devuelve la URL de Stripe Checkout a la que redirigir al alumno.

    `subscription_id` es el id de NUESTRA Subscription (ya creada en
    estado "pending" por el router antes de llamar aquí) — lo mandamos
    como client_reference_id para que el webhook, cuando el pago se
    confirme, sepa exactamente qué fila activar sin tener que adivinar.
    """
    if not plan.stripe_price_id:
        raise ValueError(f"El plan '{plan.code}' no tiene stripe_price_id configurado en Stripe todavía.")

    def _create() -> "stripe.checkout.Session":
        # El SDK de Stripe es síncrono (usa `requests` por debajo). Lo
        # corremos en un hilo aparte para no bloquear el event loop de
        # FastAPI mientras espera la respuesta HTTP de Stripe.
        stripe.api_key = settings.stripe_secret_key
        return stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user_email,
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.frontend_base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_base_url}/billing/cancel",
            client_reference_id=subscription_id,
            metadata={"subscription_id": subscription_id, "plan_code": plan.code},
        )

    session = await asyncio.to_thread(_create)
    return session.url


async def verify_webhook(payload: bytes, sig_header: str) -> "stripe.Event":
    """Verifica la firma HMAC del webhook contra STRIPE_WEBHOOK_SECRET.

    Lanza stripe.error.SignatureVerificationError si no cuadra — el
    router debe atrapar eso y devolver 400 SIN procesar el payload:
    aceptar un webhook sin verificar dejaría que cualquiera mande un
    POST fingiendo ser Stripe y active suscripciones gratis.
    """

    def _verify() -> "stripe.Event":
        return stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)

    return await asyncio.to_thread(_verify)
