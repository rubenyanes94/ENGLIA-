import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { Link } from "react-router-dom"
import type { Retention, Segment } from "../../api/management"
import ChartCard from "../../components/charts/ChartCard"
import Heatmap from "../../components/charts/Heatmap"
import StatTile from "../../components/charts/StatTile"
import { int, pct, shortDate } from "../../components/charts/format"
import { SEGMENTS, SEGMENT_ORDER } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import { useManagementData } from "../../components/management/useManagementData"

export default function RetentionPage() {
  // Sin selector de periodo a propósito: las cohortes SON su propio eje de
  // tiempo (una fila por semana de alta), y D1/D7/D30 miran toda la historia.
  const { data, loading, error } = useManagementData<Retention>("/management/retention?weeks=10")

  return (
    <PageShell
      title="Retención"
      question="¿Los clientes vuelven? ¿Cuántos se quedan semana a semana y en qué estado está la base hoy?"
      loading={loading}
      error={error}
      hasData={data != null}
    >
      {data && <RetentionBody data={data} />}
    </PageShell>
  )
}

function RetentionBody({ data }: { data: Retention }) {
  const dayN = new Map(data.day_n.map((d) => [d.day, d]))
  const segments = data.lifecycle.segments
  const total = SEGMENT_ORDER.reduce((acc, s) => acc + (segments[s] ?? 0), 0)
  const weeks = Array.from({ length: data.weeks }, (_, k) => k)

  return (
    <>
      <section className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {[1, 7, 30].map((n) => {
          const d = dayN.get(n)
          return (
            <StatTile
              key={n}
              label={`Retención día ${n}`}
              value={pct(d?.rate)}
              hint={d ? `${int(d.retained)} de ${int(d.eligible)} usaron la app el día ${n} tras registrarse` : undefined}
            />
          )
        })}
        <StatTile
          emphasis
          label="CURR semanal"
          value={pct(data.lifecycle.curr)}
          hint={`De ${int(data.lifecycle.last_week_active)} activos la semana pasada, ${int(data.lifecycle.retained_this_week)} siguen esta semana`}
        />
      </section>

      <ChartCard
        title="Cohortes semanales"
        description="Cada fila es una semana de altas; cada columna, las semanas que pasaron desde entonces. La celda dice qué parte de esa cohorte usó la app esa semana. Si las filas nuevas aguantan mejor que las viejas, el producto está mejorando."
        table={{
          columns: ["Semana de alta", "Altas", ...weeks.map((k) => `Sem. ${k}`)],
          numeric: [1, ...weeks.map((k) => k + 2)],
          rows: data.cohorts.map((c) => [shortDate(c.week_start), int(c.size), ...c.retention.map((r) => (r == null ? "" : pct(r)))]),
        }}
      >
        <Heatmap
          rows={data.cohorts.map((c) => ({ key: c.week_start, label: shortDate(c.week_start), sub: `${int(c.size)} altas` }))}
          columns={weeks.map((k) => ({ key: String(k), label: k === 0 ? "Sem. 0" : `+${k}` }))}
          values={data.cohorts.map((c) => c.retention)}
          scale={(v) => v}
          showValues
          formatValue={(v) => `${Math.round(v * 100)}`}
          describe={(r, c, v) => {
            const cohort = data.cohorts[r]
            return `Altas de la semana del ${shortDate(cohort.week_start)} (${int(cohort.size)}): el ${pct(v)} usó la app ${c === 0 ? "su primera semana" : `${c} semana${c === 1 ? "" : "s"} después`}`
          }}
          legend={["0 %", "100 %"]}
          minCell={34}
        />
      </ChartCard>

      <ChartCard
        title="Estado de la base de clientes hoy"
        description="Cada cliente en un solo estado, según cuándo usó la app por última vez. Es el modelo de crecimiento que popularizó Duolingo."
        table={{
          columns: ["Estado", "Qué significa", "Clientes", "% de la base"],
          numeric: [2, 3],
          rows: SEGMENT_ORDER.map((s) => [SEGMENTS[s].label, SEGMENTS[s].description, int(segments[s] ?? 0), pct(total ? (segments[s] ?? 0) / total : null)]),
        }}
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {SEGMENT_ORDER.map((s) => (
            <SegmentCard key={s} segment={s} count={segments[s] ?? 0} total={total} />
          ))}
        </div>
      </ChartCard>
    </>
  )
}

function SegmentCard({ segment, count, total }: { segment: Segment; count: number; total: number }) {
  const s = SEGMENTS[segment]
  const share = total ? count / total : 0
  return (
    <Link
      to={`/gerencia/clientes?segmento=${segment}`}
      className="group flex flex-col rounded-2xl border border-slate-200 p-4 transition hover:border-brand-200 hover:bg-brand-50/40"
    >
      <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
        <FontAwesomeIcon icon={s.icon} style={{ color: s.color }} />
        {s.label}
      </p>
      <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">{int(count)}</p>
      <div className="mt-2 h-1.5 w-full rounded-full bg-slate-100">
        <div className="h-full rounded-full" style={{ width: `${share * 100}%`, background: s.color }} />
      </div>
      <p className="mt-1 text-xs tabular-nums text-slate-500">{pct(share)} de la base</p>
      <p className="mt-3 text-xs leading-relaxed text-slate-500">{s.description}.</p>
      <p className="mt-2 text-xs leading-relaxed text-slate-700">{s.action}</p>
      <p className="mt-auto pt-3 text-xs font-semibold text-brand-600 group-hover:underline">Ver clientes →</p>
    </Link>
  )
}
