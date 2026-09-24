/** Tipos del panel de gerencia: espejo de backend/app/schemas/management.py.
 *
 * Importes en céntimos; tasas como fracción 0-1, o null cuando no hay
 * denominador (sin clientes no hay "0 %", hay "sin datos"). Fechas como
 * string ISO en hora local del negocio (period.timezone), sin zona. */

export type PeriodDays = 7 | 30 | 90 | 365

export interface PeriodInfo {
  days: number
  start: string
  end: string
  timezone: string
  bucket: "day" | "week"
}

export interface SeriesPoint {
  bucket: string
  signups: number
  active_customers: number
  revenue_cents: number
}

export interface Overview {
  period: PeriodInfo
  customers_total: number
  new_customers: number
  new_customers_prev: number
  active_customers: number
  active_customers_prev: number
  dau: number
  wau: number
  mau: number
  stickiness: number | null
  activation_rate: number | null
  paying_customers: number
  mrr_cents: number
  arppu_cents: number | null
  paid_conversion: number | null
  revenue_cents: number
  revenue_prev_cents: number
  series: SeriesPoint[]
}

export type Segment = "new" | "current" | "at_risk" | "dormant" | "never_active"

export interface Lifecycle {
  segments: Partial<Record<Segment, number>>
  last_week_active: number
  retained_this_week: number
  curr: number | null
}

export interface Engagement {
  period: PeriodInfo
  features: { feature: string; customers: number; volume: number }[]
  tutor: {
    sessions: number
    customers: number
    learner_turns: number
    avg_turns_per_session: number | null
    median_minutes: number | null
    correction_rate: number | null
    library_sessions: number
    module_sessions: number
  }
  heatmap: { weekday: number; hour: number; actions: number; customers: number }[]
  lifecycle: Lifecycle
  top_corrections: { rule: string; times: number; customers: number }[]
  screens: { path: string | null; views: number; customers: number }[]
}

export type FunnelKey = "registered" | "activated" | "engaged" | "achieved" | "paid"

export interface Journey {
  period: PeriodInfo
  funnel: { key: FunnelKey; customers: number }[]
  paid_any: number
  median_hours_to_activate: number | null
  median_days_to_achieve: number | null
  median_days_to_pay: number | null
  modules: { code: string | null; title: string; level_code: string; started: number; completed: number }[]
  outcomes: {
    exams_taken: number
    exams_passed: number
    modules_completed: number
    levels_certified: number
    tutor_tasks: number
    tutor_tasks_completed: number
  }
  levels: { level_code: string; customers: number }[]
}

export interface Retention {
  weeks: number
  cohorts: { week_start: string; size: number; retention: (number | null)[] }[]
  day_n: { day: number; eligible: number; retained: number; rate: number | null }[]
  lifecycle: Lifecycle
}

export interface Revenue {
  period: PeriodInfo
  mrr_cents: number
  paying_customers: number
  arppu_cents: number | null
  revenue_cents: number
  revenue_prev_cents: number
  paid_conversion: number | null
  series: SeriesPoint[]
  by_provider: { provider: string; payments: number; amount_cents: number }[]
  by_status: { status: string; payments: number; amount_cents: number }[]
  subscriptions_by_status: Record<string, number>
  pending_verification: number
  pending_verification_cents: number
  subscribers_at_start: number
  new_subscribers: number
  churned_in_period: number
  churn_rate: number | null
  ltv_cents: number | null
}

export interface CustomerRow {
  id: string
  full_name: string
  email: string
  created_at: string
  level_code: string | null
  last_active_at: string | null
  active_days_30: number
  tutor_messages: number
  modules_completed: number
  subscription_status: string
  subscription_period_end: string | null
  total_paid_cents: number
  segment: Segment
}

export type CustomerSort = "last_active" | "signup" | "messages" | "paid" | "name"

export interface CustomerList {
  items: CustomerRow[]
  total: number
  /** "Ahora" en hora del negocio, referencia para los "hace N días". */
  as_of: string
}

export interface CustomerDetail {
  as_of: string
  customer: CustomerRow
  milestones: {
    first_learning_at: string | null
    first_tutor_at: string | null
    first_module_completed_at: string | null
    first_level_certified_at: string | null
    first_payment_at: string | null
    tutor_sessions: number
    exam_answers: number
    modules_in_progress: number
    active_days_total: number
  }
  daily_activity: { day: string; actions: number }[]
  timeline: { at: string; kind: string; detail: Record<string, unknown> }[]
  top_corrections: { rule: string; times: number }[]
}

// --- Pagos (revisión manual) -------------------------------------------------

export type PaymentStatus = "pending_verification" | "approved" | "rejected" | "failed" | "refunded"

export interface PaymentReviewRow {
  id: string
  provider: "pago_movil" | "binance_pay" | "credit_card" | "paypal"
  status: PaymentStatus
  amount_cents: number
  currency: string
  external_reference: string | null
  /** Lo que declaró el alumno y lo que se le pidió. Pago Móvil:
   * reference_number, payer_bank/cedula/phone, amount_bs, expected_amount_bs,
   * bs_per_usd, rate_value_date. Binance: order_id, payer_account,
   * expected_amount, asset. Rechazado: rejection_reason. */
  payload: Record<string, string | number | null | undefined>
  created_at: string
  reviewed_at: string | null
  reviewer_name: string | null
  customer: { id: string; full_name: string; email: string }
  access_until: string | null
}

export interface PaymentReviewList {
  items: PaymentReviewRow[]
  total: number
  as_of: string
}

export interface PaymentReviewSummary {
  pending: number
  pending_by_provider: Record<string, number>
  oldest_pending_at: string | null
  approved_today: number
  approved_today_cents: number
}

// --- Correos ---------------------------------------------------------------

export type EmailStatus = "sent" | "failed" | "skipped" | "sending"

export interface EmailMessageRow {
  id: string
  /** "bienvenida", "pago_aprobado", "vence_pronto", "campana"... */
  kind: string
  status: EmailStatus
  to_email: string
  subject: string
  error: string | null
  created_at: string
  customer: { id: string; full_name: string; email: string } | null
}

export interface EmailMessageList {
  items: EmailMessageRow[]
  total: number
  as_of: string
}

export interface EmailSummary {
  days: number
  sent: number
  failed: number
  skipped: number
  failure_rate: number | null
  by_kind: { kind: string; sent: number; failed: number; skipped: number }[]
  last_sent_at: string | null
  /** Por qué no está saliendo ningún correo (falta la clave, modo de
   * pruebas). null = todo normal. */
  blocked_reason: string | null
}

/** Los campos que se escriben en el editor. El HTML no se guarda: se arma
 * al enviar con la plantilla de la marca. */
export interface TemplateDraft {
  name: string
  subject: string
  preheader: string
  eyebrow: string
  title: string
  body: string
  button_label: string | null
  button_url: string | null
}

export interface EmailTemplate extends TemplateDraft {
  id: string
  created_at: string
  updated_at: string
  author_name: string | null
  times_sent: number
  last_sent_at: string | null
}

export interface TemplatePreview {
  subject: string
  html: string
  text: string
}

export interface Audience {
  key: string
  label: string
  description: string
  customers: number
}

export interface Campaign {
  id: string
  name: string
  subject: string
  audience: string
  audience_label: string
  status: "enviando" | "terminada"
  recipients: number
  sent: number
  skipped: number
  failed: number
  sender_name: string | null
  created_at: string
  finished_at: string | null
}
