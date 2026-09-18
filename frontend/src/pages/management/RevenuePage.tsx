import { faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { Revenue } from "../../api/management"
import BarList from "../../components/charts/BarList"
import ChartCard from "../../components/charts/ChartCard"
import ColumnChart from "../../components/charts/ColumnChart"
import StatTile from "../../components/charts/StatTile"
import { change, int, money, pct, shortDate } from "../../components/charts/format"
import { STATUS } from "../../components/charts/tokens"
import { PAYMENT_STATUS, PROVIDER_LABELS, SUBSCRIPTION_LABELS } from "../../components/management/labels"
import PageShell from "../../components/management/PageShell"
import PeriodPicker from "../../components/management/PeriodPicker"
import { useManagementData } from "../../components/management/useManagementData"
import { usePeriod } from "../../components/management/usePeriod"

const SUB_ORDER = ["active", "past_due", "pending", "canceled", "expired"]

export default function RevenuePage() {
  const { days, comparison, setDays } = usePeriod(90)
  const { data, loading, error } = useManagementData<Revenue>(`/management/revenue?days=${days}`)

  return (
    <PageShell
      title="Ingresos"
      question="¿Cuánto entra, por dónde, cuánto se pierde y cuánto vale un cliente?"
      filters={<PeriodPicker value={days} onChange={setDays} />}
      loading={loading}
      error={error}
      hasData={data != null}
    >
      {data && <RevenueBody data={data} comparison={comparison} />}
    </PageShell>
  )
}

function RevenueBody({ data, comparison }: { data: Revenue; comparison: string }) {
  const bucketWord = data.period.bucket === "week" ? "semana" : "día"
  const subsTotal = Object.values(data.subscriptions_by_status).reduce((a, b) => a + b, 0)

  return (
    <>
      {data.pending_verification > 0 && (
        <p className="flex flex-wrap items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <FontAwesomeIcon icon={faTriangleExclamation} style={{ color: STATUS.warning }} />
          <strong>{int(data.pending_verification)} pagos por verificar</strong>
          ({money(data.pending_verification_cents)}). Son sobre todo de Pago Móvil y los aprueba administración desde su panel: mientras
          tanto, esos clientes no tienen acceso.
        </p>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile emphasis label="MRR" value={money(data.mrr_cents)} hint={`${int(data.paying_customers)} clientes de pago`} />
        <StatTile
          label="Ingresos cobrados"
          value={money(data.revenue_cents)}
          change={change(data.revenue_cents, data.revenue_prev_cents)}
          comparison={comparison}
        />
        <StatTile label="ARPPU" value={money(data.arppu_cents, true)} hint="Ingreso mensual medio por cliente de pago" />
        <StatTile label="Conversión a pago" value={pct(data.paid_conversion)} hint="Clientes que han pagado alguna vez" />
      </section>

      <section className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatTile
          label="Churn del periodo"
          value={pct(data.churn_rate)}
          hint={`${int(data.churned_in_period)} bajas de ${int(data.subscribers_at_start + data.new_subscribers)} suscripciones vivas en el periodo`}
        />
        <StatTile
          label="LTV estimado"
          value={money(data.ltv_cents)}
          hint="ARPPU ÷ churn mensual. Estimación: con pocas bajas medidas, varía mucho."
        />
        <StatTile label="Suscripciones activas" value={int(data.subscriptions_by_status.active ?? 0)} />
        <StatTile label="Cobro atrasado" value={int(data.subscriptions_by_status.past_due ?? 0)} hint="La pasarela avisó de un cobro fallido" />
      </section>

      <ChartCard
        title={`Ingresos por ${bucketWord}`}
        description="Pagos aprobados, en dólares."
        table={{
          columns: ["Fecha", "Ingresos"],
          numeric: [1],
          rows: data.series.map((p) => [shortDate(p.bucket), money(p.revenue_cents)]),
        }}
      >
        <ColumnChart
          data={data.series.map((p) => ({ x: p.bucket, value: p.revenue_cents / 100 }))}
          label="Ingresos"
          formatValue={(v) => money(v * 100)}
          formatX={shortDate}
          partialLast
        />
      </ChartCard>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <ChartCard
          title="Por pasarela"
          description="Cobros aprobados en el periodo."
          table={{
            columns: ["Pasarela", "Pagos", "Importe"],
            numeric: [1, 2],
            rows: data.by_provider.map((p) => [PROVIDER_LABELS[p.provider] ?? p.provider, int(p.payments), money(p.amount_cents)]),
          }}
        >
          <BarList
            items={data.by_provider.map((p) => ({
              key: p.provider,
              label: PROVIDER_LABELS[p.provider] ?? p.provider,
              value: p.amount_cents,
              display: money(p.amount_cents),
              detail: `${int(p.payments)} pagos · ${pct(data.revenue_cents ? p.amount_cents / data.revenue_cents : null)} del total`,
            }))}
          />
        </ChartCard>

        <ChartCard
          title="Estado de los pagos"
          description="Todos los intentos de pago del periodo."
          table={{
            columns: ["Estado", "Pagos", "Importe"],
            numeric: [1, 2],
            rows: data.by_status.map((s) => [PAYMENT_STATUS[s.status]?.label ?? s.status, int(s.payments), money(s.amount_cents)]),
          }}
        >
          <ul className="space-y-3">
            {data.by_status.map((s) => {
              const meta = PAYMENT_STATUS[s.status]
              return (
                <li key={s.status} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    {meta && <FontAwesomeIcon icon={meta.icon} style={{ color: meta.color }} />}
                    {meta?.label ?? s.status}
                  </span>
                  <span className="text-right text-sm tabular-nums">
                    <span className="font-semibold text-slate-900">{int(s.payments)}</span>
                    <span className="ml-2 text-slate-500">{money(s.amount_cents)}</span>
                  </span>
                </li>
              )
            })}
            {data.by_status.length === 0 && <p className="py-8 text-center text-sm text-slate-400">Sin pagos en este periodo.</p>}
          </ul>
        </ChartCard>

        <ChartCard
          title="Suscripciones por estado"
          description="Toda la historia, estado actual."
          table={{
            columns: ["Estado", "Suscripciones"],
            numeric: [1],
            rows: SUB_ORDER.filter((s) => data.subscriptions_by_status[s]).map((s) => [SUBSCRIPTION_LABELS[s], int(data.subscriptions_by_status[s])]),
          }}
        >
          <BarList
            items={SUB_ORDER.filter((s) => data.subscriptions_by_status[s]).map((s) => ({
              key: s,
              label: SUBSCRIPTION_LABELS[s] ?? s,
              value: data.subscriptions_by_status[s],
              display: int(data.subscriptions_by_status[s]),
              detail: pct(subsTotal ? data.subscriptions_by_status[s] / subsTotal : null),
            }))}
            emptyText="Todavía no hay suscripciones."
          />
        </ChartCard>
      </section>
    </>
  )
}
