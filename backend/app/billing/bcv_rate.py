"""Tasa oficial del dólar publicada por el BCV, leída y guardada sola.

Por qué la web y no Twitter/Telegram: en redes el BCV publica una IMAGEN
(habría que leerla con OCR, frágil). La misma cifra está como texto en
www.bcv.org.ve, en el bloque id="dolar", junto a su "Fecha Valor".

Tres cosas que no son obvias:

1. **TLS.** El servidor del BCV envía un certificado intermedio
   EQUIVOCADO (uno antiguo de Sectigo, no el que firmó su certificado), así
   que cualquier cliente HTTPS falla con "unable to verify the first
   certificate". En vez de desactivar la verificación — alguien en medio
   podría inyectar una tasa falsa y los clientes pagarían mal —, se añade
   el intermedio correcto (certs/, sacado de la URL "CA Issuers" del propio
   certificado del BCV; SHA-256 8C:54:C3:34:…:A4:EF:22:E0, válido hasta
   2036) a los certificados raíz de certifi.

2. **Fecha valor.** El BCV publica por la tarde la tasa que rige AL DÍA
   SIGUIENTE. Se guarda cada tasa con su fecha valor y se cobra con la que
   rige hoy: la más reciente cuya fecha valor ya empezó (ver rate_for_today).

3. **Validación.** Si el BCV cambia su página, el lector no puede guardar
   basura: una cifra que no parsea, o que se aleja más de un 25 % de la
   última guardada, se descarta y se registra en el log (y el panel de
   Sistema avisa de que la tasa se está quedando vieja).
"""

import asyncio
import logging
import re
import ssl
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import certifi
import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.redis import redis_client
from app.models import ExchangeRate
from app.repositories.analytics_repository import local_now

logger = logging.getLogger(__name__)

BCV_URL = "https://www.bcv.org.ve/"
SOURCE = "bcv.org.ve"
INTERMEDIATE_CERT = Path(__file__).parent / "certs" / "sectigo_public_server_authentication_ca_dv_r36.pem"

# Cada cuánto se consulta la web del BCV. Publica una vez al día (por la
# tarde), así que cada hora sobra para no perderse ninguna fecha valor.
REFRESH_EVERY = timedelta(hours=1)
# Más de un 25 % de salto entre dos fechas valor no es una devaluación, es
# un error de lectura: no se guarda.
MAX_JUMP = Decimal("0.25")

_DOLAR_BLOCK = re.compile(r'id="dolar".*?<strong[^>]*>\s*([\d.,]+)\s*</strong>', re.S)
_VALUE_DATE = re.compile(r'Fecha Valor:.*?content="(\d{4}-\d{2}-\d{2})', re.S)


@dataclass(frozen=True)
class PublishedRate:
    rate: Decimal
    value_date: date


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=certifi.where())
    context.load_verify_locations(cafile=str(INTERMEDIATE_CERT))
    return context


def parse_bcv_page(html: str) -> PublishedRate:
    """"852,41680000" + content="2026-09-22T00:00:00-04:00" → (852.4168, 2026-09-22)."""
    rate_match = _DOLAR_BLOCK.search(html)
    date_match = _VALUE_DATE.search(html)
    if not rate_match or not date_match:
        raise ValueError("No se encontró la tasa del dólar o su fecha valor en la página del BCV.")
    raw = rate_match.group(1).replace(".", "").replace(",", ".")
    try:
        rate = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Tasa ilegible en la página del BCV: {rate_match.group(1)!r}") from exc
    if rate <= 0:
        raise ValueError(f"Tasa no positiva en la página del BCV: {rate}")
    return PublishedRate(rate=rate, value_date=date.fromisoformat(date_match.group(1)))


async def fetch_published_rate() -> PublishedRate:
    async with httpx.AsyncClient(verify=_ssl_context(), timeout=20, follow_redirects=True) as client:
        response = await client.get(BCV_URL, headers={"User-Agent": "Espikin/1.0 (tasa de referencia)"})
        response.raise_for_status()
    return parse_bcv_page(response.text)


