import {
  faChevronLeft,
  faChevronRight,
  faEnvelopeOpenText,
  faMagnifyingGlass,
  faRotateRight,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { api } from "../../api/client"
import type { Campaign, EmailMessageList, EmailSummary } from "../../api/management"
import { dateAndTime, int, pct } from "../../components/charts/format"
import StatTile from "../../components/charts/StatTile"
import { EMAIL_KINDS, EMAIL_STATUS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import { useManagementData } from "../../components/management/useManagementData"

const PAGE_SIZE = 25

const ESTADOS = [
  { value: "", label: "Todos" },
  { value: "sent", label: "Enviados" },
  { value: "failed", label: "Fallidos" },
  { value: "skipped", label: "No enviados" },
]

/** Panel de gerencia → Correos. Qué se le ha escrito a los clientes: los
 * automáticos y las campañas, con su estado y el motivo cuando alguno no
 * salió. Solo lectura; escribir mensajes nuevos es la otra pestaña. */
export default function EmailsPage() {
  const [params, setParams] = useSearchParams()
  const estado = params.get("estado") ?? ""
  const tipo = params.get("tipo") ?? ""
  const q = params.get("q") ?? ""
  const page = Math.max(1, Number(params.get("pagina")) || 1)
  const [draft, setDraft] = useState(q)

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
      if (!v) next.delete(k)
      else next.set(k, v)
    }
    setParams(next, { replace: true })
  }

  const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String((page - 1) * PAGE_SIZE) })
  if (estado) query.set("status", estado)
  if (tipo) query.set("kind", tipo)
  if (q) query.set("search", q)

  const list = useManagementData<EmailMessageList>(`/management/emails?${query}`)
  const summary = useManagementData<EmailSummary>("/management/emails/summary")
  // Mientras una campaña se está enviando, el avance cambia solo.
  const campaigns = useManagementData<Campaign[]>("/management/email-campaigns?limit=6", { refreshMs: 5_000 })
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / PAGE_SIZE)) : 1

  return (
    <PageShell
      title="Correos"
      question="¿Qué le hemos escrito a los clientes y qué tal llegó? Aquí está todo: los avisos automáticos y las campañas."
      loading={list.loading}
      error={list.error}
      hasData={list.data != null}
      filters={
        <>
          <label className="relative block w-full sm:w-72">
            <span className="sr-only">Buscar por cliente, correo o asunto</span>
            <FontAwesomeIcon icon={faMagnifyingGlass} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-xs text-slate-400" />
            <input
              type="search"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Cliente, correo o asunto"
              className="w-full rounded-full border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none transition focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="block">
            <span className="sr-only">Tipo de correo</span>
            <select
              value={tipo}
              onChange={(e) => update({ tipo: e.target.value, pagina: null })}
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 outline-none focus:border-brand-300"
            >
              <option value="">Todos los tipos</option>
              {Object.entries(EMAIL_KINDS).map(([key, k]) => (
                <option key={key} value={key}>
                  {k.label}
                </option>
              ))}
            </select>
          </label>
          <Link
            to="/gerencia/correos/plantillas"
            className="rounded-full bg-ink-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ink-800"
          >
            Escribir un mensaje
          </Link>
        </>
      }
    >
      {summary.data?.blocked_reason && (
        <p className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <FontAwesomeIcon icon={faTriangleExclamation} className="mt-0.5" />
          <span>{summary.data.blocked_reason}</span>
        </p>
      )}

      {summary.data && (
        <section className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <StatTile label={`Enviados (${summary.data.days} días)`} value={int(summary.data.sent)} />
          <StatTile
            emphasis={summary.data.failed > 0}
            label="Fallaron"
            value={int(summary.data.failed)}
            hint={summary.data.failure_rate != null ? `${pct(summary.data.failure_rate)} de los intentos` : "Ningún intento todavía"}
          />
          <StatTile label="No se enviaron" value={int(summary.data.skipped)} hint="Bajas y direcciones de prueba" />
          <StatTile label="Último envío" value={summary.data.last_sent_at ? dateAndTime(summary.data.last_sent_at) : "—"} />
        </section>
      )}

      {campaigns.data && campaigns.data.length > 0 && (
        <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
          <h2 className="border-b border-slate-100 px-5 py-3 text-sm font-semibold text-slate-700">Campañas recientes</h2>
          <ul className="divide-y divide-slate-100">
            {campaigns.data.map((c) => (
              <CampaignRow key={c.id} campaign={c} onChange={campaigns.reload} />
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Estado del correo">
        {ESTADOS.map((e) => (
          <button
            key={e.value}
            type="button"
            role="radio"
            aria-checked={e.value === estado}
            onClick={() => update({ estado: e.value, pagina: null })}
            className={`rounded-full border px-3.5 py-1.5 text-sm font-semibold transition ${
              e.value === estado ? "border-ink-900 bg-ink-900 text-white" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
            }`}
          >
            {e.label}
          </button>
        ))}
      </div>

      {list.data && (
        <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
          <p className="border-b border-slate-100 px-5 py-3 text-sm text-slate-500">
            {int(list.data.total)} {list.data.total === 1 ? "correo" : "correos"}
          </p>

          {list.data.items.length === 0 ? (
            <div className="px-5 py-16 text-center">
              <FontAwesomeIcon icon={faEnvelopeOpenText} className="text-3xl text-slate-200" />
              <p className="mt-3 text-sm text-slate-400">Todavía no se ha enviado ningún correo con estos filtros.</p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {list.data.items.map((m) => {
                const estadoInfo = EMAIL_STATUS[m.status] ?? { label: m.status, className: "bg-slate-100 text-slate-600" }
                const tipoInfo = EMAIL_KINDS[m.kind]
                return (
                  <li key={m.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900">{m.subject}</p>
                        <p className="truncate text-xs text-slate-500">
                          {m.customer ? (
                            <Link to={`/gerencia/clientes/${m.customer.id}`} className="hover:text-brand-700">
                              {m.customer.full_name}
                            </Link>
                          ) : (
                            "—"
                          )}{" "}
                          · {m.to_email}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                          {tipoInfo?.label ?? m.kind}
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${estadoInfo.className}`}>{estadoInfo.label}</span>
                        <span className="whitespace-nowrap text-xs text-slate-400">{dateAndTime(m.created_at)}</span>
                      </div>
                    </div>
                    {m.error && <p className="mt-2 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600">{m.error}</p>}
                  </li>
                )
              })}
            </ul>
          )}

          <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm text-slate-500">
            <span>
              Página {page} de {pages}
            </span>
            <div className="flex gap-2">
              <PageButton disabled={page <= 1} onClick={() => update({ pagina: String(page - 1) })} label="Página anterior" icon={faChevronLeft} />
              <PageButton disabled={page >= pages} onClick={() => update({ pagina: String(page + 1) })} label="Página siguiente" icon={faChevronRight} />
            </div>
          </div>
        </section>
      )}
    </PageShell>
  )
}

function CampaignRow({ campaign, onChange }: { campaign: Campaign; onChange: () => void }) {
  const [busy, setBusy] = useState(false)
  const enviando = campaign.status === "enviando"
  const progreso = campaign.recipients ? Math.round(((campaign.sent + campaign.skipped) / campaign.recipients) * 100) : 100

  async function reanudar() {
    setBusy(true)
    try {
      await api.post(`/management/email-campaigns/${campaign.id}/resume`, {})
      onChange()
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-slate-900">{campaign.name}</p>
          <p className="text-xs text-slate-500">
            {campaign.audience_label} · {dateAndTime(campaign.created_at)}
            {campaign.sender_name && ` · ${campaign.sender_name}`}
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="tabular-nums text-slate-700">
            {int(campaign.sent)} de {int(campaign.recipients)} enviados
          </span>
          {campaign.failed > 0 && <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">{campaign.failed} fallaron</span>}
          {enviando && (
            <button
              type="button"
              onClick={reanudar}
              disabled={busy}
              title="Termina un envío que se quedó a medias. A quien ya le llegó no le vuelve a llegar."
              className="flex items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-40"
            >
              <FontAwesomeIcon icon={faRotateRight} spin={busy} />
              Reanudar
            </button>
          )}
        </div>
      </div>
      {enviando && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${progreso}%` }} />
        </div>
      )}
    </li>
  )
}

function PageButton({ disabled, onClick, label, icon }: { disabled: boolean; onClick: () => void; label: string; icon: typeof faChevronLeft }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
    >
      <FontAwesomeIcon icon={icon} className="text-xs" />
    </button>
  )
}
