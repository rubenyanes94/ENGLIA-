"""Panel de gerencia: analítica de clientes, de SOLO LECTURA.

Todo detrás de get_current_manager (rol "manager" o "admin"). Ningún
endpoint aquí escribe nada: gerencia mira, no toca — aprobar pagos o
editar contenido sigue siendo cosa de /admin.

Las consultas viven en repositories/analytics_repository.py; aquí solo se
derivan las tasas (con None cuando no hay denominador) y se da forma a la
respuesta.
"""

import uuid
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_manager
from app.repositories import analytics_repository as analytics
from app.schemas.management import (
    CohortRow,
    CustomerDetailOut,
    CustomerListOut,
    CustomerRow,
    DayNRetention,
    EngagementOut,
    JourneyOut,
    Lifecycle,
    OverviewOut,
    PeriodInfo,
    RetentionOut,
    RevenueOut,
    TutorStats,
)

router = APIRouter(prefix="/management", tags=["management"], dependencies=[Depends(get_current_manager)])

# Los mismos cuatro rangos que ofrece el selector del panel. Cerrado a
# propósito: un ?days=3650 obligaría a recorrer toda la historia en cada
# consulta sin que nadie lo haya pedido desde la interfaz. (Se valida a
# mano y no con Literal[7, 30, ...]: Literal de enteros no convierte el
# "30" de la query string y rechaza hasta los valores válidos.)
ALLOWED_DAYS = (7, 30, 90, 365)


def _period(days: int) -> analytics.Period:
    if days not in ALLOWED_DAYS:
        raise HTTPException(status_code=422, detail=f"days debe ser uno de {ALLOWED_DAYS}.")
    return analytics.make_period(days)


Segment = Literal["new", "current", "at_risk", "dormant", "never_active"]


def _rate(numerator, denominator) -> float | None:
    return float(numerator) / float(denominator) if denominator else None


def _period_info(period: analytics.Period) -> PeriodInfo:
    return PeriodInfo(
        days=period.days, start=period.start, end=period.end,
        timezone=settings.analytics_timezone, bucket=period.bucket,
    )


def _lifecycle(raw: dict) -> Lifecycle:
    return Lifecycle(
        segments=raw["segments"] or {},
        last_week_active=raw["last_week_active"],
        retained_this_week=raw["retained_this_week"],
        curr=_rate(raw["retained_this_week"], raw["last_week_active"]),
    )


@router.get("/overview", response_model=OverviewOut)
async def overview(days: int = Query(30), db: AsyncSession = Depends(get_db)) -> OverviewOut:
    """Los números con los que abre el panel: base de clientes, uso,
    activación e ingresos, cada uno contra el periodo anterior."""
    period = _period(days)
    k = await analytics.overview_kpis(db, period)
    series = await analytics.time_series(db, period)
    mrr = int(k["mrr_cents"])
    return OverviewOut(
        period=_period_info(period),
        customers_total=k["customers_total"],
        new_customers=k["new_customers"],
        new_customers_prev=k["new_customers_prev"],
        active_customers=k["active_customers"],
        active_customers_prev=k["active_customers_prev"],
        dau=k["dau"],
        wau=k["wau"],
        mau=k["mau"],
        stickiness=_rate(k["avg_dau_30"], k["mau"]),
        activation_rate=_rate(k["activated_new"], k["new_customers"]),
        paying_customers=k["paying_customers"],
        mrr_cents=mrr,
        arppu_cents=round(mrr / k["paying_customers"]) if k["paying_customers"] else None,
        paid_conversion=_rate(k["ever_paid_customers"], k["customers_total"]),
        revenue_cents=int(k["revenue_cents"]),
        revenue_prev_cents=int(k["revenue_prev_cents"]),
        series=series,
    )


@router.get("/engagement", response_model=EngagementOut)
async def engagement(days: int = Query(30), db: AsyncSession = Depends(get_db)) -> EngagementOut:
    """Consumo: qué partes de la app se usan, cuánto se habla con el tutor,
    cuándo se estudia, en qué estado está la base y qué se falla más."""
    period = _period(days)
    tutor = await analytics.tutor_stats(db, period)
    return EngagementOut(
        period=_period_info(period),
        features=await analytics.feature_usage(db, period),
        tutor=TutorStats(
            sessions=tutor["sessions"],
            customers=tutor["customers"],
            learner_turns=int(tutor["learner_turns"]),
            avg_turns_per_session=tutor["avg_turns_per_session"],
            median_minutes=tutor["median_minutes"],
            correction_rate=_rate(tutor["corrected_turns"], tutor["learner_turns"]),
            library_sessions=tutor["library_sessions"],
            module_sessions=tutor["module_sessions"],
        ),
        heatmap=await analytics.activity_heatmap(db, period),
        lifecycle=_lifecycle(await analytics.lifecycle(db, period)),
        top_corrections=await analytics.top_corrections(db, period),
        screens=await analytics.screen_views(db, period),
    )


@router.get("/journey", response_model=JourneyOut)
async def journey(days: int = Query(90), db: AsyncSession = Depends(get_db)) -> JourneyOut:
    """Recorrido de la cohorte que se registró en el periodo, del alta al
    pago, más dónde se atascan en el currículo y qué resultados logran."""
    period = _period(days)
    f = await analytics.journey_funnel(db, period)
    return JourneyOut(
        period=_period_info(period),
        funnel=[
            {"key": key, "customers": f[key]}
            for key in ("registered", "activated", "engaged", "achieved", "paid")
        ],
        paid_any=f["paid_any"],
        median_hours_to_activate=f["median_hours_to_activate"],
        median_days_to_achieve=f["median_days_to_achieve"],
        median_days_to_pay=f["median_days_to_pay"],
        modules=await analytics.module_progression(db),
        outcomes=await analytics.learning_outcomes(db, period),
        levels=await analytics.level_distribution(db),
    )


