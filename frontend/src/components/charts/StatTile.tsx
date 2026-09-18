import { faArrowDown, faArrowUp, faMinus } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { pct } from "./format"

/** Indicador: etiqueta, cifra grande y, si aplica, variación contra el
 * periodo anterior.
 *
 * El color de la variación depende de si SUBIR es bueno para esa cifra
 * (más clientes: bien; más churn: mal), y siempre va con flecha y texto:
 * el verde/rojo solo no lo distingue quien no ve esos colores. */
export default function StatTile({
  label,
  value,
  change,
  upIsGood = true,
  comparison,
  hint,
  emphasis = false,
}: {
  label: string
  value: string
  change?: number | null
  upIsGood?: boolean
  comparison?: string
  hint?: string
  emphasis?: boolean
}) {
  const hasChange = change !== undefined
  const direction = change == null || Math.abs(change) < 0.005 ? 0 : change > 0 ? 1 : -1
  const good = direction === 0 ? null : (direction > 0) === upIsGood
  const tone = good == null ? "text-slate-500" : good ? "text-emerald-700" : "text-rose-700"
  const icon = direction === 0 ? faMinus : direction > 0 ? faArrowUp : faArrowDown

  return (
    <div className={`flex min-w-0 flex-col rounded-3xl border p-5 shadow-sm ${emphasis ? "border-brand-200 bg-brand-50/60" : "border-slate-200 bg-white"}`}>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className={`mt-2 font-bold tracking-tight text-slate-900 ${emphasis ? "text-4xl sm:text-5xl" : "text-3xl"}`}>{value}</p>
      {hasChange && (
        <p className={`mt-2 flex items-center gap-1.5 text-xs font-semibold ${tone}`}>
          <FontAwesomeIcon icon={icon} className="text-[10px]" />
          {change == null ? "Sin base para comparar" : `${change > 0 ? "+" : ""}${pct(change)}`}
          {comparison && change != null && <span className="font-normal text-slate-400">{comparison}</span>}
        </p>
      )}
      {hint && <p className="mt-2 text-xs leading-relaxed text-slate-400">{hint}</p>}
    </div>
  )
}
