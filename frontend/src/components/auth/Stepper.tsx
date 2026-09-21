import { faCheck } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"

/** "1 Tu cuenta → 2 Tu suscripción": que el alumno sepa desde el primer
 * campo que después viene el pago, y cuánto le falta. */
export default function Stepper({ current }: { current: 1 | 2 }) {
  const steps = ["Tu cuenta", "Tu suscripción"]
  return (
    <ol className="mb-5 flex items-center gap-2 text-xs font-semibold" aria-label="Pasos del registro">
      {steps.map((label, i) => {
        const n = i + 1
        const done = n < current
        const active = n === current
        return (
          <li key={label} className="flex items-center gap-2" aria-current={active ? "step" : undefined}>
            {i > 0 && <span aria-hidden className={`h-px w-6 ${done || active ? "bg-brand-300" : "bg-slate-200"}`} />}
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full ${
                done ? "bg-brand-600 text-white" : active ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? <FontAwesomeIcon icon={faCheck} className="text-[10px]" /> : n}
            </span>
            <span className={active ? "text-slate-900" : "text-slate-400"}>{label}</span>
          </li>
        )
      })}
    </ol>
  )
}
