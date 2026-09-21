import {
  faCheck,
  faChevronLeft,
  faChevronRight,
  faCircleCheck,
  faClock,
  faMagnifyingGlass,
  faSpinner,
  faTriangleExclamation,
  faXmark,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { api } from "../../api/client"
import type { PaymentReviewList, PaymentReviewRow, PaymentReviewSummary } from "../../api/management"
import { ApiError } from "../../api/types"
import CopyField from "../../components/billing/CopyField"
import StatTile from "../../components/charts/StatTile"
import { dateAndTime, int, longDate, money, parseLocal } from "../../components/charts/format"
import { PAYMENT_STATUS_ONE, PROVIDER_LABELS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import { PAYMENTS_CHANGED } from "../../components/management/events"
import { useManagementData } from "../../components/management/useManagementData"

const PAGE_SIZE = 25

const VIEWS = [
  { value: "pending_verification", label: "Por verificar" },
  { value: "approved", label: "Aprobados" },
  { value: "rejected", label: "Rechazados" },
  { value: "all", label: "Todos" },
] as const

const PROVIDERS = [
  { value: "", label: "Todos los métodos" },
  { value: "pago_movil", label: "Pago Móvil" },
  { value: "binance_pay", label: "Binance Pay" },
  { value: "credit_card", label: "Tarjeta" },
  { value: "paypal", label: "PayPal" },
]

const REJECT_REASONS = [
  "No aparece en el estado de cuenta",
  "El monto no coincide",
  "Referencia u orden inválida o repetida",
]

export default function PaymentsPage() {
  const [params, setParams] = useSearchParams()
  const view = (params.get("vista") as (typeof VIEWS)[number]["value"] | null) ?? "pending_verification"
  const provider = params.get("metodo") ?? ""
  const q = params.get("q") ?? ""
  const page = Math.max(1, Number(params.get("pagina")) || 1)
  const [draft, setDraft] = useState(q)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => setDraft(q), [q])
  useEffect(() => {
    const t = setTimeout(() => {
      if (draft !== q) update({ q: draft || null, pagina: null })
    }, 300)
    return () => clearTimeout(t)
  }, [draft])

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v == null || v === "") next.delete(k)
      else next.set(k, v)
    }
    setParams(next, { replace: true })
  }

  const query = new URLSearchParams({ status: view, limit: String(PAGE_SIZE), offset: String((page - 1) * PAGE_SIZE) })
  if (provider) query.set("provider", provider)
  if (q) query.set("search", q)
  // La cola se refresca sola cada minuto: los pagos entran mientras se revisa.
  const list = useManagementData<PaymentReviewList>(`/management/payments?${query}`, { refreshMs: 60_000 })
  const summary = useManagementData<PaymentReviewSummary>("/management/payments/summary", { refreshMs: 60_000 })
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / PAGE_SIZE)) : 1

  function onReviewed(message: string) {
    setNotice(message)
    list.reload()
    summary.reload()
    window.dispatchEvent(new Event(PAYMENTS_CHANGED))
    setTimeout(() => setNotice(null), 4000)
  }

  return (
    <PageShell
      title="Pagos"
      question="Verifica los pagos de Pago Móvil y Binance, y consulta el registro de todos los cobros."
      loading={list.loading}
      error={list.error}
      hasData={list.data != null}
      filters={
        <>
          <label className="relative block w-full sm:w-72">
            <span className="sr-only">Buscar por cliente, email, referencia u orden</span>
            <FontAwesomeIcon icon={faMagnifyingGlass} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-xs text-slate-400" />
            <input
              type="search"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Cliente, email, referencia u orden"
              className="w-full rounded-full border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none transition focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="block">
            <span className="sr-only">Método de pago</span>
            <select
              value={provider}
              onChange={(e) => update({ metodo: e.target.value || null, pagina: null })}
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 outline-none focus:border-brand-300"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </>
      }
    >
      {summary.data && (
        <section className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <StatTile
            emphasis={summary.data.pending > 0}
            label="Por verificar"
            value={int(summary.data.pending)}
            hint={
              summary.data.pending
                ? Object.entries(summary.data.pending_by_provider)
                    .map(([p, n]) => `${n} ${PROVIDER_LABELS[p] ?? p}`)
                    .join(" · ")
                : "Nada pendiente"
            }
          />
          <StatTile
            label="Esperando desde"
            value={summary.data.oldest_pending_at && list.data ? waitingFor(summary.data.oldest_pending_at, list.data.as_of) : "—"}
            hint={summary.data.oldest_pending_at ? `El más antiguo: ${dateAndTime(summary.data.oldest_pending_at)}` : undefined}
          />
          <StatTile label="Aprobados hoy" value={int(summary.data.approved_today)} />
          <StatTile label="Cobrado hoy (aprobado)" value={money(summary.data.approved_today_cents)} />
        </section>
      )}

      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Estado del pago">
        {VIEWS.map((v) => {
          const selected = v.value === view
          const count = v.value === "pending_verification" ? summary.data?.pending : undefined
          return (
            <button
              key={v.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => update({ vista: v.value === "pending_verification" ? null : v.value, pagina: null })}
              className={`flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm font-semibold transition ${
                selected ? "border-ink-900 bg-ink-900 text-white" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {v.label}
              {count ? <span className={`rounded-full px-1.5 text-xs ${selected ? "bg-white/20" : "bg-amber-100 text-amber-800"}`}>{count}</span> : null}
            </button>
          )
        })}
      </div>

      {notice && (
        <p role="status" className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
          <FontAwesomeIcon icon={faCircleCheck} />
          {notice}
        </p>
      )}

      {list.data && (
        <>
          {list.data.items.length === 0 ? (
            <div className="rounded-3xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
              <FontAwesomeIcon icon={faCircleCheck} className="text-3xl text-emerald-500" />
              <p className="mt-3 font-semibold text-slate-800">
                {view === "pending_verification" && !q && !provider ? "No hay pagos por verificar" : "Ningún pago coincide con estos filtros"}
              </p>
              {view === "pending_verification" && !q && !provider && <p className="mt-1 text-sm text-slate-500">Los nuevos aparecerán aquí solos.</p>}
            </div>
          ) : view === "pending_verification" ? (
            <ul className="grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
              {list.data.items.map((p) => (
                <li key={p.id}>
                  <PendingCard payment={p} asOf={list.data!.as_of} onReviewed={onReviewed} />
                </li>
              ))}
            </ul>
          ) : (
            <History items={list.data.items} />
          )}

          {list.data.total > PAGE_SIZE && (
            <div className="flex items-center justify-between gap-3 text-sm text-slate-500">
              <span>
                {int(list.data.total)} pagos · página {page} de {pages}
              </span>
              <div className="flex gap-2">
                <PageButton disabled={page <= 1} onClick={() => update({ pagina: String(page - 1) })} label="Página anterior" icon={faChevronLeft} />
                <PageButton disabled={page >= pages} onClick={() => update({ pagina: String(page + 1) })} label="Página siguiente" icon={faChevronRight} />
              </div>
            </div>
          )}
        </>
      )}
    </PageShell>
  )
}

// ---------------------------------------------------------------------------
// Tarjeta de un pago por verificar
// ---------------------------------------------------------------------------

function PendingCard({ payment: p, asOf, onReviewed }: { payment: PaymentReviewRow; asOf: string; onReviewed: (msg: string) => void }) {
  const [mode, setMode] = useState<"idle" | "approve" | "reject">("idle")
  const [reason, setReason] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isBinance = p.provider === "binance_pay"

  async function act(action: "approve" | "reject") {
    setBusy(true)
    setError(null)
    try {
      if (action === "approve") {
        const r = await api.post<PaymentReviewRow>(`/management/payments/${p.id}/approve`)
        onReviewed(`Pago de ${p.customer.full_name} aprobado: tiene acceso hasta el ${r.access_until ? longDate(r.access_until) : "—"}.`)
      } else {
        await api.post(`/management/payments/${p.id}/reject`, { reason: reason.trim() })
        onReviewed(`Pago de ${p.customer.full_name} rechazado.`)
      }
    } catch (err) {
      // 409 = alguien lo revisó a la vez: se recarga la cola para quitarlo.
      if (err instanceof ApiError && err.status === 409) onReviewed("Ese pago ya lo había revisado otra persona.")
      else setError(err instanceof ApiError ? err.message : "No se pudo completar la acción.")
      setBusy(false)
    }
  }

  return (
    <article className="flex h-full flex-col rounded-3xl border border-amber-200 bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-bold text-slate-900">{p.customer.full_name}</p>
          <p className="truncate text-sm text-slate-500">{p.customer.email}</p>
        </div>
        <div className="text-right">
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">{PROVIDER_LABELS[p.provider] ?? p.provider}</span>
          <p className="mt-1.5 flex items-center justify-end gap-1.5 text-xs text-slate-500">
            <FontAwesomeIcon icon={faClock} className="text-[10px]" />
            Declarado {waitingFor(p.created_at, asOf).toLowerCase()}
          </p>
        </div>
      </header>

      <div className="mt-4 flex-1 space-y-2">{isBinance ? <BinanceDetails p={p} /> : <PagoMovilDetails p={p} />}</div>

      <p className="mt-3 text-xs text-slate-500">
        {isBinance
          ? "Busca el ID de la orden en Binance: Pay → Historial. Aprueba solo si aparece y el monto coincide."
          : "Busca la referencia en el estado de cuenta del banco. Aprueba solo si aparece y el monto coincide."}
      </p>

      {error && <p className="mt-3 text-sm text-rose-700">{error}</p>}

      {mode === "idle" && (
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={() => setMode("approve")}
            className="flex flex-1 items-center justify-center gap-2 rounded-full bg-emerald-600 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500"
          >
            <FontAwesomeIcon icon={faCheck} /> Aprobar
          </button>
          <button
            type="button"
            onClick={() => setMode("reject")}
            className="flex flex-1 items-center justify-center gap-2 rounded-full border border-slate-200 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
          >
            <FontAwesomeIcon icon={faXmark} /> Rechazar
          </button>
        </div>
      )}

      {/* Confirmación en el sitio, no un diálogo: aprobar da acceso de pago y
          no se puede deshacer desde aquí, así que se pide un segundo clic. */}
      {mode === "approve" && (
        <div className="mt-4 rounded-2xl bg-emerald-50 p-4">
          <p className="text-sm font-semibold text-emerald-900">¿Encontraste este pago y el monto coincide?</p>
          <p className="mt-0.5 text-xs text-emerald-800">Se le activa el acceso Premium por 30 días (o se suman a los que le queden).</p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => act("approve")}
              className="flex flex-1 items-center justify-center gap-2 rounded-full bg-emerald-600 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-60"
            >
              {busy ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faCheck} />} Sí, aprobar
            </button>
            <button type="button" disabled={busy} onClick={() => setMode("idle")} className="rounded-full px-4 text-sm font-semibold text-slate-600 hover:bg-white">
              Cancelar
            </button>
          </div>
        </div>
      )}

      {mode === "reject" && (
        <div className="mt-4 rounded-2xl bg-rose-50 p-4">
          <p className="text-sm font-semibold text-rose-900">¿Por qué se rechaza?</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {REJECT_REASONS.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setReason(r)}
                className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${reason === r ? "border-rose-400 bg-white text-rose-800" : "border-rose-200 text-rose-700 hover:bg-white"}`}
              >
                {r}
              </button>
            ))}
          </div>
          <label className="mt-2 block">
            <span className="sr-only">Motivo del rechazo</span>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="O escribe el motivo"
              maxLength={300}
              className="w-full rounded-xl bg-white px-3 py-2 text-sm outline-none ring-1 ring-rose-200 focus:ring-2 focus:ring-rose-400"
            />
          </label>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy || reason.trim().length < 3}
              onClick={() => act("reject")}
              className="flex flex-1 items-center justify-center gap-2 rounded-full bg-rose-600 py-2.5 text-sm font-semibold text-white transition hover:bg-rose-500 disabled:opacity-50"
            >
              {busy ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faXmark} />} Rechazar pago
            </button>
            <button type="button" disabled={busy} onClick={() => setMode("idle")} className="rounded-full px-4 text-sm font-semibold text-slate-600 hover:bg-white">
              Cancelar
            </button>
          </div>
        </div>
      )}
    </article>
  )
}

