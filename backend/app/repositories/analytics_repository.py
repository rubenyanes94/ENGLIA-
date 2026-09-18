"""Consultas del panel de gerencia (routers/management.py).

SQL explícito con text() y no el ORM, a propósito: son agregaciones con
CTEs, ventanas y percentiles, y en SQL se leen de un vistazo y se pueden
pegar tal cual en psql para contrastar una cifra. Con el ORM serían el
triple de largas y nadie podría auditarlas.

Tres decisiones que afectan a TODAS las cifras:

1. **Cliente = usuario con role "student".** Ni admins ni gerencia cuentan:
   sus clics de prueba inflarían el uso y se colarían en los embudos.

2. **Actividad = cualquier rastro de uso**, reunido en la CTE `activity`:
   mensajes al tutor, respuestas de examen, eventos (incluida la apertura
   de pantallas, `page_viewed`) y el juego de oraciones. Cada fila lleva
   un `feature` para saber de qué parte de la app viene. "Aprender"
   (activación, embudo) excluye `app` y `milestone`: abrir la app o
   inscribirse no es practicar.

3. **Hora local del negocio** (settings.analytics_timezone). La BD guarda
   UTC; aquí todo se convierte antes de agrupar por día u hora, y los
   límites de periodo que llegan de Python también son hora local.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

LEARNING_FEATURES = ("tutor", "library", "exam", "exercise", "sentence_game")

# Suscripciones que hoy dan acceso y por tanto cuentan para MRR. past_due
# entra: la pasarela avisó de un cobro fallido pero el acceso sigue (grace period).
PAYING_STATUSES = ("active", "past_due")


def _local(col: str) -> str:
    """Una columna TIMESTAMP guardada en UTC, pasada a hora local del negocio."""
    return f"(({col} AT TIME ZONE 'UTC') AT TIME ZONE CAST(:tz AS text))"


BASE_CTE = f"""
customers AS (
    SELECT id, {_local('created_at')} AS created_at
      FROM users
     WHERE role = 'student'
),
activity AS (
    SELECT s.user_id, {_local('m.created_at')} AS ts,
           CASE WHEN s.flash_course_id IS NOT NULL THEN 'library' ELSE 'tutor' END AS feature
      FROM conversation_messages m
      JOIN conversation_sessions s ON s.id = m.session_id
     WHERE m.role = 'user'
    UNION ALL
    SELECT a.user_id, {_local('a.attempted_at')},
           CASE WHEN e.stage = 'exam' THEN 'exam' ELSE 'exercise' END
      FROM exercise_attempts a
      JOIN exercises e ON e.id = a.exercise_id
    UNION ALL
    SELECT user_id, {_local('created_at')},
           CASE event_type
               WHEN 'page_viewed' THEN 'app'
               WHEN 'module_exam_submitted' THEN 'exam'
               WHEN 'chat_task_attempted' THEN 'tutor'
               ELSE 'milestone'
           END
      FROM user_events
    UNION ALL
    -- El juego solo guarda su ÚLTIMA partida (una fila por alumno), así
    -- que aporta "estuvo activo ese día", no un historial completo.
    SELECT user_id, {_local('updated_at')}, 'sentence_game'
      FROM sentence_game_progress
     WHERE total_answered > 0
),
customer_activity AS (
    SELECT a.user_id, a.ts, a.feature
      FROM activity a
      JOIN customers c ON c.id = a.user_id
)
"""


@dataclass(frozen=True)
class Period:
    """Ventana de análisis en hora local: [start, end) y la inmediatamente
    anterior de la misma duración, para los "vs periodo anterior"."""

    days: int
    start: datetime
    end: datetime
    prev_start: datetime

    @property
    def bucket(self) -> str:
        # Una serie de 365 puntos diarios es ruido; a partir de 3 meses se agrupa por semana.
        return "day" if self.days <= 90 else "week"

    @property
    def params(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "prev_start": self.prev_start,
            "tz": settings.analytics_timezone,
            "bucket": self.bucket,
            # timedelta y no "1 day": asyncpg tipa el parámetro como interval
            # por el CAST y solo acepta el tipo Python equivalente.
            "step": timedelta(days=1) if self.bucket == "day" else timedelta(weeks=1),
        }


def local_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(ZoneInfo(settings.analytics_timezone)).replace(tzinfo=None)


def make_period(days: int) -> Period:
    end = local_now()
    start = end - timedelta(days=days)
    return Period(days=days, start=start, end=end, prev_start=start - timedelta(days=days))


async def _one(db: AsyncSession, sql: str, params: dict) -> dict:
    result = await db.execute(text(sql), params)
    return dict(result.mappings().one())


async def _all(db: AsyncSession, sql: str, params: dict) -> list[dict]:
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------


async def overview_kpis(db: AsyncSession, period: Period) -> dict:
    sql = f"""
    WITH {BASE_CTE},
    new_in_period AS (
        SELECT id, created_at FROM customers
         WHERE created_at >= CAST(:start AS timestamp) AND created_at < CAST(:end AS timestamp)
    ),
    first_learning AS (
        SELECT user_id, min(ts) AS t FROM customer_activity
         WHERE feature IN {LEARNING_FEATURES} GROUP BY user_id
    ),
    paying AS (
        SELECT s.user_id,
               CASE p.interval WHEN 'year' THEN p.price_cents / 12.0 ELSE p.price_cents END AS monthly_cents
          FROM subscriptions s
          JOIN plans p ON p.id = s.plan_id
          JOIN customers c ON c.id = s.user_id
         WHERE s.status IN {PAYING_STATUSES}
    ),
    approved AS (
        SELECT p.user_id, {_local('p.created_at')} AS paid_at, p.amount_cents
          FROM payments p JOIN customers c ON c.id = p.user_id
         WHERE p.status = 'approved'
    )
    SELECT
        (SELECT count(*) FROM customers) AS customers_total,
        (SELECT count(*) FROM new_in_period) AS new_customers,
        (SELECT count(*) FROM customers
          WHERE created_at >= CAST(:prev_start AS timestamp) AND created_at < CAST(:start AS timestamp)) AS new_customers_prev,
        (SELECT count(DISTINCT user_id) FROM customer_activity
          WHERE ts >= CAST(:start AS timestamp) AND ts < CAST(:end AS timestamp)) AS active_customers,
        (SELECT count(DISTINCT user_id) FROM customer_activity
          WHERE ts >= CAST(:prev_start AS timestamp) AND ts < CAST(:start AS timestamp)) AS active_customers_prev,
        (SELECT count(DISTINCT user_id) FROM customer_activity
          WHERE ts >= CAST(:end AS timestamp) - interval '1 day') AS dau,
        (SELECT count(DISTINCT user_id) FROM customer_activity
          WHERE ts >= CAST(:end AS timestamp) - interval '7 days') AS wau,
        (SELECT count(DISTINCT user_id) FROM customer_activity
          WHERE ts >= CAST(:end AS timestamp) - interval '30 days') AS mau,
        -- DAU medio de los últimos 30 días, contando los días sin nadie
        -- como cero (por eso se divide entre 30 y no se promedian solo
        -- los días con actividad).
        (SELECT count(DISTINCT (user_id, date_trunc('day', ts)))::float / 30 FROM customer_activity
          WHERE ts >= CAST(:end AS timestamp) - interval '30 days') AS avg_dau_30,
        (SELECT count(*) FROM new_in_period n
           JOIN first_learning f ON f.user_id = n.id
          WHERE f.t < n.created_at + interval '7 days') AS activated_new,
        (SELECT count(DISTINCT user_id) FROM paying) AS paying_customers,
        (SELECT coalesce(sum(monthly_cents), 0) FROM paying) AS mrr_cents,
        (SELECT count(DISTINCT user_id) FROM approved) AS ever_paid_customers,
        (SELECT coalesce(sum(amount_cents), 0) FROM approved
          WHERE paid_at >= CAST(:start AS timestamp) AND paid_at < CAST(:end AS timestamp)) AS revenue_cents,
        (SELECT coalesce(sum(amount_cents), 0) FROM approved
          WHERE paid_at >= CAST(:prev_start AS timestamp) AND paid_at < CAST(:start AS timestamp)) AS revenue_prev_cents
    """
    return await _one(db, sql, period.params)


async def time_series(db: AsyncSession, period: Period) -> list[dict]:
    """Altas, clientes activos e ingresos por día (o semana), con cero en
    los huecos: una serie con días que faltan dibuja líneas que mienten."""
    sql = f"""
    WITH {BASE_CTE},
    buckets AS (
        SELECT generate_series(
            date_trunc(CAST(:bucket AS text), CAST(:start AS timestamp)),
            date_trunc(CAST(:bucket AS text), CAST(:end AS timestamp)),
            CAST(:step AS interval)
        ) AS b
    ),
    signups AS (
        SELECT date_trunc(CAST(:bucket AS text), created_at) AS b, count(*) AS n
          FROM customers
         WHERE created_at >= date_trunc(CAST(:bucket AS text), CAST(:start AS timestamp))
         GROUP BY 1
    ),
    actives AS (
        SELECT date_trunc(CAST(:bucket AS text), ts) AS b, count(DISTINCT user_id) AS n
          FROM customer_activity
         WHERE ts >= date_trunc(CAST(:bucket AS text), CAST(:start AS timestamp))
         GROUP BY 1
    ),
    revenue AS (
        SELECT date_trunc(CAST(:bucket AS text), {_local('p.created_at')}) AS b, sum(p.amount_cents) AS cents
          FROM payments p JOIN customers c ON c.id = p.user_id
         WHERE p.status = 'approved'
         GROUP BY 1
    )
    SELECT buckets.b AS bucket,
           coalesce(signups.n, 0) AS signups,
           coalesce(actives.n, 0) AS active_customers,
           coalesce(revenue.cents, 0) AS revenue_cents
      FROM buckets
      LEFT JOIN signups ON signups.b = buckets.b
      LEFT JOIN actives ON actives.b = buckets.b
      LEFT JOIN revenue ON revenue.b = buckets.b
     ORDER BY buckets.b
    """
    return await _all(db, sql, period.params)


# ---------------------------------------------------------------------------
# Consumo
# ---------------------------------------------------------------------------


async def feature_usage(db: AsyncSession, period: Period) -> list[dict]:
    sql = f"""
    WITH {BASE_CTE}
    SELECT feature, count(DISTINCT user_id) AS customers, count(*) AS volume
      FROM customer_activity
     WHERE ts >= CAST(:start AS timestamp) AND ts < CAST(:end AS timestamp)
     GROUP BY feature
    """
    return await _all(db, sql, period.params)


async def tutor_stats(db: AsyncSession, period: Period) -> dict:
    """Uso del tutor por sesión. La duración va del inicio al ÚLTIMO
    mensaje, no a `ended_at`: muchos alumnos cierran la pestaña sin pulsar
    "terminar" y sus sesiones no tienen fin registrado."""
    sql = f"""
    WITH customers AS (SELECT id FROM users WHERE role = 'student'),
    sess AS (
        SELECT s.id, s.user_id, s.flash_course_id, s.module_id,
               {_local('s.started_at')} AS started_at,
               count(m.id) FILTER (WHERE m.role = 'user') AS learner_turns,
               count(m.id) FILTER (
                   WHERE m.role = 'assistant' AND m.corrections IS NOT NULL
                     AND jsonb_typeof(m.corrections) = 'array' AND jsonb_array_length(m.corrections) > 0
               ) AS corrected_turns,
               max(m.created_at) AS last_msg,
               s.started_at AS started_utc
          FROM conversation_sessions s
          JOIN customers c ON c.id = s.user_id
          LEFT JOIN conversation_messages m ON m.session_id = s.id
         GROUP BY s.id
    ),
    in_period AS (
        SELECT * FROM sess
         WHERE started_at >= CAST(:start AS timestamp) AND started_at < CAST(:end AS timestamp)
           AND learner_turns > 0
    )
    SELECT count(*) AS sessions,
           count(DISTINCT user_id) AS customers,
           coalesce(sum(learner_turns), 0) AS learner_turns,
           avg(learner_turns)::float AS avg_turns_per_session,
           (percentile_cont(0.5) WITHIN GROUP (
               ORDER BY extract(epoch FROM last_msg - started_utc) / 60.0))::float AS median_minutes,
           coalesce(sum(corrected_turns), 0) AS corrected_turns,
           count(*) FILTER (WHERE flash_course_id IS NOT NULL) AS library_sessions,
           count(*) FILTER (WHERE module_id IS NOT NULL) AS module_sessions
      FROM in_period
    """
    return await _one(db, sql, period.params)


async def activity_heatmap(db: AsyncSession, period: Period) -> list[dict]:
    """Práctica por día de la semana (1 = lunes) y hora local. Solo
    aprendizaje: abrir la app no es estudiar."""
    sql = f"""
    WITH {BASE_CTE}
    SELECT extract(isodow FROM ts)::int AS weekday,
           extract(hour FROM ts)::int AS hour,
           count(*) AS actions,
           count(DISTINCT user_id) AS customers
      FROM customer_activity
     WHERE ts >= CAST(:start AS timestamp) AND ts < CAST(:end AS timestamp)
       AND feature IN {LEARNING_FEATURES}
     GROUP BY 1, 2
    """
    return await _all(db, sql, period.params)


LIFECYCLE_CASE = """
    CASE
        WHEN c.created_at >= CAST(:end AS timestamp) - interval '7 days' THEN 'new'
        WHEN la.last_ts IS NULL THEN 'never_active'
        WHEN la.last_ts >= CAST(:end AS timestamp) - interval '7 days' THEN 'current'
        WHEN la.last_ts >= CAST(:end AS timestamp) - interval '30 days' THEN 'at_risk'
        ELSE 'dormant'
    END
