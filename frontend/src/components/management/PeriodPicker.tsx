import { faCheck } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { PeriodDays } from "../../api/management"
import { PERIOD_OPTIONS } from "./usePeriod"

/** Selector de periodo: una fila de opciones fijas sobre todo lo que
 * filtra. Nadie necesita pelearse con un calendario para "últimos 30 días". */
export default function PeriodPicker({ value, onChange }: { value: PeriodDays; onChange: (d: PeriodDays) => void }) {
  return (
    <div role="radiogroup" aria-label="Periodo" className="inline-flex flex-wrap gap-1 rounded-full border border-slate-200 bg-white p-1">
      {PERIOD_OPTIONS.map((o) => {
        const selected = o.days === value
        return (
          <button
            key={o.days}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(o.days)}
            className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-semibold transition ${
              selected ? "bg-ink-900 text-white" : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {selected && <FontAwesomeIcon icon={faCheck} className="text-[11px]" />}
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