function PagoMovilDetails({ p }: { p: PaymentReviewRow }) {
  const d = p.payload
  const declared = num(d.amount_bs)
  const expected = num(d.expected_amount_bs)
  return (
    <>
      <CopyField label="Referencia" value={String(d.reference_number ?? "—")} />
      <AmountCheck declared={declared} expected={expected} rate={num(d.bs_per_usd)} rateDate={d.rate_value_date ? String(d.rate_value_date) : null} />
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 px-1 pt-1 text-sm">
        <Fact label="Banco de origen" value={d.payer_bank} />
        <Fact label="Fecha del pago" value={d.paid_at ? longDate(String(d.paid_at).slice(0, 10)) : null} />
        <Fact label="Cédula" value={d.payer_cedula} />
        <Fact label="Teléfono" value={d.payer_phone} />
      </dl>
    </>
  )
}

function BinanceDetails({ p }: { p: PaymentReviewRow }) {
  const d = p.payload
  return (
    <>
      <CopyField label="ID de la orden" value={String(d.order_id ?? p.external_reference ?? "—")} />
      <div className="rounded-2xl bg-slate-50 px-4 py-3">
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Monto esperado</p>
        <p className="font-semibold text-slate-800">
          {String(d.expected_amount ?? "—")} {String(d.asset ?? "USDT")}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 px-1 pt-1 text-sm">
        <Fact label="Pagó desde" value={d.payer_account} />
        <Fact label="Fecha del pago" value={d.paid_at ? longDate(String(d.paid_at).slice(0, 10)) : null} />
      </dl>
    </>
  )
}

