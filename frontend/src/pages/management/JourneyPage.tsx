import type { Journey } from "../../api/management"
import BarList from "../../components/charts/BarList"
import ChartCard from "../../components/charts/ChartCard"
import Funnel from "../../components/charts/Funnel"
import StatTile from "../../components/charts/StatTile"
import { dec, int, pct } from "../../components/charts/format"
import { ACCENT, DEEMPHASIS } from "../../components/charts/tokens"
import { FUNNEL_LABELS, LEVEL_LABELS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import PeriodPicker from "../../components/management/PeriodPicker"
import { useManagementData } from "../../components/management/useManagementData"
import { usePeriod } from "../../components/management/usePeriod"

export default function JourneyPage() {
  const { days, setDays } = usePeriod(90)
  const { data, loading, error } = useManagementData<Journey>(`/management/journey?days=${days}`)

  return (
    <PageShell
      title="Journey del cliente"
      question="De los que se registraron en el periodo: ¿cuántos llegan a practicar, a volver, a lograr algo y a pagar?"
      filters={<PeriodPicker value={days} onChange={setDays} />}
      loading={loading}
      error={error}
      hasData={data != null}
    >
      {data && <JourneyBody data={data} />}
    </PageShell>
  )
}

function JourneyBody({ data }: { data: Journey }) {
  const stages = data.funnel.map((s) => ({ ...s, ...FUNNEL_LABELS[s.key] }))
  // La mayor caída de paso a paso: es donde más rinde intervenir.
  let worst: { from: string; to: string; lost: number; rate: number } | null = null
  for (let i = 1; i < stages.length; i++) {
    const prev = stages[i - 1].customers
    if (!prev) continue
    const rate = stages[i].customers / prev
    if (!worst || rate < worst.rate) worst = { from: stages[i - 1].label, to: stages[i].label, lost: prev - stages[i].customers, rate }
  }
  const o = data.outcomes

  return (
    <>
      <section className="grid grid-cols-1 gap-6 2xl:grid-cols-3">
        <ChartCard
          className="2xl:col-span-2"
          title="Embudo de la cohorte"
          description="Etapas anidadas: cada una exige haber pasado la anterior, así que el embudo nunca se ensancha."
          table={{
            columns: ["Etapa", "Clientes", "% del registro", "% de la etapa anterior"],
            numeric: [1, 2, 3],
            rows: stages.map((s, i) => [
              s.label,
              int(s.customers),
              pct(stages[0].customers ? s.customers / stages[0].customers : null),
              i === 0 ? "—" : pct(stages[i - 1].customers ? s.customers / stages[i - 1].customers : null),
            ]),
          }}
        >
          <Funnel stages={stages} />
          {worst && (
            <p className="mt-5 rounded-2xl bg-brand-50 px-4 py-3 text-sm leading-relaxed text-slate-700">
              La mayor pérdida está entre <strong>{worst.from.toLowerCase()}</strong> y{" "}
              <strong>{worst.to.toLowerCase()}</strong>: solo pasa el {pct(worst.rate)} ({int(worst.lost)} clientes se quedan ahí).
              Es el paso donde una mejora mueve más el resultado final.
            </p>
          )}
        </ChartCard>

        <div className="grid grid-cols-2 content-start gap-4 xl:grid-cols-4 2xl:grid-cols-1">
          <StatTile
            label="Hasta practicar"
            value={data.median_hours_to_activate != null ? formatHours(data.median_hours_to_activate) : "—"}
            hint="Mediana desde el registro hasta la primera práctica"
          />
          <StatTile
            label="Hasta el primer logro"
            value={data.median_days_to_achieve != null ? `${dec(data.median_days_to_achieve)} días` : "—"}
            hint="Hasta completar un módulo o certificar nivel"
          />
          <StatTile
            label="Hasta pagar"
            value={data.median_days_to_pay != null ? `${dec(data.median_days_to_pay)} días` : "—"}
            hint="Mediana desde el registro hasta el primer pago"
          />
          <StatTile
            label="Pagaron (cualquier recorrido)"
            value={int(data.paid_any)}
            hint={`${int(data.funnel[4]?.customers ?? 0)} de ellos recorrieron todo el embudo`}
          />
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-5">
        <StatTile label="Exámenes presentados" value={int(o.exams_taken)} hint="En el periodo, de toda la base" />
        <StatTile label="Exámenes aprobados" value={pct(o.exams_taken ? o.exams_passed / o.exams_taken : null)} hint={`${int(o.exams_passed)} de ${int(o.exams_taken)}`} />
        <StatTile label="Módulos completados" value={int(o.modules_completed)} />
        <StatTile label="Niveles certificados" value={int(o.levels_certified)} />
        <StatTile
          label="Tareas con el tutor"
          value={pct(o.tutor_tasks ? o.tutor_tasks_completed / o.tutor_tasks : null)}
          hint={`${int(o.tutor_tasks_completed)} logradas de ${int(o.tutor_tasks)} intentos`}
        />
      </section>

      <section className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
        <ChartCard
          className="xl:col-span-2"
          title="Dónde se atascan en el currículo"
          description="Por módulo, en orden: cuántos lo empezaron y cuántos lo completaron (toda la historia). Donde cae la barra gris es donde se deja de avanzar."
          table={{
            columns: ["Módulo", "Título", "Empezaron", "Completaron", "% completado"],
            numeric: [2, 3, 4],
            rows: data.modules.map((m) => [m.code ?? "—", m.title, int(m.started), int(m.completed), pct(m.started ? m.completed / m.started : null)]),
          }}
        >
          <ModuleProgression modules={data.modules} />
        </ChartCard>

        <ChartCard
          title="Clientes por nivel"
          description="Nivel MCER actual de cada cliente."
          table={{
            columns: ["Nivel", "Clientes"],
            numeric: [1],
            rows: data.levels.map((l) => [LEVEL_LABELS[l.level_code] ?? l.level_code, int(l.customers)]),
          }}
        >
          <BarList
            items={data.levels.map((l) => ({
              key: l.level_code,
              label: LEVEL_LABELS[l.level_code] ?? l.level_code,
              value: l.customers,
              display: int(l.customers),
            }))}
          />
        </ChartCard>
      </section>
    </>
  )
}

function formatHours(h: number): string {
  return h < 48 ? `${dec(h)} h` : `${dec(h / 24)} días`
}

/** Barra gris = empezaron; violeta encima = completaron. Mismo origen y
 * misma escala (lo completado está dentro de lo empezado), así que se
 * superponen en vez de ir lado a lado. Leyenda siempre: son dos series. */
function ModuleProgression({ modules }: { modules: Journey["modules"] }) {
  const max = Math.max(1, ...modules.map((m) => m.started))
  return (
    <div>
      <ul className="mb-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: DEEMPHASIS }} />
          Empezaron
        </li>
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: ACCENT }} />
          Completaron
        </li>
      </ul>
      <ol className="space-y-2.5">
        {modules.map((m) => (
          <li key={`${m.level_code}-${m.code}`} className="grid grid-cols-[5rem_1fr_auto] items-center gap-3 sm:grid-cols-[12rem_1fr_auto]">
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-700">{m.code}</p>
              <p className="hidden truncate text-xs text-slate-500 sm:block">{m.title}</p>
            </div>
            <div className="relative h-3" title={`${m.code}: ${m.started} empezaron, ${m.completed} completaron`}>
              <div className="absolute inset-y-0 left-0 rounded-r" style={{ width: `${(m.started / max) * 100}%`, background: DEEMPHASIS }} />
              <div className="absolute inset-y-0 left-0 rounded-r" style={{ width: `${(m.completed / max) * 100}%`, background: ACCENT }} />
            </div>
            <p className="w-24 text-right text-xs tabular-nums text-slate-600">
              <span className="font-semibold text-slate-900">{int(m.completed)}</span> / {int(m.started)}
              <span className="ml-1 text-slate-400">{m.started ? pct(m.completed / m.started) : ""}</span>
            </p>
          </li>
        ))}
      </ol>
    </div>
  )
}
