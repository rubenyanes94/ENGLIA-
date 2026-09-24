"""A quién le toca hoy un correo de retención, y el bucle que lo revisa.

Cuatro momentos, elegidos porque son los que deciden si un alumno sigue o
se va:

1. **Faltan 3 días** para que venza. Hay tiempo de reaccionar sin prisa.
2. **Último día**. El aviso que más renovaciones trae, porque ya es real.
3. **Venció hoy**. Se manda el mismo día, mientras todavía se acuerda de
   nosotros; a la semana ya es un correo frío.
4. **Una semana sin entrar**, teniendo acceso pagado. Es el aviso más
   rentable de todos: ese alumno ya pagó y está a punto de no renovar
   porque dejó de usarlo.

Todo se calcula en fechas de CALENDARIO en hora de Venezuela, no en
"horas que faltan": la suscripción vence a medianoche (ver
app/billing/period.py), así que "faltan 3 días" es una resta de días del
calendario y no de horas, y el aviso sale siempre a la misma hora del día
para todos.

El bucle corre dentro del backend (como el de la tasa del BCV) con un
candado en Redis, para que con varios procesos solo uno escriba. Aun si
el candado fallara, la clave única de email_messages impide el duplicado:
son dos redes distintas para el mismo pez.
"""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.redis import redis_client
from app.models import User
from app.notifications import service
from app.notifications.messages import fecha_larga
from app.repositories.analytics_repository import BASE_CTE, _all, _local, local_now

logger = logging.getLogger(__name__)

# Cuántos días antes del vencimiento se avisa. El de 1 día es "último
# día" y tiene su propio texto.
AVISO_PREVIO_DIAS = 3

# Quién NO recibe correos de retención: el equipo y las cuentas con
# acceso regalado (a un exento no se le puede pedir que renueve nada).
DESTINATARIOS = "u.role = 'student' AND u.is_active AND NOT u.access_exempt"

# Tope por vuelta. No es un límite del proveedor: es un freno de mano. Si
# una consulta sale mal y de pronto "le toca" a media base de datos, se
# envían cincuenta y el resto espera a la vuelta siguiente, con un aviso
# en el log. Una campaña disparada por error no se puede deshacer.
MAX_POR_VUELTA = 50


async def _suscripciones_por_vencer(db: AsyncSession) -> list[dict]:
    """Por cada alumno, la fecha en que se le acaba el acceso (la más
    lejana que tenga) y cuántos días de calendario faltan.

    Se mira la suscripción más lejana y no la "activa" porque quien
    renueva antes de tiempo tiene dos: si cogiéramos cualquiera, le
    diríamos "te quedan 3 días" a alguien que acaba de pagar un mes más.
    """
    sql = f"""
    WITH fin AS (
        SELECT s.user_id, max({_local('s.current_period_end')}) AS termina
          FROM subscriptions s
         WHERE s.status = 'active' AND s.current_period_end IS NOT NULL
         GROUP BY s.user_id
    )
    SELECT u.id, fin.termina,
           (fin.termina::date - CAST(:hoy AS timestamp)::date) AS dias
      FROM fin
      JOIN users u ON u.id = fin.user_id
     WHERE {DESTINATARIOS}
       AND (fin.termina::date - CAST(:hoy AS timestamp)::date) IN (:previo, 1, 0)
    """
    return await _all(db, sql, {"hoy": local_now(), "previo": AVISO_PREVIO_DIAS, "tz": settings.analytics_timezone})


async def _inactivos_con_acceso(db: AsyncSession) -> list[dict]:
    """Alumnos que pagaron, tienen el acceso vigente y llevan `inactivity_days`
    sin aparecer. Se cuenta desde su última señal de vida o, si nunca hizo
    nada, desde el día que se registró."""
    sql = f"""
    WITH {BASE_CTE},
    ultima AS (
        SELECT user_id, max(ts) AS ts FROM customer_activity GROUP BY user_id
    ),
    vigentes AS (
        SELECT s.user_id, max({_local('s.current_period_end')}) AS termina
          FROM subscriptions s
         WHERE s.status = 'active' AND s.current_period_end IS NOT NULL
         GROUP BY s.user_id
    )
    SELECT u.id, (CAST(:hoy AS timestamp)::date - coalesce(ultima.ts, c.created_at)::date) AS dias
      FROM vigentes v
      JOIN users u ON u.id = v.user_id
      JOIN customers c ON c.id = u.id
      LEFT JOIN ultima ON ultima.user_id = u.id
     WHERE {DESTINATARIOS}
       AND v.termina > CAST(:hoy AS timestamp)
       AND (CAST(:hoy AS timestamp)::date - coalesce(ultima.ts, c.created_at)::date) >= :dias
    """
    return await _all(db, sql, {"hoy": local_now(), "dias": settings.inactivity_days, "tz": settings.analytics_timezone})


async def run_once() -> dict:
    """Una pasada completa. Devuelve el recuento por tipo, que es lo que
    se ve en el panel de Sistema."""
    enviados: dict[str, int] = {}
    total = 0
    async with AsyncSessionLocal() as db:
        for row in await _suscripciones_por_vencer(db):
            dias = row["dias"]
            kind = {AVISO_PREVIO_DIAS: "vence_pronto", 1: "ultimo_dia", 0: "vencio"}[dias]
            user = await db.get(User, row["id"])
            if user is None:
                continue
            fecha = row["termina"].date()
            ok = await service.send(
                db, user, kind,
                # La fecha de vencimiento en la clave: si el alumno renueva
                # y vuelve a acercarse otro vencimiento, es un aviso nuevo
                # y legítimo, no el mismo repetido.
                dedupe_key=f"{kind}:{fecha.isoformat()}",
                context={"hasta": fecha_larga(fecha), "dias": dias},
            )
            if ok:
                enviados[kind] = enviados.get(kind, 0) + 1
                total += 1
                if total >= MAX_POR_VUELTA:
                    logger.warning("Tope de %s correos por vuelta alcanzado; el resto sale en la siguiente.", MAX_POR_VUELTA)
                    return enviados

        for row in await _inactivos_con_acceso(db):
            user = await db.get(User, row["id"])
            if user is None:
                continue
            # Una vez por semana como mucho: la clave es el lunes de la
            # semana en curso.
            hoy = local_now().date()
            semana = hoy - timedelta(days=hoy.weekday())
            ok = await service.send(
                db, user, "te_echamos_de_menos",
                dedupe_key=f"te_echamos_de_menos:{semana.isoformat()}",
                context={"dias": int(row["dias"])},
            )
            if ok:
                enviados["te_echamos_de_menos"] = enviados.get("te_echamos_de_menos", 0) + 1
                total += 1
                if total >= MAX_POR_VUELTA:
                    logger.warning("Tope de %s correos por vuelta alcanzado; el resto sale en la siguiente.", MAX_POR_VUELTA)
                    break

    if enviados:
        logger.info("Correos de retención enviados: %s", enviados)
    return enviados


async def notifications_loop() -> None:
    """Bucle de fondo del backend (ver el lifespan de app/main.py)."""
    interval = max(5, settings.notifications_interval_minutes) * 60
    while True:
        try:
            if await redis_client.set("notifications:loop-lock", "1", nx=True, ex=interval - 30):
                await run_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — una vuelta fallida no mata el bucle
            logger.warning("Fallo en la revisión de correos de retención", exc_info=True)
        await asyncio.sleep(interval)
