import {
  faArrowLeft,
  faAward,
  faCircleCheck,
  faComments,
  faCreditCard,
  faFlagCheckered,
  faGraduationCap,
  faUserPlus,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"
import { Link, useLocation, useParams } from "react-router-dom"
import type { CustomerDetail } from "../../api/management"
import Avatar from "../../components/Avatar"
import BarList from "../../components/charts/BarList"
import ChartCard from "../../components/charts/ChartCard"
import Heatmap from "../../components/charts/Heatmap"
import StatTile from "../../components/charts/StatTile"
import { dateAndTime, int, longDate, money, parseLocal, relativeDays, shortDate } from "../../components/charts/format"
import { PROVIDER_LABELS, SUBSCRIPTION_LABELS, TIMELINE_LABELS, WEEKDAYS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import SegmentBadge from "../../components/management/SegmentBadge"
import { useManagementData } from "../../components/management/useManagementData"

const CALENDAR_WEEKS = 13
const TIMELINE_PREVIEW = 12

// Estado de UN pago (en la lista de estados del panel de ingresos van en plural).
const PAYMENT_STATUS_ONE: Record<string, string> = {
  approved: "aprobado",
  pending_verification: "por verificar",
  rejected: "rechazado",
  failed: "fallido",
  refunded: "reembolsado",
}

export default function CustomerDetailPage() {
  const { customerId } = useParams()
  const { state } = useLocation()
  const { data, loading, error } = useManagementData<CustomerDetail>(`/management/customers/${customerId}`)

  return (
    <div className="space-y-4">
      <Link
        to={(state as { from?: string } | null)?.from ?? "/gerencia/clientes"}
        className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-900"
      >
        <FontAwesomeIcon icon={faArrowLeft} className="text-xs" />
        Clientes
      </Link>
      <PageShell
        title={data?.customer.full_name ?? "Cliente"}
        question={data ? data.customer.email : "Cargando ficha…"}
        loading={loading}
        error={error}
        hasData={data != null}
      >
        {data && <CustomerBody data={data} />}
      </PageShell>
    </div>
  )
}

function CustomerBody({ data }: { data: CustomerDetail }) {
  const c = data.customer
  const m = data.milestones
  const signup = parseLocal(c.created_at)
  const dayFromSignup = (iso: string | null) =>
    iso ? Math.max(0, Math.floor((parseLocal(iso).getTime() - signup.getTime()) / 86_400_000)) : null

  const steps: { icon: IconDefinition; label: string; at: string | null }[] = [
    { icon: faUserPlus, label: "Se registró", at: c.created_at },
    { icon: faFlagCheckered, label: "Primera práctica", at: m.first_learning_at },
    { icon: faComments, label: "Primera conversación con el tutor", at: m.first_tutor_at },
    { icon: faCircleCheck, label: "Primer módulo completado", at: m.first_module_completed_at },
    { icon: faAward, label: "Primer nivel certificado", at: m.first_level_certified_at },
    { icon: faCreditCard, label: "Primer pago", at: m.first_payment_at },
  ]

  const calendar = buildCalendar(data.daily_activity, data.as_of)
  const [showAll, setShowAll] = useState(false)
  const timeline = showAll ? data.timeline : data.timeline.slice(0, TIMELINE_PREVIEW)

  return (
    <>
      <section className="flex flex-wrap items-center gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <Avatar name={c.full_name} avatarUrl={null} size={52} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SegmentBadge segment={c.segment} />
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
              Nivel {c.level_code ?? "sin asignar"}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
              {SUBSCRIPTION_LABELS[c.subscription_status] ?? c.subscription_status}
              {c.subscription_period_end && c.subscription_status === "active" && ` · vence el ${longDate(c.subscription_period_end)}`}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-500">
            Cliente desde el {longDate(c.created_at)} · última actividad: {relativeDays(c.last_active_at, data.as_of).toLowerCase()}
          </p>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-3 2xl:grid-cols-6">
        <StatTile label="Días activos" value={int(m.active_days_total)} hint={`${int(c.active_days_30)} en los últimos 30`} />
        <StatTile label="Sesiones con el tutor" value={int(m.tutor_sessions)} />
        <StatTile label="Mensajes al tutor" value={int(c.tutor_messages)} />
        <StatTile label="Módulos completados" value={int(c.modules_completed)} hint={`${int(m.modules_in_progress)} en curso`} />
        <StatTile label="Respuestas de examen" value={int(m.exam_answers)} />
        <StatTile label="Pagado en total" value={money(c.total_paid_cents)} />
      </section>

      <section className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h3 className="text-base font-bold text-slate-900">Su recorrido</h3>
          <p className="mt-1 text-sm text-slate-500">Los hitos del journey y cuántos días tardó en alcanzar cada uno.</p>
          <ol className="mt-5 space-y-0">
            {steps.map((s, i) => {
              const reached = s.at != null
              const day = dayFromSignup(s.at)
              return (
                <li key={s.label} className="relative flex gap-3 pb-5 last:pb-0">
                  {i < steps.length - 1 && (
                    <span aria-hidden className={`absolute left-4 top-8 h-[calc(100%-2rem)] w-px ${reached ? "bg-brand-200" : "bg-slate-200"}`} />
                  )}
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs ${
                      reached ? "bg-brand-600 text-white" : "border border-dashed border-slate-300 text-slate-300"
                    }`}
                  >
                    <FontAwesomeIcon icon={s.icon} />
                  </span>
                  <div className="min-w-0 pt-1">
                    <p className={`text-sm font-semibold ${reached ? "text-slate-900" : "text-slate-400"}`}>{s.label}</p>
                    <p className="text-xs text-slate-500">
                      {reached ? (
                        <>
                          {longDate(s.at)}
                          {i > 0 && day != null && <span className="text-slate-400"> · {day === 0 ? "el mismo día" : `día ${day}`}</span>}
                        </>
                      ) : (
                        "Todavía no"
                      )}
                    </p>
                  </div>
                </li>
              )
            })}
          </ol>
        </div>

        <ChartCard
          className="xl:col-span-2"
          title="Actividad de las últimas 13 semanas"
          description="Acciones de práctica por día. Un hueco largo antes de irse suele ser la señal más temprana de abandono."
          table={{
            columns: ["Día", "Acciones"],
            numeric: [1],
            rows: data.daily_activity.map((d) => [longDate(d.day), int(d.actions)]),
          }}
        >
          <Heatmap
            rows={WEEKDAYS.map((d) => ({ key: d, label: d.slice(0, 3) }))}
            columns={calendar.weeks.map((w, i) => ({ key: w, label: shortDate(w), showLabel: i % 3 === 0 }))}
            values={calendar.values}
            scale={(v) => (v === 0 ? 0 : 0.2 + 0.8 * (v / calendar.max))}
            formatValue={int}
            describe={(r, col, v) => `${longDate(calendar.dates[r][col] ?? "")}: ${int(v)} acciones`}
            legend={["Sin actividad", "Mucha"]}
            minCell={16}
          />
        </ChartCard>
      </section>

      <section className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
        <ChartCard
          title="Lo que más le corrige el tutor"
          description="Solo la regla y las veces: nunca el texto de sus conversaciones."
          table={{ columns: ["Regla", "Veces"], numeric: [1], rows: data.top_corrections.map((r) => [r.rule, int(r.times)]) }}
        >
          <BarList
            items={data.top_corrections.map((r) => ({ key: r.rule, label: r.rule, value: r.times, display: int(r.times) }))}
            emptyText="El tutor todavía no le ha corregido nada."
          />
        </ChartCard>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 xl:col-span-2">
          <h3 className="text-base font-bold text-slate-900">Actividad reciente</h3>
          <p className="mt-1 text-sm text-slate-500">Lo último que hizo, del más reciente al más antiguo.</p>
          <ul className="mt-4 divide-y divide-slate-100">
            {timeline.map((item, i) => (
              <li key={`${item.at}-${i}`} className="flex items-start justify-between gap-4 py-3">
                <div className="flex min-w-0 items-start gap-3">
                  <FontAwesomeIcon icon={timelineIcon(item.kind)} className="mt-1 w-4 shrink-0 text-slate-400" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800">{TIMELINE_LABELS[item.kind] ?? item.kind}</p>
                    <p className="text-xs text-slate-500">{describeTimeline(item)}</p>
                  </div>
                </div>
                <time className="shrink-0 text-xs text-slate-400">{dateAndTime(item.at)}</time>
              </li>
            ))}
            {data.timeline.length === 0 && <li className="py-8 text-center text-sm text-slate-400">Sin actividad todavía.</li>}
          </ul>
          {data.timeline.length > TIMELINE_PREVIEW && (
            <button
              type="button"
              onClick={() => setShowAll((v) => !v)}
              className="mt-2 w-full rounded-full border border-slate-200 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {showAll ? "Ver menos" : `Ver las ${data.timeline.length} más recientes`}
            </button>
          )}
        </div>
      </section>
    </>
  )
}

function timelineIcon(kind: string): IconDefinition {
  if (kind === "tutor_session") return faComments
  if (kind === "payment" || kind === "subscription_canceled") return faCreditCard
  if (kind === "level_certified") return faAward
  if (kind === "module_completed") return faCircleCheck
  return faGraduationCap
}

function describeTimeline(item: CustomerDetail["timeline"][number]): string {
  const d = item.detail
  if (item.kind === "tutor_session") {
    const where = d.library ? "en la biblioteca" : d.module ? "practicando un módulo" : "conversación libre"
    return `${int(Number(d.turns ?? 0))} mensajes · ${where}`
  }
  if (item.kind === "payment") {
    const status = PAYMENT_STATUS_ONE[String(d.status)] ?? String(d.status)
    return `${money(Number(d.amount_cents ?? 0))} por ${PROVIDER_LABELS[String(d.provider)] ?? d.provider} · ${status}`
  }
  if (item.kind === "module_exam_submitted") {
    const score = typeof d.score === "number" ? ` · nota ${Math.round(d.score * 100)} %` : ""
    return `${d.passed ? "Aprobado" : "No aprobado"}${score}`
  }
  if (item.kind === "level_certified") return `Nivel ${String(d.level_code ?? "")}`
  if (item.kind === "subscription_canceled") return `Pagaba por ${PROVIDER_LABELS[String(d.provider)] ?? d.provider}`
  return ""
}

/** Calendario tipo GitHub: filas = día de la semana, columnas = semanas,
 * terminando en la semana de `as_of`. Los días futuros quedan en blanco. */
function buildCalendar(daily: CustomerDetail["daily_activity"], asOf: string) {
  const byDay = new Map(daily.map((d) => [d.day, d.actions]))
  const today = parseLocal(asOf)
  today.setHours(0, 0, 0, 0)
  const mondayThisWeek = new Date(today)
  mondayThisWeek.setDate(today.getDate() - ((today.getDay() + 6) % 7))
  const firstMonday = new Date(mondayThisWeek)
  firstMonday.setDate(mondayThisWeek.getDate() - (CALENDAR_WEEKS - 1) * 7)

  const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
  const weeks: string[] = []
  const values: (number | null)[][] = Array.from({ length: 7 }, () => [])
  const dates: (string | null)[][] = Array.from({ length: 7 }, () => [])

  for (let w = 0; w < CALENDAR_WEEKS; w++) {
    const monday = new Date(firstMonday)
    monday.setDate(firstMonday.getDate() + w * 7)
    weeks.push(iso(monday))
    for (let d = 0; d < 7; d++) {
      const day = new Date(monday)
      day.setDate(monday.getDate() + d)
      const key = iso(day)
      const future = day > today
      values[d].push(future ? null : byDay.get(key) ?? 0)
      dates[d].push(future ? null : key)
    }
  }
  const max = Math.max(1, ...values.flat().map((v) => v ?? 0))
  return { weeks, values, dates, max }
}
