import { faChevronLeft, faChevronRight, faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom"
import type { CustomerList, CustomerSort, Segment } from "../../api/management"
import { int, money, relativeDays } from "../../components/charts/format"
import { SEGMENTS, SEGMENT_ORDER, SUBSCRIPTION_LABELS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import SegmentBadge from "../../components/management/SegmentBadge"
import { useManagementData } from "../../components/management/useManagementData"

const PAGE_SIZE = 25

const SORTS: { value: CustomerSort; label: string }[] = [
  { value: "last_active", label: "Actividad más reciente" },
  { value: "signup", label: "Registro más reciente" },
  { value: "messages", label: "Más mensajes al tutor" },
  { value: "paid", label: "Más pagado" },
  { value: "name", label: "Nombre (A–Z)" },
]

export default function CustomersPage() {
  const navigate = useNavigate()
  const location = useLocation()
  // La ficha del cliente vuelve a ESTA lista, con sus filtros y su página.
  const from = { from: location.pathname + location.search }
  // Todos los filtros en la URL: se puede mandar "los clientes en riesgo
  // que más han pagado" como un enlace, y el botón atrás funciona.
  const [params, setParams] = useSearchParams()
  const q = params.get("q") ?? ""
  const segment = (params.get("segmento") as Segment | null) ?? null
  const sort = (params.get("orden") as CustomerSort | null) ?? "last_active"
  const page = Math.max(1, Number(params.get("pagina")) || 1)

  const [draft, setDraft] = useState(q)
  useEffect(() => setDraft(q), [q])
  useEffect(() => {
    // Buscar mientras se escribe, pero sin una petición por tecla.
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

  const query = new URLSearchParams({ sort, limit: String(PAGE_SIZE), offset: String((page - 1) * PAGE_SIZE) })
  if (q) query.set("search", q)
  if (segment) query.set("segment", segment)
  const { data, loading, error } = useManagementData<CustomerList>(`/management/customers?${query}`)
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <PageShell
      title="Clientes"
      question="¿Quién es cada cliente, cómo usa la app y en qué punto está? Pulsa uno para ver su recorrido."
      loading={loading}
      error={error}
      hasData={data != null}
      filters={
        <>
          <label className="relative block w-full sm:w-72">
            <span className="sr-only">Buscar por nombre o email</span>
            <FontAwesomeIcon icon={faMagnifyingGlass} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-xs text-slate-400" />
            <input
              type="search"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Buscar por nombre o email"
              className="w-full rounded-full border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none transition focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="block">
            <span className="sr-only">Ordenar</span>
            <select
              value={sort}
              onChange={(e) => update({ orden: e.target.value, pagina: null })}
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 outline-none focus:border-brand-300"
            >
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </>
      }
    >
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Estado del cliente">
        <SegmentChip label="Todos" selected={segment == null} onClick={() => update({ segmento: null, pagina: null })} />
        {SEGMENT_ORDER.map((s) => (
          <SegmentChip key={s} label={SEGMENTS[s].label} selected={segment === s} onClick={() => update({ segmento: s, pagina: null })} />
        ))}
      </div>

      {data && (
        <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
          <p className="border-b border-slate-100 px-5 py-3 text-sm text-slate-500">
            {int(data.total)} {data.total === 1 ? "cliente" : "clientes"}
            {segment && <> · {SEGMENTS[segment].description.toLowerCase()}</>}
          </p>

          {/* Tabla en pantallas anchas… */}
          <div className="hidden overflow-x-auto lg:block">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr className="border-b border-slate-100">
                  <th scope="col" className="px-5 py-3 font-semibold">Cliente</th>
                  <th scope="col" className="px-3 py-3 font-semibold">Estado</th>
                  <th scope="col" className="px-3 py-3 font-semibold">Nivel</th>
                  <th scope="col" className="px-3 py-3 font-semibold">Última actividad</th>
                  <th scope="col" className="px-3 py-3 text-right font-semibold">Días activos (30 d)</th>
                  <th scope="col" className="px-3 py-3 text-right font-semibold">Mensajes</th>
                  <th scope="col" className="px-3 py-3 text-right font-semibold">Módulos</th>
                  <th scope="col" className="px-3 py-3 font-semibold">Suscripción</th>
                  <th scope="col" className="px-5 py-3 text-right font-semibold">Pagado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/gerencia/clientes/${c.id}`, { state: from })}
                    className="cursor-pointer transition hover:bg-slate-50"
                  >
                    <td className="px-5 py-3">
                      <Link to={`/gerencia/clientes/${c.id}`} state={from} className="font-semibold text-slate-900 hover:text-brand-700" onClick={(e) => e.stopPropagation()}>
                        {c.full_name}
                      </Link>
                      <p className="text-xs text-slate-500">{c.email}</p>
                    </td>
                    <td className="px-3 py-3"><SegmentBadge segment={c.segment} /></td>
                    <td className="px-3 py-3 text-slate-700">{c.level_code ?? "—"}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-slate-700">{relativeDays(c.last_active_at, data.as_of)}</td>
                    <td className="px-3 py-3 text-right tabular-nums text-slate-700">{int(c.active_days_30)}</td>
                    <td className="px-3 py-3 text-right tabular-nums text-slate-700">{int(c.tutor_messages)}</td>
                    <td className="px-3 py-3 text-right tabular-nums text-slate-700">{int(c.modules_completed)}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-slate-700">{SUBSCRIPTION_LABELS[c.subscription_status] ?? c.subscription_status}</td>
                    <td className="px-5 py-3 text-right tabular-nums text-slate-700">{money(c.total_paid_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* …y tarjetas en móvil y tablet, donde nueve columnas no caben. */}
          <ul className="divide-y divide-slate-100 lg:hidden">
            {data.items.map((c) => (
              <li key={c.id}>
                <Link to={`/gerencia/clientes/${c.id}`} state={from} className="block px-5 py-4 transition hover:bg-slate-50">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-900">{c.full_name}</p>
                      <p className="truncate text-xs text-slate-500">{c.email}</p>
                    </div>
                    <SegmentBadge segment={c.segment} />
                  </div>
                  <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <Fact label="Última actividad" value={relativeDays(c.last_active_at, data.as_of)} />
                    <Fact label="Mensajes" value={int(c.tutor_messages)} />
                    <Fact label="Pagado" value={money(c.total_paid_cents)} />
                    <Fact label="Nivel" value={c.level_code ?? "—"} />
                    <Fact label="Módulos" value={int(c.modules_completed)} />
                    <Fact label="Suscripción" value={SUBSCRIPTION_LABELS[c.subscription_status] ?? c.subscription_status} />
                  </dl>
                </Link>
              </li>
            ))}
          </ul>

          {data.items.length === 0 && <p className="px-5 py-12 text-center text-sm text-slate-400">Ningún cliente coincide con estos filtros.</p>}

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

function SegmentChip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onClick}
      className={`rounded-full border px-3.5 py-1.5 text-sm font-semibold transition ${
        selected ? "border-ink-900 bg-ink-900 text-white" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
      }`}
    >
      {label}
    </button>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-slate-400">{label}</dt>
      <dd className="truncate font-medium text-slate-700">{value}</dd>
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
      className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
    >
      <FontAwesomeIcon icon={icon} className="text-xs" />
    </button>
  )
}
