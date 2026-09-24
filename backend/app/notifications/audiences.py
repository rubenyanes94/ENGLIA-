"""A qué grupos de clientes se puede enviar una campaña desde gerencia.

Grupos cerrados y calculados por nosotros, no "escribe aquí una consulta":
quien manda un correo a 200 personas necesita saber EXACTAMENTE a quién se
lo manda, y una lista de seis opciones con su recuento al lado es más
segura que un filtro libre en el que un paréntesis mal puesto le escribe a
toda la base de datos.

Cada grupo responde a una pregunta de negocio distinta:

- todos ........... cualquier cosa que deba saber la academia entera.
- con_acceso ...... los que pagan hoy. Novedades, clases nuevas.
- por_vencer ...... se les acaba esta semana. Un empujón a renovar.
- vencidos ........ pagaron y se fueron. Recuperación.
- nunca_pagaron ... se registraron y nunca pagaron. Conversión.
- inactivos ....... pagan pero no entran. Antes de que dejen de pagar.

Los tres filtros de siempre (alumno, cuenta activa, no exento) están en
BASE: al equipo y a las cuentas de acceso regalado no se les manda
publicidad.

Ojo con lo que estos números NO dicen: son los que están en el grupo, no
los que van a recibir el correo. Quien se dio de baja de los recordatorios
y las direcciones de prueba se descartan al enviar (service.py), así que
"enviados" siempre sale igual o menor. La pantalla lo avisa.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.analytics_repository import _local, local_now

BASE = "u.role = 'student' AND u.is_active AND NOT u.access_exempt"

# El acceso vigente de cada alumno: la suscripción activa que más lejos
# llega. Se repite en casi todos los grupos, así que va aparte.
FIN = f"""
    fin AS (
        SELECT s.user_id, max({_local('s.current_period_end')}) AS termina
          FROM subscriptions s
         WHERE s.status = 'active' AND s.current_period_end IS NOT NULL
         GROUP BY s.user_id
    )
"""

# Días que se miran hacia delante en "por_vencer".
VENCE_EN_DIAS = 7


@dataclass(frozen=True)
class Audience:
    key: str
    label: str
    description: str
    sql: str


AUDIENCES: dict[str, Audience] = {
    "todos": Audience(
        "todos", "Todos los clientes",
        "Todas las cuentas de alumno activas, paguen o no.",
        f"SELECT u.id FROM users u WHERE {BASE}",
    ),
    "con_acceso": Audience(
        "con_acceso", "Con acceso activo",
        "Los que hoy pueden entrar a las clases porque su suscripción está vigente.",
        f"WITH {FIN} SELECT u.id FROM users u JOIN fin ON fin.user_id = u.id"
        f" WHERE {BASE} AND fin.termina > CAST(:hoy AS timestamp)",
    ),
    "por_vencer": Audience(
        "por_vencer", f"Vencen en {VENCE_EN_DIAS} días",
        f"Su acceso termina dentro de los próximos {VENCE_EN_DIAS} días y todavía no han renovado.",
        f"WITH {FIN} SELECT u.id FROM users u JOIN fin ON fin.user_id = u.id"
        f" WHERE {BASE} AND fin.termina > CAST(:hoy AS timestamp)"
        f" AND fin.termina <= CAST(:hoy AS timestamp) + make_interval(days => :dias)",
    ),
    "vencidos": Audience(
        "vencidos", "Se les venció",
        "Pagaron alguna vez, se les acabó el acceso y no volvieron a pagar.",
        f"WITH {FIN} SELECT u.id FROM users u JOIN fin ON fin.user_id = u.id"
        f" WHERE {BASE} AND fin.termina <= CAST(:hoy AS timestamp)",
    ),
    "nunca_pagaron": Audience(
        "nunca_pagaron", "Nunca han pagado",
        "Se registraron pero no tienen ningún pago aprobado.",
        f"SELECT u.id FROM users u WHERE {BASE}"
        " AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.user_id = u.id AND p.status = 'approved')",
    ),
    "inactivos": Audience(
        "inactivos", "Pagan pero no entran",
        "Tienen el acceso vigente y llevan una semana o más sin practicar. Los que están a punto de no renovar.",
        f"""
        WITH {FIN},
        actividad AS (
            SELECT s.user_id, max(m.created_at) AS ts
              FROM conversation_messages m JOIN conversation_sessions s ON s.id = m.session_id
             WHERE m.role = 'user' GROUP BY s.user_id
            UNION ALL
            SELECT user_id, max(created_at) FROM user_events GROUP BY user_id
            UNION ALL
            SELECT user_id, max(attempted_at) FROM exercise_attempts GROUP BY user_id
        ),
        ultima AS (SELECT user_id, {_local('max(ts)')} AS ts FROM actividad GROUP BY user_id)
        SELECT u.id FROM users u
          JOIN fin ON fin.user_id = u.id
          LEFT JOIN ultima ON ultima.user_id = u.id
         WHERE {BASE} AND fin.termina > CAST(:hoy AS timestamp)
           AND coalesce(ultima.ts, {_local('u.created_at')}) < CAST(:hoy AS timestamp) - make_interval(days => :inactividad)
        """,
    ),
}


def _params() -> dict:
    return {
        "hoy": local_now(),
        "tz": settings.analytics_timezone,
        "dias": VENCE_EN_DIAS,
        "inactividad": settings.inactivity_days,
    }


async def user_ids(db: AsyncSession, key: str) -> list:
    audience = AUDIENCES[key]
    result = await db.execute(text(audience.sql), _params())
    return [row[0] for row in result.all()]


async def counts(db: AsyncSession) -> list[dict]:
    """Los seis grupos con cuánta gente hay hoy en cada uno, para la
    pantalla de envío."""
    salida = []
    params = _params()
    for audience in AUDIENCES.values():
        total = (await db.execute(text(f"SELECT count(*) FROM ({audience.sql}) AS grupo"), params)).scalar()
        salida.append({"key": audience.key, "label": audience.label, "description": audience.description, "customers": total or 0})
    return salida
