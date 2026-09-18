import { useSearchParams } from "react-router-dom"
import type { PeriodDays } from "../../api/management"

export const PERIOD_OPTIONS: { days: PeriodDays; label: string; comparison: string }[] = [
  { days: 7, label: "7 días", comparison: "vs 7 días anteriores" },
  { days: 30, label: "30 días", comparison: "vs 30 días anteriores" },
  { days: 90, label: "90 días", comparison: "vs 90 días anteriores" },
  { days: 365, label: "12 meses", comparison: "vs 12 meses anteriores" },
]

/** El periodo vive en la URL (?periodo=30) y no en un estado de React:
 * así se conserva al cambiar de pestaña, sobrevive a recargar y se puede
 * mandar el enlace exacto de lo que se está mirando. */
export function usePeriod(fallback: PeriodDays) {
  const [params, setParams] = useSearchParams()
  const raw = Number(params.get("periodo"))
  const option = PERIOD_OPTIONS.find((o) => o.days === raw) ?? PERIOD_OPTIONS.find((o) => o.days === fallback)!

  function setDays(days: PeriodDays) {
    const next = new URLSearchParams(params)
    next.set("periodo", String(days))
    setParams(next, { replace: true })
  }

  return { days: option.days, comparison: option.comparison, setDays }
}
