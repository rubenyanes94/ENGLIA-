import { useState } from "react"
import { ACCENT } from "./tokens"

export interface BarItem {
  key: string
  label: string
  value: number
  /** El valor ya formateado que se rotula en la punta de la barra. */
  display: string
  /** Contexto secundario (p. ej. "38 clientes"), visible bajo la etiqueta. */
  detail?: string
}

/** Barras horizontales de UNA serie: categorías sin orden propio
 * (pasarelas, pantallas, reglas de gramática). Todas del mismo color: la
 * longitud ya dice cuál es mayor, colorearlas distinto solo añadiría ruido.
 *
 * Barra fina, extremo redondeado y base recta, valor en la punta en color
 * de texto (nunca del color de la barra). Horizontal porque las etiquetas
 * son largas y así se leen enteras, también en un móvil. */
export default function BarList({ items, color = ACCENT, emptyText = "Sin datos en este periodo." }: { items: BarItem[]; color?: string; emptyText?: string }) {
  const [active, setActive] = useState<string | null>(null)
  const max = Math.max(0, ...items.map((i) => i.value))

  if (items.length === 0) return <p className="py-8 text-center text-sm text-slate-400">{emptyText}</p>

  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const w = max > 0 ? (item.value / max) * 100 : 0
        const dim = active != null && active !== item.key
        return (
          <li
            key={item.key}
            tabIndex={0}
            onPointerEnter={() => setActive(item.key)}
            onPointerLeave={() => setActive(null)}
            onFocus={() => setActive(item.key)}
            onBlur={() => setActive(null)}
            className="rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 text-sm text-slate-700">{item.label}</span>
              <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-900">{item.display}</span>
            </div>
            <div className="mt-1.5 flex items-center gap-3">
              <div className="h-2.5 flex-1">
                <div
                  className="h-full rounded-r transition-opacity"
                  style={{ width: `${Math.max(w, item.value > 0 ? 1 : 0)}%`, background: color, opacity: dim ? 0.45 : 1 }}
                />
              </div>
            </div>
            {item.detail && <p className="mt-1 text-xs text-slate-400">{item.detail}</p>}
          </li>
        )
      })}
    </ul>
  )
}
