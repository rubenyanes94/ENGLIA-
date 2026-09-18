import { faArrowsRotate, faCheck, faCircleCheck, faCircleXmark, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState, type ReactNode } from "react"
import { useSearchParams } from "react-router-dom"
import type { Alert, MonitoringMetrics, MonitoringStatus, WindowHours } from "../../api/monitoring"
import ChartCard from "../../components/charts/ChartCard"
import ColumnChart from "../../components/charts/ColumnChart"
import LineChart from "../../components/charts/LineChart"
import StatTile from "../../components/charts/StatTile"
import { agoShort, bucketLabel, compact, dateAndTime, duration, int, pct } from "../../components/charts/format"
import { SERIES, STATUS } from "../../components/charts/tokens"
import { CHECK_STATUS, FAILURE_SOURCES, OPERATION_LABELS, PURPOSE_LABELS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import { useManagementData } from "../../components/management/useManagementData"

const WINDOWS: { hours: WindowHours; label: string }[] = [
  { hours: 1, label: "1 hora" },
  { hours: 24, label: "24 horas" },
  { hours: 168, label: "7 días" },
  { hours: 720, label: "30 días" },
]

// Cada minuto: esta pestaña se deja abierta para vigilar, y un estado de
// hace diez minutos no dice si la app funciona AHORA.
const REFRESH_MS = 60_000

export default function SystemPage() {
  const [params, setParams] = useSearchParams()
  const hours = (WINDOWS.find((w) => w.hours === Number(params.get("ventana")))?.hours ?? 24) as WindowHours
  const [auto, setAuto] = useState(true)

  const status = useManagementData<MonitoringStatus>("/management/monitoring/status", { refreshMs: auto ? REFRESH_MS : undefined })
  const metrics = useManagementData<MonitoringMetrics>(`/management/monitoring/metrics?hours=${hours}`, {
    refreshMs: auto ? REFRESH_MS : undefined,
  })

  function setHours(h: WindowHours) {
    const next = new URLSearchParams(params)
    next.set("ventana", String(h))
    setParams(next, { replace: true })
  }

  return (
    <PageShell
      title="Sistema"
      question="¿Funciona todo ahora mismo? Estado en vivo de la app, rendimiento de Nemotron y fallos detectados."
      loading={metrics.loading}
      error={metrics.error ?? status.error}
      hasData={metrics.data != null}
      filters={
        <>
          <WindowPicker value={hours} onChange={setHours} />
          <RefreshControl
            updatedAt={status.updatedAt}
            loading={status.loading || metrics.loading}
            auto={auto}
            onToggleAuto={() => setAuto((a) => !a)}
            onRefresh={() => {
              status.reload()
              metrics.reload()
            }}
          />
        </>
      }
    >
      <StatusSection status={status.data} loading={status.loading} />
      {metrics.data && <MetricsSections m={metrics.data} />}
    </PageShell>
  )
}

// ---------------------------------------------------------------------------
// Controles
// ---------------------------------------------------------------------------

function WindowPicker({ value, onChange }: { value: WindowHours; onChange: (h: WindowHours) => void }) {
  return (
    <div role="radiogroup" aria-label="Ventana de tiempo" className="inline-flex flex-wrap gap-1 rounded-full border border-slate-200 bg-white p-1">
      {WINDOWS.map((w) => {
        const selected = w.hours === value
        return (
          <button
            key={w.hours}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(w.hours)}
            className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-semibold transition ${
              selected ? "bg-ink-900 text-white" : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {selected && <FontAwesomeIcon icon={faCheck} className="text-[11px]" />}
            {w.label}
          </button>
        )
      })}
    </div>
  )
}

function RefreshControl({
  updatedAt,
  loading,
  auto,
  onToggleAuto,
  onRefresh,
}: {
  updatedAt: Date | null
  loading: boolean
  auto: boolean
  onToggleAuto: () => void
  onRefresh: () => void
}) {
  // Re-render cada 5 s solo para que "hace N s" avance.
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <span className="hidden sm:inline" aria-live="polite">
        {updatedAt ? `Actualizado ${agoShort(updatedAt, now)}` : "Cargando…"}
      </span>
      <label className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">
        <input type="checkbox" checked={auto} onChange={onToggleAuto} className="accent-brand-600" />
        Auto
      </label>
      <button
        type="button"
        onClick={onRefresh}
        title="Actualizar ahora"
        className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
      >
        <FontAwesomeIcon icon={faArrowsRotate} spin={loading} />
        <span className="sr-only">Actualizar ahora</span>
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Estado en vivo
// ---------------------------------------------------------------------------

const OVERALL = {
  ok: { icon: faCircleCheck, color: STATUS.good, title: "Todo funciona", text: "Todas las comprobaciones pasan y no hay avisos en la última hora.", box: "border-emerald-200 bg-emerald-50" },
  warning: { icon: faTriangleExclamation, color: STATUS.warning, title: "Funciona, con avisos", text: "La app responde, pero hay cosas que revisar.", box: "border-amber-200 bg-amber-50" },
  critical: { icon: faCircleXmark, color: STATUS.critical, title: "Hay fallas", text: "Algo no funciona y los usuarios probablemente lo están notando.", box: "border-rose-200 bg-rose-50" },
}

function StatusSection({ status, loading }: { status: MonitoringStatus | null; loading: boolean }) {
  if (!status) {
    return (
      <p className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-400">
        {loading ? "Comprobando los servicios en vivo (NVIDIA, base de datos, Redis, worker)…" : "No se pudo obtener el estado."}
      </p>
    )
  }
  const o = OVERALL[status.overall]
  return (
    <>
      <section className={`flex flex-wrap items-center gap-4 rounded-3xl border p-5 sm:p-6 ${o.box}`} aria-live="polite">
        <FontAwesomeIcon icon={o.icon} style={{ color: o.color }} className="text-3xl" />
        <div className="min-w-0 flex-1">
          <h2 className="text-xl font-bold text-slate-900">{o.title}</h2>
          <p className="text-sm text-slate-600">
            {o.text} Comprobado el {dateAndTime(status.checked_at)}
          </p>
        </div>
        {status.alerts.length > 0 && (
          <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-slate-700">
            {status.alerts.length} {status.alerts.length === 1 ? "aviso" : "avisos"}
          </span>
        )}
      </section>

      {status.alerts.length > 0 && (
        <ul className="space-y-3">
          {status.alerts.map((a) => (
            <AlertItem key={`${a.title}-${a.detail}`} alert={a} />
          ))}
        </ul>
      )}

      <section>
        <h2 className="mb-3 text-lg font-bold text-slate-900">Comprobaciones en vivo</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {status.checks.map((c) => {
            const s = CHECK_STATUS[c.status]
            return (
              <div
                key={c.key + c.label}
                className={`flex flex-col rounded-2xl border bg-white p-4 shadow-sm ${c.status === "ok" ? "border-slate-200" : c.status === "critical" ? "border-rose-300" : "border-amber-300"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-800">{c.label}</p>
                  <span className="flex shrink-0 items-center gap-1.5 text-xs font-semibold text-slate-600">
                    <FontAwesomeIcon icon={s.icon} style={{ color: s.color }} />
                    {s.label}
                  </span>
                </div>
                <p className="mt-1.5 break-words text-xs leading-relaxed text-slate-500">{c.detail}</p>
                {c.hint && <p className="mt-2 text-xs leading-relaxed text-slate-700">{c.hint}</p>}
                {c.latency_ms != null && <p className="mt-auto pt-2 text-[11px] tabular-nums text-slate-400">Respondió en {duration(c.latency_ms)}</p>}
              </div>
            )
          })}
        </div>
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
        <summary className="cursor-pointer font-semibold text-slate-700">Configuración activa de este servidor</summary>
        <p className="mt-2 text-xs text-slate-500">Lo que el proceso usa de verdad, no lo que dice el archivo .env: si no cuadran, el contenedor arrastra variables antiguas.</p>
        <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2 xl:grid-cols-3">
          <ConfigRow label="Proveedor del modelo" value={status.config.llm_host} />
          <ConfigRow label="Modelo del chat" value={status.config.llm_model} />
          <ConfigRow label="Embeddings" value={status.config.embedding_model} />
          <ConfigRow label="Moderación" value={status.config.moderation_model} />
          <ConfigRow label="Pronunciación" value={status.config.pronunciation_model} />
          <ConfigRow label="Voz" value={status.config.tts_provider} />
          <ConfigRow label="Llamadas simultáneas" value={String(status.config.llm_max_concurrency)} />
          <ConfigRow label="Reintentos" value={String(status.config.llm_max_retries)} />
          <ConfigRow label="Clave de API" value={status.config.api_key_configured ? "Configurada" : "FALTA"} />
          <ConfigRow label="Entorno" value={status.config.environment} />
        </dl>
      </details>
    </>
  )
}

function AlertItem({ alert }: { alert: Alert }) {
  const critical = alert.severity === "critical"
  return (
    <li className={`flex gap-3 rounded-2xl border bg-white p-4 shadow-sm ${critical ? "border-rose-300" : "border-amber-300"}`}>
      <FontAwesomeIcon
        icon={critical ? faCircleXmark : faTriangleExclamation}
        style={{ color: critical ? STATUS.critical : STATUS.warning }}
        className="mt-0.5 shrink-0"
      />
      <div className="min-w-0">
        <p className="text-sm font-semibold text-slate-900">
          <span className="sr-only">{critical ? "Falla: " : "Aviso: "}</span>
          {alert.title}
        </p>
        <p className="mt-0.5 break-words text-sm text-slate-600">{alert.detail}</p>
        {alert.hint && <p className="mt-1 text-xs text-slate-500">{alert.hint}</p>}
      </div>
    </li>
  )
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="break-all font-mono text-xs text-slate-700">{value}</dd>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Métricas
// ---------------------------------------------------------------------------

function SectionTitle({ children, sub }: { children: ReactNode; sub: string }) {
  return (
    <div className="pt-2">
      <h2 className="text-lg font-bold text-slate-900">{children}</h2>
      <p className="text-sm text-slate-500">{sub}</p>
    </div>
  )
}

function MetricsSections({ m }: { m: MonitoringMetrics }) {
  const x = (iso: string) => bucketLabel(iso, m.hours)
  const tramo = m.bucket_minutes >= 1440 ? "día" : m.bucket_minutes >= 60 ? `${m.bucket_minutes / 60} h` : `${m.bucket_minutes} min`
  const llm = m.llm
  const totalTokens = llm.input_tokens + llm.output_tokens

  const slowRoutes = [...m.routes].filter((r) => r.requests >= 3 && r.p95_ms != null).sort((a, b) => (b.p95_ms ?? 0) - (a.p95_ms ?? 0)).slice(0, 10)
  const errorRoutes = m.routes.filter((r) => r.server_errors > 0).sort((a, b) => b.server_errors - a.server_errors)

  return (
    <>
      <SectionTitle sub="Cada llamada al modelo: cuánto tarda, cuántos tokens gasta y cuántas fallan. Un reintento que salva la llamada no cuenta como fallo.">
        Nemotron
      </SectionTitle>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-3 2xl:grid-cols-6">
        <StatTile label="Llamadas al modelo" value={int(llm.calls)} hint={`${int(llm.attempts)} intentos · ${int(llm.retried_calls)} necesitaron reintento`} />
        <StatTile label="Tokens usados" value={compact(totalTokens)} hint={`${compact(llm.input_tokens)} de entrada · ${compact(llm.output_tokens)} de salida`} />
        <StatTile label="Respuesta del tutor" value={duration(llm.tutor_p50_ms)} hint={`Mediana · el 5 % más lento, ${duration(llm.tutor_p95_ms)}`} />
        <StatTile label="Chat, todas las funciones" value={duration(llm.chat_p50_ms)} hint={`Mediana · p95 ${duration(llm.chat_p95_ms)}`} />
        <StatTile
          label="Llamadas fallidas"
          value={pct(llm.calls ? llm.failed_calls / llm.calls : null)}
          hint={`${int(llm.failed_calls)} fallaron incluso tras reintentar`}
        />
        <StatTile label="Respuestas cortadas" value={int(llm.truncated)} hint="Se quedaron sin tokens a mitad de frase" />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ChartCard
          title="Tiempo de respuesta del chat"
          description={`Mediana y percentil 95 por tramo de ${tramo}. Si el p95 se despega de la mediana, unas pocas respuestas se están haciendo muy largas.`}
          table={{
            columns: ["Tramo", "Mediana", "p95", "Intentos", "Fallos"],
            numeric: [1, 2, 3, 4],
            rows: m.llm_series.map((p) => [x(p.bucket), duration(p.p50_ms), duration(p.p95_ms), int(p.attempts), int(p.errors)]),
          }}
        >
          <LineChart
            data={m.llm_series.map((p) => ({ x: p.bucket, values: [p.p50_ms, p.p95_ms] }))}
            series={[
              { name: "Mediana", color: SERIES[0] },
              { name: "p95", color: SERIES[1] },
            ]}
            formatValue={duration}
            formatX={x}
            partialLast
          />
        </ChartCard>
        <ChartCard
          title="Tokens por tramo"
          description={`Entrada + salida de todas las llamadas, por tramo de ${tramo}. La tabla los separa.`}
          table={{
            columns: ["Tramo", "Entrada", "Salida", "Total"],
            numeric: [1, 2, 3],
            rows: m.llm_series.map((p) => [x(p.bucket), int(p.input_tokens), int(p.output_tokens), int(p.input_tokens + p.output_tokens)]),
          }}
        >
          <ColumnChart
            data={m.llm_series.map((p) => ({ x: p.bucket, value: p.input_tokens + p.output_tokens }))}
            label="Tokens"
            formatValue={compact}
            formatX={x}
            partialLast
          />
        </ChartCard>
      </section>

      <TableCard
        title="Por función"
        description="Qué parte de la app llama al modelo, cuánto tarda cada una y cuánto gasta. Es la tabla para decidir dónde optimizar."
        head={["Función", "Tipo", "Llamadas", "Fallos", "Mediana", "p95", "Tokens medios (ent. / sal.)", "Tokens totales"]}
        numeric={[2, 3, 4, 5, 6, 7]}
        rows={m.llm_by_purpose.map((p) => [
          PURPOSE_LABELS[p.purpose] ?? p.purpose,
          OPERATION_LABELS[p.operation] ?? p.operation,
          int(p.calls),
          p.errors ? <span className="font-semibold text-rose-700">{int(p.errors)}</span> : "0",
          duration(p.p50_ms),
          duration(p.p95_ms),
          p.operation === "tts" ? "—" : `${int(p.avg_input_tokens != null ? Math.round(p.avg_input_tokens) : null)} / ${int(p.avg_output_tokens != null ? Math.round(p.avg_output_tokens) : null)}`,
          p.operation === "tts" ? "—" : compact(p.total_tokens),
        ])}
        empty="Ninguna llamada al modelo en esta ventana."
      />

      <TableCard
        title="Por modelo"
        head={["Modelo", "Tipo", "Intentos", "Fallos", "Mediana", "p95", "Tokens entrada", "Tokens salida"]}
        numeric={[2, 3, 4, 5, 6, 7]}
        rows={m.llm_by_model.map((r) => [
          <span className="font-mono text-xs">{r.model}</span>,
          OPERATION_LABELS[r.operation] ?? r.operation,
          int(r.attempts),
          r.errors ? <span className="font-semibold text-rose-700">{int(r.errors)}</span> : "0",
          duration(r.p50_ms),
          duration(r.p95_ms),
          compact(r.input_tokens),
          compact(r.output_tokens),
        ])}
        empty="Ninguna llamada al modelo en esta ventana."
      />

      <SectionTitle sub="Cada petición del navegador al servidor: si responde, cuánto tarda y cuáles fallan.">Aplicación web</SectionTitle>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-3 2xl:grid-cols-5">
        <StatTile label="Peticiones a la API" value={int(m.http.requests)} />
        <StatTile
          label="Errores del servidor (5xx)"
          value={int(m.http.server_errors)}
          hint={m.http.requests ? `${pct(m.http.server_errors / m.http.requests)} de las peticiones` : undefined}
        />
        <StatTile label="Rechazadas (4xx)" value={int(m.http.client_errors)} hint="Sin sesión, datos inválidos, no encontrado: normalmente no son fallos" />
        <StatTile label="Tiempo de respuesta" value={duration(m.http.p50_ms)} hint={`Mediana · p95 ${duration(m.http.p95_ms)}`} />
        <StatTile label="Errores en navegadores" value={int(m.client_errors)} hint="JavaScript que falló en el equipo de un usuario" />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ChartCard
          title="Peticiones por tramo"
          description={`Volumen de uso de la API por tramo de ${tramo}.`}
          table={{
            columns: ["Tramo", "Peticiones", "Errores 5xx", "p95"],
            numeric: [1, 2, 3],
            rows: m.http_series.map((p) => [x(p.bucket), int(p.requests), int(p.server_errors), duration(p.p95_ms)]),
          }}
        >
          <ColumnChart data={m.http_series.map((p) => ({ x: p.bucket, value: p.requests }))} label="Peticiones" formatValue={int} formatX={x} partialLast />
        </ChartCard>
        <ChartCard
          title="Tiempo de respuesta de la API (p95)"
          description="El 5 % más lento de cada tramo. Las llamadas al tutor tardan lo que tarda Nemotron; el resto debería ir en milisegundos."
          table={{
            columns: ["Tramo", "p95"],
            numeric: [1],
            rows: m.http_series.map((p) => [x(p.bucket), duration(p.p95_ms)]),
          }}
        >
          <LineChart
            data={m.http_series.map((p) => ({ x: p.bucket, values: [p.p95_ms] }))}
            series={[{ name: "p95", color: SERIES[0] }]}
            formatValue={duration}
            formatX={x}
            partialLast
          />
        </ChartCard>
      </section>

      <section className="grid grid-cols-1 items-start gap-6 2xl:grid-cols-2">
        <TableCard
          title="Rutas más lentas"
          description="Por percentil 95, entre las rutas con al menos 3 peticiones."
          head={["Ruta", "Peticiones", "Mediana", "p95", "Máximo"]}
          numeric={[1, 2, 3, 4]}
          rows={slowRoutes.map((r) => [<RouteCell method={r.method} route={r.route} />, int(r.requests), duration(r.p50_ms), duration(r.p95_ms), duration(r.max_ms)])}
          empty="Todavía no hay suficientes peticiones para comparar."
        />
        <TableCard
          title="Rutas con errores del servidor"
          description="Las que devolvieron algún 5xx en la ventana."
          head={["Ruta", "Peticiones", "Errores 5xx", "% de error"]}
          numeric={[1, 2, 3]}
          rows={errorRoutes.map((r) => [<RouteCell method={r.method} route={r.route} />, int(r.requests), int(r.server_errors), pct(r.server_errors / r.requests)])}
          empty="Ninguna ruta falló en esta ventana."
        />
      </section>

      <FailureList failures={m.failures} />
    </>
  )
}

function RouteCell({ method, route }: { method: string; route: string }) {
  return (
    <span className="font-mono text-xs">
      <span className="mr-1.5 font-semibold text-slate-400">{method}</span>
      {route}
    </span>
  )
}

function TableCard({
  title,
  description,
  head,
  rows,
  numeric = [],
  empty,
}: {
  title: string
  description?: string
  head: string[]
  rows: ReactNode[][]
  numeric?: number[]
  empty: string
}) {
  const isNum = new Set(numeric)
  return (
    <section className="min-w-0 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h3 className="text-base font-bold text-slate-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-500">
            <tr className="border-b border-slate-100">
              {head.map((h, i) => (
                <th key={h} scope="col" className={`whitespace-nowrap px-2 py-2 font-semibold ${isNum.has(i) ? "text-right" : ""}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, r) => (
              <tr key={r}>
                {row.map((cell, i) => (
                  <td key={i} className={`px-2 py-2 text-slate-700 ${isNum.has(i) ? "whitespace-nowrap text-right tabular-nums" : ""}`}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="py-6 text-center text-sm text-slate-400">{empty}</p>}
      </div>
    </section>
  )
}

function FailureList({ failures }: { failures: MonitoringMetrics["failures"] }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-bold text-slate-900">Fallos recientes</h2>
      <p className="mt-1 text-sm text-slate-500">
        Del modelo (llamadas que fallaron), de la API (errores 5xx con dónde saltó) y de los navegadores de los usuarios. Los fallos
        idénticos se agrupan: el número dice cuántas veces pasó.
      </p>
      {failures.length === 0 ? (
        <p className="flex items-center gap-2 py-8 text-sm text-slate-500">
          <FontAwesomeIcon icon={faCircleCheck} style={{ color: STATUS.good }} />
          Ningún fallo en esta ventana.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-slate-100">
          {failures.map((f, i) => (
            <li key={`${f.at}-${i}`} className="py-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex min-w-0 items-start gap-2">
                  <span className="mt-0.5 shrink-0 rounded-full border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                    {FAILURE_SOURCES[f.source]}
                  </span>
                  {f.occurrences > 1 && (
                    <span className="mt-0.5 shrink-0 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-bold tabular-nums text-rose-700">
                      ×{int(f.occurrences)}
                    </span>
                  )}
                  <div className="min-w-0">
                    <p className="break-words text-sm font-medium text-slate-800">{f.title.split(" · ").map((part, j) => (j === 0 ? PURPOSE_LABELS[part] ?? part : ` · ${part}`))}</p>
                    <p className="break-words text-xs text-slate-600">{f.message}</p>
                  </div>
                </div>
                <p className="shrink-0 text-right text-xs text-slate-400">
                  <time>{dateAndTime(f.at)}</time>
                  {f.occurrences > 1 && <span className="block">desde {dateAndTime(f.first_at)}</span>}
                </p>
              </div>
              {f.detail && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs font-semibold text-brand-600">Ver detalle</summary>
                  <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700">
                    {f.detail}
                  </pre>
                </details>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
