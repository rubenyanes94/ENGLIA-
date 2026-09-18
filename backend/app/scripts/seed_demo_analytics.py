"""Clientes de DEMOSTRACIÓN para desarrollar y enseñar el panel de gerencia.

Con tres alumnos reales, todas las gráficas de gerencia salen planas: no
se puede comprobar si un embudo, una matriz de cohortes o un mapa de
horas se leen bien. Este script genera ~240 alumnos ficticios con seis
meses de historia coherente entre tablas: se registran, practican con el
tutor (con correcciones), hacen exámenes de módulo, completan módulos,
algunos certifican nivel, algunos pagan y algunos cancelan.

Todo lo que crea cuelga de usuarios con email `demo+NNN@example.com`
(example.com es un dominio reservado para documentación: jamás será el
correo de un cliente real), así que se puede borrar entero sin tocar nada
más:

    python -m app.scripts.seed_demo_analytics            # crea (o recrea) la demo
    python -m app.scripts.seed_demo_analytics --purge    # la borra

Se niega a correr si ENVIRONMENT no es "development": estos datos no
pueden acabar mezclados con los de clientes reales.
"""

import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, insert, select, text

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    AgentPersona,
    CEFRLevel,
    ConversationMessage,
    ConversationSession,
    Enrollment,
    Exercise,
    ExerciseAttempt,
    FlashCourse,
    FlashCourseProgress,
    Lesson,
    Module,
    Payment,
    Plan,
    SentenceGameProgress,
    Subscription,
    User,
    UserEvent,
)

DEMO_EMAIL_PATTERN = "demo+%@example.com"
N_CUSTOMERS = 240
HISTORY_DAYS = 180
SEED = 20260918

FIRST_NAMES = [
    "María", "José", "Luis", "Ana", "Carlos", "Daniela", "Andrés", "Valentina", "Miguel", "Gabriela",
    "Jesús", "Andrea", "Pedro", "Carolina", "Juan", "Isabel", "Ricardo", "Paola", "Fernando", "Sofía",
    "Alejandro", "Camila", "Diego", "Mariana", "Rafael", "Lucía", "Jorge", "Natalia", "Héctor", "Adriana",
]
LAST_NAMES = [
    "González", "Rodríguez", "Pérez", "Hernández", "García", "Martínez", "López", "Díaz", "Romero", "Sánchez",
    "Torres", "Ramírez", "Flores", "Rojas", "Morales", "Castillo", "Mendoza", "Vargas", "Suárez", "Medina",
]

# Errores típicos de hispanohablante, con la MISMA redacción de regla cada
# vez: el panel agrupa por regla para decir "qué es lo que más se falla".
CORRECTIONS = [
    ("I have 25 years", "I am 25 years old", "La edad se dice con 'to be', no con 'to have'."),
    ("She work in a bank", "She works in a bank", "Tercera persona del singular: el verbo lleva -s."),
    ("Is raining", "It is raining", "En inglés el sujeto no se omite: hace falta 'it'."),
    ("I am agree", "I agree", "'Agree' es un verbo: no va con 'to be'."),
    ("The people is nice", "The people are nice", "'People' es plural: va con 'are'."),
    ("A car red", "A red car", "El adjetivo va antes del sustantivo."),
    ("I go to the home", "I go home", "'Home' no lleva artículo tras verbos de movimiento."),
    ("Give me a coffee", "Could I have a coffee, please?", "Para pedir algo, 'give me' suena brusco: usa 'could I have'."),
    ("I am boring", "I am bored", "-ed describe cómo te sientes; -ing, lo que causa el sentimiento."),
    ("Yesterday I go", "Yesterday I went", "Pasado simple: 'go' es irregular, 'went'."),
]

LEARNER_LINES = [
    "Hello, my name is {name}.", "I live in Caracas.", "I work in a office.", "I like to play football.",
    "Yesterday I go to the beach.", "My sister is doctor.", "I have 25 years.", "What time is it?",
    "Can you repeat please?", "I want to practice for my job interview.", "She work in a bank.",
    "The people is very friendly.", "I am agree with you.", "I would like a coffee.",
]