"""


async def lifecycle(db: AsyncSession, period: Period) -> dict:
    """Modelo de crecimiento tipo Duolingo: en qué estado está HOY cada
    cliente, más la CURR (Current User Retention Rate): de los activos la
    semana pasada, cuántos siguen activos esta semana. Es el indicador que
    Duolingo identificó como el que más mueve el uso diario."""
    sql = f"""
    WITH {BASE_CTE},
    last_act AS (SELECT user_id, max(ts) AS last_ts FROM customer_activity GROUP BY user_id),
    segments AS (
        SELECT {LIFECYCLE_CASE} AS segment
          FROM customers c LEFT JOIN last_act la ON la.user_id = c.id
    ),
    last_week AS (
        SELECT DISTINCT user_id FROM customer_activity
         WHERE ts >= CAST(:end AS timestamp) - interval '14 days' AND ts < CAST(:end AS timestamp) - interval '7 days'
    ),
    this_week AS (
        SELECT DISTINCT user_id FROM customer_activity
         WHERE ts >= CAST(:end AS timestamp) - interval '7 days'
    )
    SELECT
        (SELECT json_object_agg(segment, n) FROM (SELECT segment, count(*) AS n FROM segments GROUP BY segment) x) AS segments,
        (SELECT count(*) FROM last_week) AS last_week_active,
        (SELECT count(*) FROM last_week JOIN this_week USING (user_id)) AS retained_this_week
    """
    return await _one(db, sql, period.params)


async def top_corrections(db: AsyncSession, period: Period, limit: int = 10) -> list[dict]:
    """Los errores que más corrige el tutor, agrupados por la regla que
    explica. Es la lista de "qué contenido falta o no está funcionando"."""
    sql = f"""
    SELECT corr ->> 'rule' AS rule,
           count(*) AS times,
           count(DISTINCT s.user_id) AS customers
      FROM conversation_messages m
      JOIN conversation_sessions s ON s.id = m.session_id
      JOIN users u ON u.id = s.user_id AND u.role = 'student'
     CROSS JOIN LATERAL jsonb_array_elements(
         CASE WHEN jsonb_typeof(m.corrections) = 'array' THEN m.corrections ELSE '[]'::jsonb END
     ) AS corr
     WHERE m.role = 'assistant'
       AND {_local('m.created_at')} >= CAST(:start AS timestamp)
       AND {_local('m.created_at')} < CAST(:end AS timestamp)
       AND coalesce(corr ->> 'rule', '') <> ''
     GROUP BY 1
     ORDER BY times DESC
     LIMIT :limit
    """
    return await _all(db, sql, {**period.params, "limit": limit})


async def screen_views(db: AsyncSession, period: Period) -> list[dict]:
    sql = f"""
    SELECT e.payload ->> 'path' AS path, count(*) AS views, count(DISTINCT e.user_id) AS customers
      FROM user_events e
      JOIN users u ON u.id = e.user_id AND u.role = 'student'
     WHERE e.event_type = 'page_viewed'
       AND {_local('e.created_at')} >= CAST(:start AS timestamp)
       AND {_local('e.created_at')} < CAST(:end AS timestamp)
     GROUP BY 1
     ORDER BY views DESC
    """
    return await _all(db, sql, period.params)


# ---------------------------------------------------------------------------
# Journey
# ---------------------------------------------------------------------------


async def journey_funnel(db: AsyncSession, period: Period) -> dict:
    """Embudo de la cohorte que se REGISTRÓ en el periodo. Las etapas están
    anidadas (cada una exige la anterior) para que el embudo nunca pueda
    ensancharse: quien pagó sin completar un módulo no cuenta en "de pago"
    del embudo, pero sí en `paid_any`, que se devuelve aparte."""
    sql = f"""
    WITH {BASE_CTE},
    cohort AS (
        SELECT id, created_at FROM customers
         WHERE created_at >= CAST(:start AS timestamp) AND created_at < CAST(:end AS timestamp)
    ),
    learn AS (SELECT user_id, ts FROM customer_activity WHERE feature IN {LEARNING_FEATURES}),
    first_learn AS (SELECT user_id, min(ts) AS t FROM learn GROUP BY user_id),
    learn_days AS (SELECT user_id, count(DISTINCT date_trunc('day', ts)) AS d FROM learn GROUP BY user_id),
    achievement AS (
        SELECT user_id, min({_local('created_at')}) AS t FROM user_events
         WHERE event_type IN ('module_completed', 'level_certified') GROUP BY user_id
    ),
    paid AS (
        SELECT user_id, min({_local('created_at')}) AS t FROM payments
         WHERE status = 'approved' GROUP BY user_id
    ),
    journey AS (
        SELECT co.id, co.created_at, fl.t AS activated_at, coalesce(ld.d, 0) AS learn_days,
               a.t AS achieved_at, p.t AS paid_at
          FROM cohort co
          LEFT JOIN first_learn fl ON fl.user_id = co.id
          LEFT JOIN learn_days ld ON ld.user_id = co.id
          LEFT JOIN achievement a ON a.user_id = co.id
          LEFT JOIN paid p ON p.user_id = co.id
    )
    SELECT count(*) AS registered,
           count(*) FILTER (WHERE activated_at IS NOT NULL) AS activated,
           count(*) FILTER (WHERE activated_at IS NOT NULL AND learn_days >= 3) AS engaged,
           count(*) FILTER (WHERE activated_at IS NOT NULL AND learn_days >= 3 AND achieved_at IS NOT NULL) AS achieved,
           count(*) FILTER (WHERE activated_at IS NOT NULL AND learn_days >= 3 AND achieved_at IS NOT NULL
                              AND paid_at IS NOT NULL) AS paid,
           count(*) FILTER (WHERE paid_at IS NOT NULL) AS paid_any,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM activated_at - created_at) / 3600.0))::float
               AS median_hours_to_activate,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM achieved_at - created_at) / 86400.0))::float
               AS median_days_to_achieve,
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM paid_at - created_at) / 86400.0))::float
               AS median_days_to_pay
      FROM journey
    """
    return await _one(db, sql, period.params)


async def module_progression(db: AsyncSession) -> list[dict]:
    """Por módulo (en el orden del currículo): cuántos clientes lo empezaron
    y cuántos lo completaron. Donde cae la curva es donde se atascan."""
    sql = """
    SELECT m.code, coalesce(m.title_es, m.title) AS title, l.code AS level_code,
           count(e.id) AS started,
           count(e.id) FILTER (WHERE e.status = 'completed') AS completed
      FROM modules m
      JOIN cefr_levels l ON l.id = m.level_id
      LEFT JOIN enrollments e ON e.module_id = m.id
           AND e.user_id IN (SELECT id FROM users WHERE role = 'student')
     GROUP BY m.id, m.code, m.title_es, m.title, l.code, l."order", m."order"
    HAVING count(e.id) > 0 OR l.code = 'A1'
     ORDER BY l."order", m."order"
    """
    return await _all(db, sql, {})


async def learning_outcomes(db: AsyncSession, period: Period) -> dict:
    sql = f"""
    WITH ev AS (
        SELECT e.event_type, e.payload
          FROM user_events e
          JOIN users u ON u.id = e.user_id AND u.role = 'student'
         WHERE {_local('e.created_at')} >= CAST(:start AS timestamp)
           AND {_local('e.created_at')} < CAST(:end AS timestamp)
    )
    SELECT count(*) FILTER (WHERE event_type = 'module_exam_submitted') AS exams_taken,
           count(*) FILTER (WHERE event_type = 'module_exam_submitted' AND (payload ->> 'passed')::boolean) AS exams_passed,
           count(*) FILTER (WHERE event_type = 'module_completed') AS modules_completed,
           count(*) FILTER (WHERE event_type = 'level_certified') AS levels_certified,
           count(*) FILTER (WHERE event_type = 'chat_task_attempted') AS tutor_tasks,
           count(*) FILTER (WHERE event_type = 'chat_task_attempted' AND (payload ->> 'completed')::boolean) AS tutor_tasks_completed
      FROM ev
    """
    return await _one(db, sql, period.params)


async def level_distribution(db: AsyncSession) -> list[dict]:
    sql = """
    SELECT coalesce(l.code, 'none') AS level_code, count(*) AS customers
      FROM users u
      LEFT JOIN cefr_levels l ON l.id = u.current_level_id
     WHERE u.role = 'student'
     GROUP BY l.code, l."order"
     ORDER BY l."order" NULLS LAST
    """
    return await _all(db, sql, {})


# ---------------------------------------------------------------------------
# Retención
# ---------------------------------------------------------------------------


async def cohort_retention(db: AsyncSession, weeks: int) -> list[dict]:
    """Filas (semana de alta, semanas desde el alta, clientes activos esa
    semana). La matriz se arma en el router; aquí solo se cuenta."""
    sql = f"""
    WITH {BASE_CTE},
    cohorts AS (
        SELECT id AS user_id, date_trunc('week', created_at) AS cohort_week FROM customers
         WHERE created_at >= date_trunc('week', CAST(:end AS timestamp)) - (CAST(:weeks AS int) - 1) * interval '1 week'
    ),
    weekly AS (
        SELECT DISTINCT a.user_id, date_trunc('week', a.ts) AS active_week
          FROM customer_activity a JOIN cohorts USING (user_id)
    )
    SELECT c.cohort_week,
           (SELECT count(*) FROM cohorts c2 WHERE c2.cohort_week = c.cohort_week) AS cohort_size,
           round(extract(epoch FROM w.active_week - c.cohort_week) / 604800)::int AS week_offset,
           count(DISTINCT w.user_id) AS retained
      FROM cohorts c
      LEFT JOIN weekly w ON w.user_id = c.user_id AND w.active_week >= c.cohort_week
     GROUP BY c.cohort_week, week_offset
     ORDER BY c.cohort_week, week_offset
    """
    return await _all(db, sql, {"end": local_now(), "tz": settings.analytics_timezone, "weeks": weeks})


async def day_n_retention(db: AsyncSession, day_marks: tuple[int, ...] = (1, 7, 30)) -> list[dict]:
    """Retención clásica "día N": de los clientes que se registraron hace al
    menos N+1 días, cuántos usaron la app EXACTAMENTE el día N tras el alta
    (entre las 24·N y las 24·(N+1) horas). Es la definición que usan
    Amplitude y las comparativas del sector, así que se puede comparar.

    Se calcula el "día desde el alta" de cada actividad UNA vez y se cruza,
    en vez de un EXISTS por cliente y día: con 40k filas de actividad el
    EXISTS tardaba 6 s; así, milisegundos."""
    marks = ", ".join(f"({int(n)})" for n in day_marks)
    sql = f"""
    WITH {BASE_CTE},
    user_days AS (
        SELECT DISTINCT a.user_id, floor(extract(epoch FROM a.ts - c.created_at) / 86400)::int AS day_n
          FROM customer_activity a
          JOIN customers c ON c.id = a.user_id
         WHERE a.ts >= c.created_at
    ),
    marks(day) AS (VALUES {marks})
    SELECT marks.day,
           count(c.id) AS eligible,
           count(ud.user_id) AS retained
      FROM marks
      JOIN customers c ON c.created_at <= CAST(:end AS timestamp) - (marks.day + 1) * interval '1 day'
      LEFT JOIN user_days ud ON ud.user_id = c.id AND ud.day_n = marks.day
     GROUP BY marks.day
     ORDER BY marks.day
    """
    return await _all(db, sql, {"end": local_now(), "tz": settings.analytics_timezone})


# ---------------------------------------------------------------------------
# Ingresos
# ---------------------------------------------------------------------------


async def revenue_breakdown(db: AsyncSession, period: Period) -> dict:
    sql = f"""
    WITH customers AS (SELECT id FROM users WHERE role = 'student'),
    pays AS (
        SELECT p.provider, p.status, p.amount_cents, {_local('p.created_at')} AS at
          FROM payments p JOIN customers c ON c.id = p.user_id
    ),
    subs AS (
        SELECT s.*, {_local('s.created_at')} AS created_local,
               {_local('s.canceled_at')} AS canceled_local,
               {_local('s.current_period_end')} AS period_end_local
          FROM subscriptions s JOIN customers c ON c.id = s.user_id
    )
    SELECT
        (SELECT json_agg(x) FROM (
            SELECT provider, count(*) AS payments, sum(amount_cents) AS amount_cents
              FROM pays
             WHERE status = 'approved' AND at >= CAST(:start AS timestamp) AND at < CAST(:end AS timestamp)
             GROUP BY provider ORDER BY sum(amount_cents) DESC
        ) x) AS by_provider,
        (SELECT json_agg(x) FROM (
            SELECT status, count(*) AS payments, sum(amount_cents) AS amount_cents
              FROM pays
             WHERE at >= CAST(:start AS timestamp) AND at < CAST(:end AS timestamp)
             GROUP BY status ORDER BY count(*) DESC
        ) x) AS by_status,
        (SELECT json_object_agg(status, n) FROM (SELECT status, count(*) AS n FROM subs GROUP BY status) x)
            AS subscriptions_by_status,
        (SELECT count(*) FROM pays WHERE status = 'pending_verification') AS pending_verification,
        (SELECT coalesce(sum(amount_cents), 0) FROM pays WHERE status = 'pending_verification') AS pending_verification_cents,
        -- Suscriptores al empezar el periodo: nacidos antes y todavía no
        -- cancelados ni vencidos en ese momento.
        (SELECT count(*) FROM subs
          WHERE created_local < CAST(:start AS timestamp)
            AND status <> 'pending'
            AND (canceled_local IS NULL OR canceled_local >= CAST(:start AS timestamp))
            AND NOT (status = 'expired' AND period_end_local < CAST(:start AS timestamp))) AS subscribers_at_start,
        -- Las que nacieron DENTRO del periodo también pueden darse de baja
        -- en él: si no entran en el denominador, con una base que crece el
        -- churn sale inflado (llegó a dar 7 bajas "de 7" con 21 activas).
        (SELECT count(*) FROM subs
          WHERE created_local >= CAST(:start AS timestamp) AND created_local < CAST(:end AS timestamp)
            AND status <> 'pending') AS new_subscribers,
        (SELECT count(*) FROM subs
          WHERE (canceled_local >= CAST(:start AS timestamp) AND canceled_local < CAST(:end AS timestamp))
             OR (status = 'expired' AND canceled_local IS NULL
                 AND period_end_local >= CAST(:start AS timestamp) AND period_end_local < CAST(:end AS timestamp)))
            AS churned_in_period
    """
    return await _one(db, sql, period.params)


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

CUSTOMER_SORTS = {
    "last_active": "last_active_at DESC NULLS LAST",
    "signup": "created_at DESC",
    "messages": "tutor_messages DESC",
    "paid": "total_paid_cents DESC",
    "name": "full_name ASC",
}

CUSTOMERS_CTE = f"""
{BASE_CTE},
last_act AS (
    SELECT user_id, max(ts) AS last_ts,
           count(DISTINCT date_trunc('day', ts)) FILTER (
               WHERE ts >= CAST(:end AS timestamp) - interval '30 days') AS days_30
      FROM customer_activity GROUP BY user_id
),
msgs AS (
    SELECT s.user_id, count(*) AS n
      FROM conversation_messages m JOIN conversation_sessions s ON s.id = m.session_id
     WHERE m.role = 'user' GROUP BY s.user_id
),
mods AS (SELECT user_id, count(*) FILTER (WHERE status = 'completed') AS completed FROM enrollments GROUP BY user_id),
paid AS (SELECT user_id, sum(amount_cents) FILTER (WHERE status = 'approved') AS total FROM payments GROUP BY user_id),
sub AS (
    SELECT DISTINCT ON (user_id) user_id, status, {_local('current_period_end')} AS period_end
      FROM subscriptions ORDER BY user_id, created_at DESC
),
customer_rows AS (
    SELECT u.id, u.full_name, u.email, c.created_at, lv.code AS level_code,
           la.last_ts AS last_active_at, coalesce(la.days_30, 0) AS active_days_30,
           coalesce(msgs.n, 0) AS tutor_messages, coalesce(mods.completed, 0) AS modules_completed,
           coalesce(sub.status, 'free') AS subscription_status, sub.period_end AS subscription_period_end,
           coalesce(paid.total, 0) AS total_paid_cents,
           {LIFECYCLE_CASE} AS segment
      FROM users u
      JOIN customers c ON c.id = u.id
      LEFT JOIN cefr_levels lv ON lv.id = u.current_level_id
      LEFT JOIN last_act la ON la.user_id = u.id
      LEFT JOIN msgs ON msgs.user_id = u.id
      LEFT JOIN mods ON mods.user_id = u.id
      LEFT JOIN paid ON paid.user_id = u.id
      LEFT JOIN sub ON sub.user_id = u.id
)
"""


async def list_customers(
    db: AsyncSession, *, search: str | None, segment: str | None, sort: str, limit: int, offset: int
) -> tuple[list[dict], int]:
    order_by = CUSTOMER_SORTS.get(sort, CUSTOMER_SORTS["last_active"])
    where = """
     WHERE (CAST(:search AS text) IS NULL OR full_name ILIKE CAST(:search AS text) OR email ILIKE CAST(:search AS text))
       AND (CAST(:segment AS text) IS NULL OR segment = CAST(:segment AS text))
    """
    params = {
        "end": local_now(),
        "tz": settings.analytics_timezone,
        "search": f"%{search.strip()}%" if search and search.strip() else None,
        "segment": segment,
    }
    rows = await _all(
        db,
        f"WITH {CUSTOMERS_CTE} SELECT * FROM customer_rows {where} ORDER BY {order_by}, id LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset},
    )
    total = await _one(db, f"WITH {CUSTOMERS_CTE} SELECT count(*) AS n FROM customer_rows {where}", params)
    return rows, total["n"]


async def get_customer(db: AsyncSession, user_id) -> dict | None:
    params = {"end": local_now(), "tz": settings.analytics_timezone, "user_id": user_id}
    result = await db.execute(
        text(f"WITH {CUSTOMERS_CTE} SELECT * FROM customer_rows WHERE id = :user_id"), params
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def customer_milestones(db: AsyncSession, user_id) -> dict:
    sql = f"""
    WITH {BASE_CTE}
    SELECT
        (SELECT min(ts) FROM customer_activity WHERE user_id = :user_id AND feature IN {LEARNING_FEATURES}) AS first_learning_at,
        (SELECT min(ts) FROM customer_activity WHERE user_id = :user_id AND feature = 'tutor') AS first_tutor_at,
        (SELECT min({_local('created_at')}) FROM user_events
          WHERE user_id = :user_id AND event_type = 'module_completed') AS first_module_completed_at,
        (SELECT min({_local('created_at')}) FROM user_events
          WHERE user_id = :user_id AND event_type = 'level_certified') AS first_level_certified_at,
        (SELECT min({_local('created_at')}) FROM payments
          WHERE user_id = :user_id AND status = 'approved') AS first_payment_at,
        (SELECT count(*) FROM conversation_sessions WHERE user_id = :user_id) AS tutor_sessions,
        (SELECT count(*) FROM exercise_attempts WHERE user_id = :user_id) AS exam_answers,
        (SELECT count(*) FROM enrollments WHERE user_id = :user_id AND status = 'in_progress') AS modules_in_progress,
        (SELECT count(DISTINCT date_trunc('day', ts)) FROM customer_activity WHERE user_id = :user_id) AS active_days_total
    """
    return await _one(db, sql, {"user_id": user_id, "tz": settings.analytics_timezone})


async def customer_daily_activity(db: AsyncSession, user_id, days: int = 91) -> list[dict]:
    sql = f"""
    WITH {BASE_CTE}
    SELECT date_trunc('day', ts)::date AS day, count(*) AS actions
      FROM customer_activity
     WHERE user_id = :user_id AND feature IN {LEARNING_FEATURES}
       AND ts >= date_trunc('day', CAST(:end AS timestamp)) - CAST(:days AS int) * interval '1 day'
     GROUP BY 1 ORDER BY 1
    """
    return await _all(db, sql, {"user_id": user_id, "tz": settings.analytics_timezone, "end": local_now(), "days": days})


async def customer_timeline(db: AsyncSession, user_id, limit: int = 40) -> list[dict]:
    """Lo último que hizo el cliente, de más reciente a más antiguo. De las
    conversaciones con el tutor solo se muestra CUÁNTO habló, nunca QUÉ
    dijo: gerencia necesita el comportamiento, no leer sus mensajes."""
    sql = f"""
    SELECT * FROM (
        SELECT {_local('s.started_at')} AS at, 'tutor_session' AS kind,
               json_build_object(
                   'turns', (SELECT count(*) FROM conversation_messages m WHERE m.session_id = s.id AND m.role = 'user'),
                   'library', s.flash_course_id IS NOT NULL,
                   'module', s.module_id IS NOT NULL
               ) AS detail
          FROM conversation_sessions s WHERE s.user_id = :user_id
        UNION ALL
        SELECT {_local('created_at')}, event_type, payload::json
          FROM user_events
         WHERE user_id = :user_id AND event_type NOT IN ('page_viewed', 'chat_task_attempted')
        UNION ALL
        SELECT {_local('created_at')}, 'payment',
               json_build_object('status', status, 'provider', provider, 'amount_cents', amount_cents)
          FROM payments WHERE user_id = :user_id
        UNION ALL
        SELECT {_local('canceled_at')}, 'subscription_canceled', json_build_object('provider', provider)
          FROM subscriptions WHERE user_id = :user_id AND canceled_at IS NOT NULL
    ) t
    WHERE at IS NOT NULL
    ORDER BY at DESC
    LIMIT :limit
    """
    return await _all(db, sql, {"user_id": user_id, "tz": settings.analytics_timezone, "limit": limit})


async def customer_top_corrections(db: AsyncSession, user_id, limit: int = 5) -> list[dict]:
    """Solo la REGLA y cuántas veces: el patrón de error del alumno sirve
    para ayudarle; la frase exacta que escribió no le hace falta a nadie."""
    sql = """
    SELECT corr ->> 'rule' AS rule, count(*) AS times
      FROM conversation_messages m
      JOIN conversation_sessions s ON s.id = m.session_id
     CROSS JOIN LATERAL jsonb_array_elements(
         CASE WHEN jsonb_typeof(m.corrections) = 'array' THEN m.corrections ELSE '[]'::jsonb END
     ) AS corr
     WHERE s.user_id = :user_id AND m.role = 'assistant' AND coalesce(corr ->> 'rule', '') <> ''
     GROUP BY 1 ORDER BY times DESC LIMIT :limit
    """
    return await _all(db, sql, {"user_id": user_id, "limit": limit})
