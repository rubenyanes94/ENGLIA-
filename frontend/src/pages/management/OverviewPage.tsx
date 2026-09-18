import { faLightbulb } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { Overview } from "../../api/management"
import ChartCard from "../../components/charts/ChartCard"
import ColumnChart from "../../components/charts/ColumnChart"
import LineChart from "../../components/charts/LineChart"
import StatTile from "../../components/charts/StatTile"
import { change, dec, int, money, pct, shortDate } from "../../components/charts/format"
import { ACCENT } from "../../components/charts/tokens"
import PageShell from "../../components/management/PageShell"
import PeriodPicker from "../../components/management/PeriodPicker"
import { useManagementData } from "../../components/management/useManagementData"
import { usePeriod } from "../../components/management/usePeriod"

export default function OverviewPage() {
  const { days, comparison, setDays } = usePeriod(30)
  const { data, loading, error } = useManagementData<Overview>(`/management/overview?days=${days}`)
  const bucketWord = data?.period.bucket === "week" ? "semana" : "día"

  return (
    <PageShell
      title="Resumen"
      question="¿Cómo va el negocio? Clientes, uso e ingresos del periodo, contra el periodo anterior."
      filters={<PeriodPicker value={days} onChange={setDays} />}
      loading={loading}
      error={error}
      hasData={data != null}
    >
      {data && (
        <>
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              emphasis
              label="Ingreso mensual recurrente (MRR)"
              value={money(data.mrr_cents)}
              hint={`${int(data.paying_customers)} clientes de pago hoy`}
            />
            <StatTile
              label="Clientes activos"
              value={int(data.active_customers)}
              change={change(data.active_customers, data.active_customers_prev)}
              comparison={comparison}
              hint="Usaron la app al menos una vez en el periodo"
            />
            <StatTile
              label="Clientes nuevos"
              value={int(data.new_customers)}
              change={change(data.new_customers, data.new_customers_prev)}
              comparison={comparison}
            />
            <StatTile
              label="Ingresos cobrados"
              value={money(data.revenue_cents)}
              change={change(data.revenue_cents, data.revenue_prev_cents)}
              comparison={comparison}
              hint="Pagos aprobados en el periodo"
            />
          </section>

          <section className="grid grid-cols-2 gap-4 lg:grid-cols-3 2xl:grid-cols-6">
            <StatTile label="Activos hoy (DAU)" value={int(data.dau)} hint="Últimas 24 horas" />
            <StatTile label="Activos semana (WAU)" value={int(data.wau)} hint="Últimos 7 días" />
            <StatTile label="Activos mes (MAU)" value={int(data.mau)} hint="Últimos 30 días" />
            <StatTile
              label="Frecuencia (DAU/MAU)"
              value={pct(data.stickiness)}
              hint="Del mes, qué parte vuelve cada día"
            />
            <StatTile
              label="Activación"
              value={pct(data.activation_rate)}
              hint="Nuevos que practicaron en su primera semana"
            />
            <StatTile
              label="Conversión a pago"
              value={pct(data.paid_conversion)}
              hint={`ARPPU ${money(data.arppu_cents)}/mes`}
            />
          </section>

          <Insights data={data} />

          <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <ChartCard
              title={`Clientes activos por ${bucketWord}`}
              description={`Clientes distintos que usaron la app en cada tramo. El último ${bucketWord} aún está en curso.`}
              table={{
                columns: ["Fecha", "Clientes activos"],
                numeric: [1],
                rows: data.series.map((p) => [shortDate(p.bucket), int(p.active_customers)]),
              }}
            >
              <LineChart
                data={data.series.map((p) => ({ x: p.bucket, values: [p.active_customers] }))}
                series={[{ name: "Clientes activos", color: ACCENT }]}
                formatValue={int}
                formatX={shortDate}
                partialLast
              />
            </ChartCard>
            <ChartCard
              title={`Altas por ${bucketWord}`}
              description="Cuentas nuevas de alumnos. Aparte de los activos: son escalas distintas."
              table={{
                columns: ["Fecha", "Altas"],
                numeric: [1],
                rows: data.series.map((p) => [shortDate(p.bucket), int(p.signups)]),
              }}
            >
              <ColumnChart
                data={data.series.map((p) => ({ x: p.bucket, value: p.signups }))}
                label="Altas"
                formatValue={int}
                formatX={shortDate}
                partialLast
              />
            </ChartCard>
          </section>

          <p className="text-xs text-slate-400">
            {int(data.customers_total)} clientes en total. Cifras en hora de {data.period.timezone.replace("_", " ")}, del{" "}
            {shortDate(data.period.start)} al {shortDate(data.period.end)}; solo cuentan cuentas de alumno (gerencia y
            administración no se incluyen).
          </p>
        </>
      )}
    </PageShell>
  )
}

/** Lectura rápida: tres o cuatro frases con lo que un directivo tiene que
 * saber sin leer gráficos. Umbrales conservadores y dichos en el texto,
 * para que se pueda discrepar de ellos. */
function Insights({ data }: { data: Overview }) {
  const notes: string[] = []
  const activeChange = change(data.active_customers, data.active_customers_prev)

  if (activeChange != null) {
    notes.push(
      activeChange >= 0
        ? `El uso crece: ${int(data.active_customers)} clientes activos, ${pct(activeChange)} más que el periodo anterior.`
        : `El uso cae: ${int(data.active_customers)} clientes activos, ${pct(-activeChange)} menos que el periodo anterior.`,
    )
  }
  if (data.stickiness != null) {
    notes.push(
      data.stickiness >= 0.2
        ? `Frecuencia sana: el ${pct(data.stickiness)} de los activos del mes vuelve cada día (en apps de consumo, por encima del 20 % se considera buena).`
        : `Frecuencia baja: solo el ${pct(data.stickiness)} de los activos del mes vuelve cada día. Rachas y recordatorios diarios son la palanca típica.`,
    )
  }
  if (data.activation_rate != null && data.new_customers > 0) {
    notes.push(
      data.activation_rate >= 0.6
        ? `La primera semana funciona: el ${pct(data.activation_rate)} de los nuevos ya practicó.`
        : `Se pierden nuevos al empezar: solo el ${pct(data.activation_rate)} practicó en su primera semana. Revisar el registro y la primera sesión con el tutor.`,
    )
  }
  if (data.paying_customers > 0 && data.arppu_cents) {
    notes.push(
      `Cada cliente de pago deja ${money(data.arppu_cents)} al mes. Sobre ${int(data.customers_total)} clientes, cada punto más de conversión a pago son unos ${money(
        Math.round(data.customers_total * 0.01 * data.arppu_cents),
      )} más de MRR.`,
    )
  }
  if (notes.length === 0) return null

  return (
    <section className="rounded-3xl border border-brand-100 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
        <FontAwesomeIcon icon={faLightbulb} className="text-brand-600" />
        Lectura rápida
      </h2>
      <ul className="mt-3 grid gap-3 lg:grid-cols-2">
        {notes.map((n) => (
          <li key={n} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-600">
            {n}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-slate-400">DAU medio de 30 días: {dec(data.stickiness != null ? data.stickiness * data.mau : null)} clientes.</p>
    </section>
  )
}