/** Declarado contra esperado. Un pago de menos es lo más fácil de pasar por
 * alto revisando a ojo, y el que más cuesta: se marca en rojo. */
function AmountCheck({ declared, expected, rate, rateDate }: { declared: number | null; expected: number | null; rate: number | null; rateDate: string | null }) {
  const diff = declared != null && expected != null ? declared - expected : null
  const short = diff != null && diff < -1
  const over = diff != null && diff > 1
  return (
    <div className={`rounded-2xl px-4 py-3 ${short ? "bg-rose-50 ring-1 ring-rose-200" : "bg-slate-50"}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Monto declarado</p>
          <p className="font-semibold text-slate-800">Bs {bs(declared)}</p>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Se le pidió</p>
          <p className="font-semibold text-slate-800">{expected != null ? `Bs ${bs(expected)}` : "—"}</p>
        </div>
      </div>
      {diff != null && (
        <p className={`mt-1.5 flex items-center gap-1.5 text-xs font-semibold ${short ? "text-rose-700" : over ? "text-amber-700" : "text-emerald-700"}`}>
          <FontAwesomeIcon icon={short ? faTriangleExclamation : faCircleCheck} />
          {short ? `Faltan Bs ${bs(-diff)}` : over ? `Pagó Bs ${bs(diff)} de más` : "El monto coincide"}
        </p>
      )}
      {rate != null && (
        <p className="mt-1 text-[11px] text-slate-400">
          Tasa BCV {bs(rate)} Bs/${rateDate ? ` del ${longDate(rateDate)}` : ""}
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Registro (aprobados, rechazados, todos)
// ---------------------------------------------------------------------------

function History({ items }: { items: PaymentReviewRow[] }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
      <ul className="divide-y divide-slate-100">
        {items.map((p) => {
          const s = PAYMENT_STATUS_ONE[p.status]
          const reference = p.payload.reference_number ?? p.payload.order_id ?? p.external_reference
          return (
            <li key={p.id}>
              <details className="group">
                <summary className="grid cursor-pointer list-none grid-cols-1 gap-2 px-5 py-4 transition hover:bg-slate-50 sm:grid-cols-[1fr_auto_auto] sm:items-center sm:gap-6 [&::-webkit-details-marker]:hidden">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{p.customer.full_name}</p>
                    <p className="truncate text-xs text-slate-500">
                      {p.customer.email} · {PROVIDER_LABELS[p.provider] ?? p.provider} · {dateAndTime(p.created_at)}
                    </p>
                  </div>
                  <p className="text-sm font-semibold tabular-nums text-slate-800">{money(p.amount_cents)}</p>
                  <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                    {s && <FontAwesomeIcon icon={s.icon} style={{ color: s.color }} className="text-[11px]" />}
                    {s?.label ?? p.status}
                  </span>
                </summary>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-2 bg-slate-50/60 px-5 py-4 text-sm sm:grid-cols-4">
                  <Fact label={p.provider === "binance_pay" ? "ID de la orden" : "Referencia"} value={reference} />
                  <Fact label="Revisado por" value={p.reviewer_name ?? (p.reviewed_at ? "Automático (pasarela)" : null)} />
                  <Fact label="Revisado" value={p.reviewed_at ? dateAndTime(p.reviewed_at) : null} />
                  {p.status === "approved" ? (
                    <Fact label="Acceso hasta" value={p.access_until ? longDate(p.access_until) : null} />
                  ) : (
                    <Fact label="Motivo" value={p.payload.rejection_reason} />
                  )}
                  {p.provider === "pago_movil" && (
                    <>
                      <Fact label="Monto declarado" value={p.payload.amount_bs != null ? `Bs ${bs(num(p.payload.amount_bs))}` : null} />
                      <Fact label="Banco de origen" value={p.payload.payer_bank} />
                    </>
                  )}
                  {p.provider === "binance_pay" && <Fact label="Pagó desde" value={p.payload.payer_account} />}
                </dl>
              </details>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// ---------------------------------------------------------------------------

function Fact({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="break-words font-medium text-slate-700">{value == null || value === "" ? "—" : String(value)}</dd>
    </div>
  )
}

function PageButton({ disabled, onClick, label, icon }: { disabled: boolean; onClick: () => void; label: string; icon: typeof faChevronLeft }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
    >
      <FontAwesomeIcon icon={icon} className="text-xs" />
    </button>
  )
}

function num(value: unknown): number | null {
  const n = typeof value === "number" ? value : typeof value === "string" && value.trim() !== "" ? Number(value) : NaN
  return Number.isFinite(n) ? n : null
}

const bsFormat = new Intl.NumberFormat("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
function bs(value: number | null): string {
  return value == null ? "—" : bsFormat.format(value)
}

/** "Hace 2 h" / "Hace 3 días" entre dos fechas en hora del negocio. */
function waitingFor(iso: string, asOf: string): string {
  const minutes = Math.max(0, Math.round((parseLocal(asOf).getTime() - parseLocal(iso).getTime()) / 60000))
  if (minutes < 60) return minutes <= 1 ? "Hace un momento" : `Hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Hace ${hours} h`
  const days = Math.floor(hours / 24)
  return days === 1 ? "Hace 1 día" : `Hace ${days} días`
}
