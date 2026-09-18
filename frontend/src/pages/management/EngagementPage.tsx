import type { Engagement } from "../../api/management"
import BarList from "../../components/charts/BarList"
import ChartCard from "../../components/charts/ChartCard"
import Heatmap from "../../components/charts/Heatmap"
import StatTile from "../../components/charts/StatTile"
import { dec, int, pct } from "../../components/charts/format"
import { FEATURE_LABELS, SCREEN_LABELS, WEEKDAYS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import PeriodPicker from "../../components/management/PeriodPicker"
import { useManagementData } from "../../components/management/useManagementData"
import { usePeriod } from "../../components/management/usePeriod"

// "Abrir la app" e "hitos" no son práctica: se enseñan aparte, al final,
// para que la lista de funciones hable solo de aprendizaje.
const LEARNING_ORDER = ["tutor", "exam", "library", "exercise", "sentence_game"]
const HOURS = Array.from({ length: 24 }, (_, h) => h)

export default function EngagementPage() {
  const { days, setDays } = usePeriod(30)
  const { data, loading, error } = useManagementData<Engagement>(`/management/engagement?days=${days}`)

  return (
    <PageShell
      title="Consumo"
      question="¿Qué usan los clientes, cuánto y cuándo? ¿Qué es lo que más les cuesta?"
      filters={<PeriodPicker value={days} onChange={setDays} />}
      loading={loading}
      error={error}
      hasData={data != null}
    >
      {data && <EngagementBody data={data} />}
    </PageShell>
  )
}

function EngagementBody({ data }: { data: Engagement }) {
  const { tutor } = data
  const byFeature = new Map(data.features.map((f) => [f.feature, f]))
  const appOpeners = byFeature.get("app")?.customers ?? 0
  const learners = Math.max(0, ...data.features.filter((f) => LEARNING_ORDER.includes(f.feature)).map((f) => f.customers))
  const base = Math.max(appOpeners, learners)

  const features = LEARNING_ORDER.filter((k) => byFeature.has(k)).map((k) => {
    const f = byFeature.get(k)!
    const meta = FEATURE_LABELS[k]
    return {
      key: k,
      label: meta.label,
      value: f.customers,
      display: `${int(f.customers)} clientes`,
      detail: k === "sentence_game" ? `${pct(base ? f.customers / base : null)} de los activos` : `${pct(base ? f.customers / base : null)} de los activos · ${int(f.volume)} ${meta.unit}`,
    }
  })

  const heat = WEEKDAYS.map((_, wi) => HOURS.map((h) => data.heatmap.find((c) => c.weekday === wi + 1 && c.hour === h)?.actions ?? 0))
  const heatMax = Math.max(1, ...heat.flat())
  const peak = data.heatmap.reduce<(typeof data.heatmap)[number] | null>((best, c) => (!best || c.actions > best.actions ? c : best), null)

  const screens = data.screens.map((s) => ({
    key: s.path ?? "?",
    label: SCREEN_LABELS[s.path ?? ""] ?? s.path ?? "Desconocida",
    value: s.views,
    display: int(s.views),
    detail: `${int(s.customers)} clientes`,
  }))

  return (
    <>
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-3 2xl:grid-cols-6">
        <StatTile label="Sesiones con el tutor" value={int(tutor.sessions)} hint={`De ${int(tutor.customers)} clientes`} />
        <StatTile label="Mensajes de alumnos" value={int(tutor.learner_turns)} hint="Turnos escritos al tutor" />
        <StatTile label="Mensajes por sesión" value={dec(tutor.avg_turns_per_session)} hint="Media de turnos del alumno" />
        <StatTile
          label="Duración de sesión"
          value={tutor.median_minutes != null ? `${dec(tutor.median_minutes)} min` : "—"}
          hint="Mediana, del inicio al último mensaje"
        />
        <StatTile label="Turnos corregidos" value={pct(tutor.correction_rate)} hint="El tutor corrigió algo en ese mensaje" />
        <StatTile
          label="Práctica guiada"
          value={pct(tutor.sessions ? (tutor.module_sessions + tutor.library_sessions) / tutor.sessions : null)}
          hint={`${int(tutor.module_sessions)} de módulo · ${int(tutor.library_sessions)} de biblioteca`}
        />
      </section>

      <section className="grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
        <div className="space-y-6">
          <ChartCard
            title="Uso por función"
            description="Cuántos clientes usaron cada parte de la app en el periodo, y cuánto."
            table={{
              columns: ["Función", "Clientes", "% de activos", "Volumen"],
              numeric: [1, 2, 3],
              rows: data.features.map((f) => [
                FEATURE_LABELS[f.feature]?.label ?? f.feature,
                int(f.customers),
                pct(base ? f.customers / base : null),
                `${int(f.volume)} ${FEATURE_LABELS[f.feature]?.unit ?? ""}`,
              ]),
            }}
          >
            <BarList items={features} />
            {appOpeners > 0 && (
              <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
                {int(appOpeners)} clientes abrieron la app en el periodo ({int(byFeature.get("app")?.volume ?? 0)} pantallas vistas).
              </p>
            )}
          </ChartCard>

          <ChartCard
            title="Pantallas más visitadas"
            description="Se registra desde hoy: cada vez que un alumno abre una sección de la app."
            table={{
              columns: ["Pantalla", "Visitas", "Clientes"],
              numeric: [1, 2],
              rows: data.screens.map((s) => [SCREEN_LABELS[s.path ?? ""] ?? s.path ?? "?", int(s.views), int(s.customers)]),
            }}
          >
            <BarList items={screens} emptyText="Todavía no hay visitas registradas en este periodo." />
          </ChartCard>
        </div>

        <ChartCard
          title="Errores que más corrige el tutor"
          description="Agrupados por la regla que explica el tutor. Es la lista de qué contenido reforzar primero."
          table={{
            columns: ["Regla", "Veces", "Clientes"],
            numeric: [1, 2],
            rows: data.top_corrections.map((c) => [c.rule, int(c.times), int(c.customers)]),
          }}
        >
          <BarList
            items={data.top_corrections.map((c) => ({
              key: c.rule,
              label: c.rule,
              value: c.times,
              display: int(c.times),
              detail: `${int(c.customers)} clientes distintos`,
            }))}
            emptyText="El tutor no ha corregido nada en este periodo."
          />
        </ChartCard>
      </section>

      <ChartCard
        title="Cuándo estudian"
        description={
          peak
            ? `Acciones de práctica por día y hora (hora local). El pico es el ${WEEKDAYS[peak.weekday - 1].toLowerCase()} a las ${peak.hour}:00: el mejor momento para recordatorios y novedades.`
            : "Acciones de práctica por día y hora (hora local)."
        }
        table={{
          columns: ["Día", ...HOURS.map((h) => `${h}h`)],
          numeric: HOURS.map((_, i) => i + 1),
          rows: WEEKDAYS.map((d, wi) => [d, ...heat[wi].map((v) => int(v))]),
        }}
      >
        <Heatmap
          rows={WEEKDAYS.map((d) => ({ key: d, label: d }))}
          columns={HOURS.map((h) => ({ key: String(h), label: String(h), showLabel: h % 3 === 0 }))}
          values={heat}
          scale={(v) => v / heatMax}
          formatValue={int}
          describe={(r, c, v) => {
            const cell = data.heatmap.find((x) => x.weekday === r + 1 && x.hour === c)
            return `${WEEKDAYS[r]} ${c}:00 — ${int(v)} acciones de ${int(cell?.customers ?? 0)} clientes`
          }}
          legend={["Menos", "Más"]}
        />
      </ChartCard>
    </>
  )
}