# Perfiles de uso. Son los que dan forma a las curvas: la mayoría abandona
# pronto (como en cualquier app de idiomas), y un núcleo pequeño sostiene
# el uso y paga. `daily_p` es la probabilidad de estar activo cada día al
# principio; `half_life` cuántos días tarda en caer a la mitad.
PROFILES = [
    # nombre, peso, daily_p, half_life, prob. de pagar, msgs por sesión
    ("solo_registro", 0.14, 0.0, 1, 0.0, (1, 1)),  # se registra y no vuelve a entrar
    ("se_va_pronto", 0.30, 0.45, 3, 0.02, (2, 5)),
    ("casual", 0.34, 0.30, 25, 0.12, (3, 7)),
    ("constante", 0.22, 0.55, 90, 0.38, (4, 10)),
    ("intensivo", 0.06, 0.85, 400, 0.65, (6, 14)),
]

# Hora local de estudio: picos antes del trabajo, al mediodía y de noche.
HOUR_WEIGHTS = [
    1, 0, 0, 0, 0, 1, 4, 9, 8, 4, 3, 4, 7, 7, 4, 3, 3, 4, 6, 10, 13, 12, 8, 3,
]
LOCAL_TZ = ZoneInfo(settings.analytics_timezone)
PROVIDERS = [("pago_movil", 0.40), ("paypal", 0.25), ("credit_card", 0.20), ("binance_pay", 0.15)]


def utcnow() -> datetime:
    # Las columnas son TIMESTAMP sin zona y el backend escribe UTC (func.now()
    # del contenedor de Postgres): la demo tiene que usar la misma referencia.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def weighted(rng: random.Random, pairs):
    total = sum(w for _, w in pairs)
    x = rng.random() * total
    for value, w in pairs:
        x -= w
        if x <= 0:
            return value
    return pairs[-1][0]


def at_hour(rng: random.Random, day: datetime) -> datetime:
    """Una hora de estudio creíble ese día. HOUR_WEIGHTS está en hora
    LOCAL del negocio (el alumno estudia a las 8 de la noche de Caracas,
    no de Greenwich), y se guarda convertida a UTC como cualquier dato real."""
    hour = weighted(rng, list(enumerate(HOUR_WEIGHTS)))
    local = day.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60), microsecond=0, tzinfo=LOCAL_TZ)
    return local.astimezone(timezone.utc).replace(tzinfo=None)


async def purge(session) -> int:
    demo_ids = select(User.id).where(User.email.like(DEMO_EMAIL_PATTERN))
    demo_sessions = select(ConversationSession.id).where(ConversationSession.user_id.in_(demo_ids))
    await session.execute(delete(ConversationMessage).where(ConversationMessage.session_id.in_(demo_sessions)))
    for model in (
        ConversationSession, ExerciseAttempt, Enrollment, UserEvent, Payment,
        Subscription, FlashCourseProgress, SentenceGameProgress,
    ):
        await session.execute(delete(model).where(model.user_id.in_(demo_ids)))
    # descriptor_evidence no se genera, pero si alguien practicó con una
    # cuenta demo a mano, también hay que llevársela para poder borrar al usuario.
    await session.execute(text("DELETE FROM descriptor_evidence WHERE user_id IN (SELECT id FROM users WHERE email LIKE :p)"), {"p": DEMO_EMAIL_PATTERN})
    result = await session.execute(delete(User).where(User.email.like(DEMO_EMAIL_PATTERN)))
    await session.commit()
    return result.rowcount or 0


