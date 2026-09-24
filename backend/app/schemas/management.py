"""Respuestas del panel de gerencia (routers/management.py).

Importes en céntimos (int) como en el resto de la facturación; tasas como
fracción 0-1 (float) o None cuando el denominador es cero — un "0 %" sobre
cero clientes afirmaría algo que no se ha medido.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PeriodInfo(BaseModel):
    days: int
    start: datetime
    end: datetime
    timezone: str
    bucket: str  # "day" | "week": granularidad de las series


class SeriesPoint(BaseModel):
    bucket: datetime
    signups: int
    active_customers: int
    revenue_cents: int


class OverviewOut(BaseModel):
    period: PeriodInfo
    customers_total: int
    new_customers: int
    new_customers_prev: int
    active_customers: int
    active_customers_prev: int
    dau: int
    wau: int
    mau: int
    # DAU medio de 30 días / MAU: qué fracción del mes vuelve cada día.
    stickiness: float | None
    # Altas del periodo que practicaron en sus primeros 7 días.
    activation_rate: float | None
    paying_customers: int
    mrr_cents: int
    arppu_cents: int | None
    # Clientes que han pagado alguna vez / clientes totales.
    paid_conversion: float | None
    revenue_cents: int
    revenue_prev_cents: int
    series: list[SeriesPoint]


class FeatureUsage(BaseModel):
    feature: str
    customers: int
    volume: int


class TutorStats(BaseModel):
    sessions: int
    customers: int
    learner_turns: int
    avg_turns_per_session: float | None
    median_minutes: float | None
    # Turnos del alumno en los que el tutor corrigió algo.
    correction_rate: float | None
    library_sessions: int
    module_sessions: int


class HeatCell(BaseModel):
    weekday: int  # 1 = lunes … 7 = domingo
    hour: int  # 0-23, hora local
    actions: int
    customers: int


class Lifecycle(BaseModel):
    segments: dict[str, int]
    last_week_active: int
    retained_this_week: int
    curr: float | None


class CorrectionRule(BaseModel):
    rule: str
    times: int
    customers: int


class ScreenViews(BaseModel):
    path: str | None
    views: int
    customers: int


class EngagementOut(BaseModel):
    period: PeriodInfo
    features: list[FeatureUsage]
    tutor: TutorStats
    heatmap: list[HeatCell]
    lifecycle: Lifecycle
    top_corrections: list[CorrectionRule]
    screens: list[ScreenViews]


class FunnelStage(BaseModel):
    key: str
    customers: int


class ModuleProgress(BaseModel):
    code: str | None
    title: str
    level_code: str
    started: int
    completed: int


class LearningOutcomes(BaseModel):
    exams_taken: int
    exams_passed: int
    modules_completed: int
    levels_certified: int
    tutor_tasks: int
    tutor_tasks_completed: int


class LevelCount(BaseModel):
    level_code: str
    customers: int


class JourneyOut(BaseModel):
    period: PeriodInfo
    funnel: list[FunnelStage]
    paid_any: int
    median_hours_to_activate: float | None
    median_days_to_achieve: float | None
    median_days_to_pay: float | None
    modules: list[ModuleProgress]
    outcomes: LearningOutcomes
    levels: list[LevelCount]


class CohortRow(BaseModel):
    week_start: date
    size: int
    # Índice = semanas desde el alta. None = esa semana todavía no ha pasado.
    retention: list[float | None]


class DayNRetention(BaseModel):
    day: int
    eligible: int
    retained: int
    rate: float | None


class RetentionOut(BaseModel):
    weeks: int
    cohorts: list[CohortRow]
    day_n: list[DayNRetention]
    lifecycle: Lifecycle


class ProviderRevenue(BaseModel):
    provider: str
    payments: int
    amount_cents: int


class PaymentStatusCount(BaseModel):
    status: str
    payments: int
    amount_cents: int


class RevenueOut(BaseModel):
    period: PeriodInfo
    mrr_cents: int
    paying_customers: int
    arppu_cents: int | None
    revenue_cents: int
    revenue_prev_cents: int
    paid_conversion: float | None
    series: list[SeriesPoint]
    by_provider: list[ProviderRevenue]
    by_status: list[PaymentStatusCount]
    subscriptions_by_status: dict[str, int]
    pending_verification: int
    pending_verification_cents: int
    subscribers_at_start: int
    new_subscribers: int
    churned_in_period: int
    churn_rate: float | None
    # Estimación: ARPPU / churn mensual. None si no hay churn medible.
    ltv_cents: int | None


class CustomerRow(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    created_at: datetime
    level_code: str | None
    last_active_at: datetime | None
    active_days_30: int
    tutor_messages: int
    modules_completed: int
    subscription_status: str
    subscription_period_end: datetime | None
    total_paid_cents: int
    segment: str


class CustomerListOut(BaseModel):
    items: list[CustomerRow]
    total: int
    # "Ahora" en hora del negocio: para que el frontend calcule "hace 3
    # días" contra la misma referencia que las fechas, no contra la zona
    # horaria del navegador de quien mira.
    as_of: datetime


class CustomerMilestones(BaseModel):
    first_learning_at: datetime | None
    first_tutor_at: datetime | None
    first_module_completed_at: datetime | None
    first_level_certified_at: datetime | None
    first_payment_at: datetime | None
    tutor_sessions: int
    exam_answers: int
    modules_in_progress: int
    active_days_total: int


class DailyActivity(BaseModel):
    day: date
    actions: int


class TimelineItem(BaseModel):
    at: datetime
    kind: str
    detail: dict


class CustomerRuleCount(BaseModel):
    rule: str
    times: int


class CustomerDetailOut(BaseModel):
    as_of: datetime
    customer: CustomerRow
    milestones: CustomerMilestones
    daily_activity: list[DailyActivity]
    timeline: list[TimelineItem]
    top_corrections: list[CustomerRuleCount]


# --- Pagos (revisión manual desde el panel de gerencia) ---------------------


class PaymentCustomer(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str


class PaymentReviewRow(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    amount_cents: int
    currency: str
    external_reference: str | None
    # Lo que declaró el alumno y lo que se le pidió: referencia, banco,
    # cédula, monto en Bs esperado y declarado, ID de orden de Binance...
    payload: dict
    created_at: datetime
    reviewed_at: datetime | None
    reviewer_name: str | None
    customer: PaymentCustomer
    # Hasta cuándo da acceso, si se aprobó.
    access_until: datetime | None


class PaymentReviewList(BaseModel):
    items: list[PaymentReviewRow]
    total: int
    as_of: datetime  # "ahora" en hora del negocio, para los "hace 2 h"


class PaymentReviewSummary(BaseModel):
    pending: int
    pending_by_provider: dict[str, int]
    oldest_pending_at: datetime | None
    approved_today: int
    approved_today_cents: int


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


# --- Correos (registro de envíos, plantillas y campañas) --------------------


class EmailMessageRow(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    to_email: str
    subject: str
    error: str | None
    created_at: datetime
    customer: PaymentCustomer | None


class EmailMessageList(BaseModel):
    items: list[EmailMessageRow]
    total: int
    as_of: datetime


class EmailKindCount(BaseModel):
    kind: str
    sent: int
    failed: int
    skipped: int


class EmailSummary(BaseModel):
    days: int
    sent: int
    failed: int
    skipped: int
    # Correos que no salieron por un fallo / los que se intentaron. None
    # si no se intentó ninguno: un "0 %" sobre cero envíos no dice nada.
    failure_rate: float | None
    by_kind: list[EmailKindCount]
    last_sent_at: datetime | None
    # Si hace falta configurar algo para que salgan correos, se dice aquí
    # y la pantalla lo avisa arriba en vez de mentir con ceros.
    blocked_reason: str | None


class TemplateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    subject: str = Field(min_length=2, max_length=200)
    preheader: str = Field(default="", max_length=200)
    eyebrow: str = Field(default="Espikin", max_length=40)
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=2, max_length=4000)
    button_label: str | None = Field(default=None, max_length=60)
    button_url: str | None = Field(default=None, max_length=500)


class TemplateOut(TemplateIn):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    author_name: str | None
    # Cuántas veces se ha enviado y cuándo fue la última.
    times_sent: int
    last_sent_at: datetime | None


class TemplatePreviewOut(BaseModel):
    subject: str
    html: str
    text: str


class AudienceOut(BaseModel):
    key: str
    label: str
    description: str
    customers: int


class CampaignIn(BaseModel):
    template_id: uuid.UUID
    audience: str


class CampaignOut(BaseModel):
    id: uuid.UUID
    name: str
    subject: str
    audience: str
    audience_label: str
    status: str
    recipients: int
    sent: int
    skipped: int
    failed: int
    sender_name: str | None
    created_at: datetime
    finished_at: datetime | None