async def _latest(db: AsyncSession) -> ExchangeRate | None:
    result = await db.execute(select(ExchangeRate).where(ExchangeRate.currency == "USD").order_by(ExchangeRate.value_date.desc()).limit(1))
    return result.scalars().first()


async def store_rate(db: AsyncSession, published: PublishedRate, source: str = SOURCE) -> bool:
    """Guarda la tasa de su fecha valor. Si ya había una para esa fecha, la
    actualiza (el BCV a veces corrige). Devuelve False si la descarta por
    alejarse demasiado de la última conocida."""
    latest = await _latest(db)
    if latest is not None and latest.value_date != published.value_date:
        jump = abs(published.rate - latest.rate) / latest.rate
        if jump > MAX_JUMP:
            logger.warning(
                "Tasa BCV descartada: %s para %s se aleja %.0f%% de %s (%s)",
                published.rate, published.value_date, jump * 100, latest.rate, latest.value_date,
            )
            return False
    stmt = insert(ExchangeRate).values(currency="USD", rate=published.rate, value_date=published.value_date, source=source)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_exchange_rates_currency_value_date",
        set_={"rate": stmt.excluded.rate, "source": stmt.excluded.source, "fetched_at": datetime.utcnow()},
    )
    await db.execute(stmt)
    await db.commit()
    return True


async def refresh_from_bcv() -> PublishedRate | None:
    """Lee la web del BCV y guarda lo que publica. Nunca lanza: si el BCV no
    responde se reintentará en la próxima vuelta, y mientras tanto se sigue
    cobrando con la última tasa guardada."""
    try:
        published = await fetch_published_rate()
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo leer la tasa del BCV", exc_info=True)
        return None
    async with AsyncSessionLocal() as db:
        stored = await store_rate(db, published)
    if stored:
        logger.info("Tasa BCV guardada: %s Bs/$ con fecha valor %s", published.rate, published.value_date)
    return published if stored else None


@dataclass(frozen=True)
class ApplicableRate:
    rate: Decimal
    value_date: date
    source: str


async def rate_for_today(db: AsyncSession) -> ApplicableRate | None:
    """La tasa que rige HOY en Caracas: la de fecha valor más reciente que
    ya empezó. Si solo hay tasas futuras (recién instalado un lunes por la
    tarde), la más próxima. PAGO_MOVIL_BS_PER_USD, si se pone, manda sobre
    todo: es la palanca manual para una emergencia."""
    if settings.pago_movil_bs_per_usd:
        return ApplicableRate(Decimal(str(settings.pago_movil_bs_per_usd)), local_now().date(), "manual (PAGO_MOVIL_BS_PER_USD)")
    today = local_now().date()
    base = select(ExchangeRate).where(ExchangeRate.currency == "USD")
    row = (await db.execute(base.where(ExchangeRate.value_date <= today).order_by(ExchangeRate.value_date.desc()).limit(1))).scalars().first()
    if row is None:
        row = (await db.execute(base.order_by(ExchangeRate.value_date.asc()).limit(1))).scalars().first()
    return ApplicableRate(row.rate, row.value_date, row.source) if row else None


async def ensure_rate(db: AsyncSession) -> ApplicableRate | None:
    """Para las pantallas de pago: si no hay NINGUNA tasa guardada (primer
    arranque), se lee del BCV en el momento en vez de dejar al alumno sin
    monto. Con tasas guardadas no se espera a la red: el refresco es del
    bucle de fondo."""
    applicable = await rate_for_today(db)
    if applicable is None:
        await refresh_from_bcv()
        applicable = await rate_for_today(db)
    return applicable


async def refresh_loop() -> None:
    """Bucle de fondo del backend (ver lifespan en app/main.py): lee la tasa
    al arrancar y luego cada hora. Con varios procesos del backend, un
    candado en Redis hace que solo uno consulte al BCV por vuelta."""
    while True:
        try:
            if await redis_client.set("bcv-rate:refresh-lock", "1", nx=True, ex=int(REFRESH_EVERY.total_seconds()) - 60):
                await refresh_from_bcv()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — el bucle no puede morir por una vuelta fallida
            logger.warning("Fallo en el refresco de la tasa BCV", exc_info=True)
        await asyncio.sleep(REFRESH_EVERY.total_seconds())