async def seed() -> None:
    rng = random.Random(SEED)
    now = utcnow()

    async with AsyncSessionLocal() as session:
        removed = await purge(session)
        if removed:
            print(f"Demo anterior borrada ({removed} clientes).")

        levels = {l.code: l for l in (await session.execute(select(CEFRLevel))).scalars()}
        personas = {
            p.level_id: p
            for p in (await session.execute(select(AgentPersona).where(AgentPersona.is_active.is_(True)))).scalars()
        }
        a1_modules = list(
            (
                await session.execute(
                    select(Module).where(Module.level_id == levels["A1"].id).order_by(Module.order)
                )
            ).scalars()
        )
        exam_by_module: dict[uuid.UUID, list[uuid.UUID]] = {}
        rows = await session.execute(
            select(Exercise.id, Lesson.module_id).join(Lesson, Lesson.id == Exercise.lesson_id).where(Exercise.stage == "exam")
        )
        for exercise_id, module_id in rows:
            exam_by_module.setdefault(module_id, []).append(exercise_id)
        flash_courses = list((await session.execute(select(FlashCourse))).scalars())
        plan = (await session.execute(select(Plan).where(Plan.code == "premium_monthly"))).scalars().first()
        if plan is None or not a1_modules or not personas:
            print("Faltan datos base (plan premium_monthly, módulos A1 o tutores). Corre los seeds del currículo primero.")
            return

        password = hash_password("demo-no-login-" + uuid.uuid4().hex)
        users, sessions, messages, attempts, enrollments, events = [], [], [], [], [], []
        subscriptions, payments, flash_progress, game_progress = [], [], [], []

        for i in range(1, N_CUSTOMERS + 1):
            # Altas con crecimiento: más registros cuanto más reciente
            # (sqrt sesga hacia el final del rango).
            age_days = int(HISTORY_DAYS * (1 - rng.random() ** 0.6))
            signup = at_hour(rng, now - timedelta(days=age_days))
            if signup > now:
                signup = now - timedelta(minutes=rng.randrange(30, 600))

            profile = weighted(rng, [(p, p[1]) for p in PROFILES])
            _, _, daily_p, half_life, pay_p, msg_range = profile

            level_code = weighted(rng, [("A1", 0.55), ("A2", 0.25), ("B1", 0.14), ("B2", 0.06)])
            first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
            user_id = uuid.uuid4()
            users.append(dict(
                id=user_id, email=f"demo+{i:03d}@example.com", hashed_password=password,
                full_name=f"{first} {last}", native_language="es", role="student",
                current_level_id=levels[level_code].id if rng.random() > 0.12 else None,
                notifications_enabled=rng.random() > 0.3, is_active=True, created_at=signup,
            ))
            persona = personas.get(levels[level_code].id) or next(iter(personas.values()))

            # --- Días activos ------------------------------------------------
            active_days: list[datetime] = []
            day = signup.replace(hour=0, minute=0, second=0, microsecond=0)
            d = 0
            while day <= now:
                p = daily_p * 0.5 ** (d / half_life)
                if day.weekday() >= 5:
                    p *= 0.7  # el fin de semana se estudia menos
                if d == 0 and daily_p > 0:
                    p = max(p, 0.6)  # la mayoría prueba algo el mismo día del alta
                if rng.random() < p:
                    active_days.append(day)
                day += timedelta(days=1)
                d += 1

            # --- Tutor, biblioteca, eventos de navegación --------------------
            for day in active_days:
                start = at_hour(rng, day)
                if day.date() == signup.date():
                    start = max(start, signup + timedelta(minutes=rng.randrange(2, 40)))
                if start > now:
                    continue
                use_library = flash_courses and rng.random() < 0.18
                # Practicar DENTRO de un módulo (con su tarea comunicativa) en
                # vez de charla libre: ~30 % de las sesiones que no son de biblioteca.
                practice_module = rng.choice(a1_modules[:4]) if not use_library and rng.random() < 0.3 else None
                session_id = uuid.uuid4()
                n_msgs = rng.randint(*msg_range)
                t = start
                for _ in range(n_msgs):
                    t += timedelta(seconds=rng.randrange(25, 110))
                    line = rng.choice(LEARNER_LINES).format(name=first)
                    messages.append(dict(id=uuid.uuid4(), session_id=session_id, role="user", content=line, corrections=None, created_at=t))
                    corrections = None
                    if rng.random() < 0.45:
                        err, fix, rule = rng.choice(CORRECTIONS)
                        corrections = [{"error": err, "correction": fix, "rule": rule}]
                    t += timedelta(seconds=rng.randrange(2, 6))
                    messages.append(dict(id=uuid.uuid4(), session_id=session_id, role="assistant", content="(respuesta de demostración)", corrections=corrections, created_at=t))
                ended = t + timedelta(seconds=rng.randrange(20, 90)) if rng.random() < 0.7 else None
                sessions.append(dict(
                    id=session_id, user_id=user_id, persona_id=persona.id,
                    module_id=practice_module.id if practice_module else None,
                    flash_course_id=rng.choice(flash_courses).id if use_library else None,
                    started_at=start, ended_at=ended,
                ))
                if practice_module is not None and rng.random() < 0.7:
                    events.append(dict(
                        id=uuid.uuid4(), user_id=user_id, event_type="chat_task_attempted",
                        payload={"session_id": str(session_id), "task_id": "demo", "descriptor": "A1.SI.01",
                                 "completed": rng.random() < 0.62, "scaffolded": rng.random() < 0.3},
                        created_at=t,
                    ))
                for path in rng.sample(["/dashboard", "/classroom", "/chat", "/progress", "/library", "/profile"], rng.randint(1, 3)):
                    events.append(dict(id=uuid.uuid4(), user_id=user_id, event_type="page_viewed", payload={"path": path}, created_at=start - timedelta(minutes=rng.randrange(1, 5))))

            # --- Módulos A1: inscripción, examen, completado -----------------
            n_days = len(active_days)
            modules_reached = min(len(a1_modules), n_days // 4)
            for k, module in enumerate(a1_modules[:modules_reached]):
                started = active_days[min(k * 4, n_days - 1)] + timedelta(hours=rng.randint(7, 21))
                if started > now:
                    break
                completed = rng.random() < 0.72 and k * 4 + 3 < n_days
                completed_at = active_days[min(k * 4 + 3, n_days - 1)] + timedelta(hours=rng.randint(7, 21)) if completed else None
                if completed_at and completed_at > now:
                    completed, completed_at = False, None
                enrollments.append(dict(
                    id=uuid.uuid4(), user_id=user_id, module_id=module.id,
                    status="completed" if completed else "in_progress",
                    mastery_score=round(rng.uniform(0.8, 0.98), 2) if completed else round(rng.uniform(0.2, 0.7), 2),
                    started_at=started, completed_at=completed_at,
                ))
                events.append(dict(id=uuid.uuid4(), user_id=user_id, event_type="module_enrolled", payload={"module_id": str(module.id)}, created_at=started))
                exam_ids = exam_by_module.get(module.id, [])
                sittings = 1 + (rng.random() < 0.35)
                for s in range(sittings):
                    last_try = s == sittings - 1
                    passed = completed and last_try
                    exam_at = (completed_at if passed else started + timedelta(days=rng.randint(1, 3)))
                    if exam_at is None or exam_at > now:
                        continue
                    score = round(rng.uniform(0.8, 1.0) if passed else rng.uniform(0.35, 0.78), 2)
                    for ex_id in exam_ids[:8]:
                        attempts.append(dict(id=uuid.uuid4(), user_id=user_id, exercise_id=ex_id, response={"demo": True}, score=1.0 if rng.random() < score else 0.0, attempted_at=exam_at))
                    events.append(dict(id=uuid.uuid4(), user_id=user_id, event_type="module_exam_submitted", payload={"module_id": str(module.id), "score": score, "passed": passed}, created_at=exam_at))
                if completed:
                    events.append(dict(id=uuid.uuid4(), user_id=user_id, event_type="module_completed", payload={"module_id": str(module.id)}, created_at=completed_at))
            if modules_reached >= 9 and rng.random() < 0.6:
                events.append(dict(id=uuid.uuid4(), user_id=user_id, event_type="level_certified", payload={"level_code": "A1", "next_level_code": "A2", "source": "demo"}, created_at=active_days[-1] + timedelta(hours=20)))

            # --- Biblioteca y juego -----------------------------------------
            if flash_courses and n_days >= 3 and rng.random() < 0.35:
                course = rng.choice(flash_courses)
                done = rng.random() < 0.4
                started = active_days[1] + timedelta(hours=18)
                if started <= now:
                    flash_progress.append(dict(id=uuid.uuid4(), user_id=user_id, course_id=course.id, completed_scenarios=["s1", "s2"] if done else ["s1"], started_at=started, completed_at=started + timedelta(days=2) if done and started + timedelta(days=2) <= now else None))
            if n_days >= 2 and rng.random() < 0.5:
                answered = rng.randint(10, 40) * max(1, n_days // 5)
                game_progress.append(dict(user_id=user_id, level=1 + answered // 60, level_progress=answered % 10, total_answered=answered, total_correct=int(answered * rng.uniform(0.55, 0.9)), streak=rng.randint(0, 8), best_streak=rng.randint(5, 25), pending_item_id=None, recent_item_ids=[], updated_at=active_days[-1] + timedelta(hours=rng.randint(7, 22))))

            # --- Suscripción y pagos ----------------------------------------
            # Pagan más los que más usan: la conversión sale del uso, no al revés.
            if n_days >= 2 and rng.random() < pay_p:
                provider = weighted(rng, PROVIDERS)
                sub_start = active_days[min(len(active_days) - 1, rng.randint(1, 6))] + timedelta(hours=rng.randint(8, 22))
                if sub_start > now:
                    continue
                sub_id = uuid.uuid4()
                auto_renew = provider in ("paypal", "credit_card")
                months_kept = 1 + int(rng.expovariate(1 / (6 if profile[0] in ("constante", "intensivo") else 2)))
                period_start = sub_start
                paid_months = 0
                canceled_at = None
                pending_last = False
                while period_start <= now and paid_months < months_kept:
                    pay_status = "approved"
                    if provider == "pago_movil" and now - period_start < timedelta(days=2) and rng.random() < 0.6:
                        pay_status = "pending_verification"
                        pending_last = True
                    elif rng.random() < 0.04:
                        pay_status = rng.choice(["rejected", "failed"])
                    payments.append(dict(
                        id=uuid.uuid4(), user_id=user_id, subscription_id=sub_id, provider=provider,
                        amount_cents=plan.price_cents, currency="USD", status=pay_status,
                        external_reference=None if provider == "pago_movil" else f"demo-{uuid.uuid4().hex[:10]}",
                        payload={"demo": True}, created_at=period_start,
                    ))
                    if pay_status in ("rejected", "failed"):
                        canceled_at = period_start + timedelta(hours=6)
                        break
                    paid_months += 1
                    period_start += timedelta(days=30)
                period_end = period_start
                if canceled_at is not None:
                    status = "canceled"
                elif pending_last:
                    status = "pending"
                elif period_end > now:
                    status = "active"
                elif auto_renew:
                    status = "canceled"
                    canceled_at = period_end - timedelta(days=rng.randint(1, 10))
                else:
                    status = "expired"
                subscriptions.append(dict(
                    id=sub_id, user_id=user_id, plan_id=plan.id, status=status, provider=provider,
                    provider_subscription_id=f"demo-sub-{uuid.uuid4().hex[:8]}" if auto_renew else None,
                    auto_renew=auto_renew, current_period_start=period_end - timedelta(days=30),
                    current_period_end=period_end, canceled_at=canceled_at, created_at=sub_start,
                ))

        # Ningún dato en el futuro: los hitos se colocan "a las N horas" de
        # un día activo, y si ese día es hoy pueden pasarse de la hora actual.
        # Se recolocan en las últimas horas en vez de descartarlos, para no
        # romper la coherencia entre tablas (un módulo completado sin su evento).
        for rows in (sessions, messages, enrollments, attempts, events, subscriptions, payments, flash_progress, game_progress):
            for row in rows:
                for key, value in row.items():
                    if isinstance(value, datetime) and value > now:
                        row[key] = now - timedelta(minutes=rng.randint(5, 240))

        # Orden de inserción = orden de las FK.
        for model, rows in (
            (User, users), (ConversationSession, sessions), (ConversationMessage, messages),
            (Enrollment, enrollments), (ExerciseAttempt, attempts), (UserEvent, events),
            (Subscription, subscriptions), (Payment, payments), (FlashCourseProgress, flash_progress),
            (SentenceGameProgress, game_progress),
        ):
            for chunk in range(0, len(rows), 2000):
                await session.execute(insert(model), rows[chunk:chunk + 2000])
        await session.commit()

        print(
            f"Demo creada: {len(users)} clientes, {len(sessions)} sesiones con el tutor, "
            f"{len(messages)} mensajes, {len(attempts)} respuestas de examen, {len(enrollments)} inscripciones, "
            f"{len(events)} eventos, {len(subscriptions)} suscripciones, {len(payments)} pagos."
        )


async def main() -> None:
    if settings.environment != "development":
        print(f"ENVIRONMENT={settings.environment!r}: la demo solo se genera en desarrollo.")
        sys.exit(1)
    if "--purge" in sys.argv:
        async with AsyncSessionLocal() as session:
            removed = await purge(session)
        print(f"Demo borrada: {removed} clientes y todo lo que colgaba de ellos.")
        return
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