@router.get("/retention", response_model=RetentionOut)
async def retention(weeks: int = Query(10, ge=4, le=26), db: AsyncSession = Depends(get_db)) -> RetentionOut:
    """Cohortes semanales (qué fracción de cada semana de altas sigue
    activa N semanas después), retención día 1/7/30 y CURR."""
    rows = await analytics.cohort_retention(db, weeks)
    now = analytics.local_now()
    current_week = (now - timedelta(days=now.weekday())).date()

    cohorts: dict = {}
    for r in rows:
        week = r["cohort_week"].date()
        entry = cohorts.setdefault(week, {"size": r["cohort_size"], "retained": {}})
        if r["week_offset"] is not None:
            entry["retained"][r["week_offset"]] = r["retained"]

    cohort_rows = []
    for week in sorted(cohorts):
        entry = cohorts[week]
        elapsed = (current_week - week).days // 7
        cohort_rows.append(CohortRow(
            week_start=week,
            size=entry["size"],
            retention=[
                (entry["retained"].get(k, 0) / entry["size"]) if k <= elapsed else None
                for k in range(weeks)
            ],
        ))

    day_n = [
        DayNRetention(day=r["day"], eligible=r["eligible"], retained=r["retained"], rate=_rate(r["retained"], r["eligible"]))
        for r in await analytics.day_n_retention(db)
    ]
    return RetentionOut(
        weeks=weeks,
        cohorts=cohort_rows,
        day_n=day_n,
        lifecycle=_lifecycle(await analytics.lifecycle(db, analytics.make_period(30))),
    )


@router.get("/revenue", response_model=RevenueOut)
async def revenue(days: int = Query(90), db: AsyncSession = Depends(get_db)) -> RevenueOut:
    """Ingresos: MRR, cobros por pasarela y estado, churn y LTV estimado."""
    period = _period(days)
    k = await analytics.overview_kpis(db, period)
    b = await analytics.revenue_breakdown(db, period)

    mrr = int(k["mrr_cents"])
    arppu = round(mrr / k["paying_customers"]) if k["paying_customers"] else None
    # Bajas / suscripciones que estuvieron vivas en algún momento del
    # periodo (las que había al empezar + las que nacieron en él).
    exposed = b["subscribers_at_start"] + b["new_subscribers"]
    churn_rate = _rate(b["churned_in_period"], exposed)
    # LTV = lo que deja un cliente de pago al mes / la fracción que se va
    # cada mes. El churn del periodo se pasa a mensual para que 7 y 365
    # días den LTVs comparables; sin churn medible no hay LTV que estimar.
    ltv = None
    if arppu and churn_rate:
        monthly_churn = 1 - (1 - min(churn_rate, 1.0)) ** (30 / days)
        ltv = round(arppu / monthly_churn) if monthly_churn > 0 else None

    return RevenueOut(
        period=_period_info(period),
        mrr_cents=mrr,
        paying_customers=k["paying_customers"],
        arppu_cents=arppu,
        revenue_cents=int(k["revenue_cents"]),
        revenue_prev_cents=int(k["revenue_prev_cents"]),
        paid_conversion=_rate(k["ever_paid_customers"], k["customers_total"]),
        series=await analytics.time_series(db, period),
        by_provider=b["by_provider"] or [],
        by_status=b["by_status"] or [],
        subscriptions_by_status=b["subscriptions_by_status"] or {},
        pending_verification=b["pending_verification"],
        pending_verification_cents=int(b["pending_verification_cents"]),
        subscribers_at_start=b["subscribers_at_start"],
        new_subscribers=b["new_subscribers"],
        churned_in_period=b["churned_in_period"],
        churn_rate=churn_rate,
        ltv_cents=ltv,
    )


@router.get("/customers", response_model=CustomerListOut)
async def customers(
    search: str | None = Query(None, max_length=100, description="Nombre o email, parcial"),
    segment: Segment | None = Query(None),
    sort: Literal["last_active", "signup", "messages", "paid", "name"] = Query("last_active"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> CustomerListOut:
    rows, total = await analytics.list_customers(
        db, search=search, segment=segment, sort=sort, limit=limit, offset=offset
    )
    return CustomerListOut(items=rows, total=total, as_of=analytics.local_now())


@router.get("/customers/{customer_id}", response_model=CustomerDetailOut)
async def customer_detail(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CustomerDetailOut:
    """Ficha de un cliente: sus cifras, sus hitos, su actividad diaria y lo
    último que hizo. Sin el contenido de sus conversaciones (ver
    analytics_repository.customer_timeline)."""
    row = await analytics.get_customer(db, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No existe ese cliente.")
    return CustomerDetailOut(
        as_of=analytics.local_now(),
        customer=CustomerRow(**row),
        milestones=await analytics.customer_milestones(db, customer_id),
        daily_activity=await analytics.customer_daily_activity(db, customer_id),
        timeline=await analytics.customer_timeline(db, customer_id),
        top_corrections=await analytics.customer_top_corrections(db, customer_id),
    )
