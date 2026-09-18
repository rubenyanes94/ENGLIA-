import type { ReactNode } from "react"

export interface TooltipRow {
  color?: string
  /** "line" para series de líneas, "box" para barras/celdas: la clave
   * imita la marca, como pide la guía. */
  shape?: "line" | "box"
  label: string
  value: string
}

/** Recuadro flotante. El VALOR va en negrita y primero; el nombre de la
 * serie, detrás y en gris: quien pasa el ratón ya sabe qué serie es y
 * busca la cifra. */
export default function Tooltip({
  x,
  y,
  containerWidth,
  title,
  rows,
  footer,
}: {
  x: number
  y: number
  containerWidth: number
  title: string
  rows: TooltipRow[]
  footer?: ReactNode
}) {
  // Se abre hacia el lado con sitio, para no salirse de la tarjeta.
  const flip = x > containerWidth - 200
  return (
    <div
      role="status"
      className="pointer-events-none absolute z-10 min-w-[10rem] rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg"
      style={{ left: flip ? undefined : x + 12, right: flip ? containerWidth - x + 12 : undefined, top: Math.max(0, y - 8) }}
    >
      <p className="mb-1 font-semibold text-slate-500">{title}</p>
      {rows.map((r) => (
        <p key={r.label} className="flex items-center gap-2 py-0.5">
          {r.color && (
            <span
              aria-hidden
              className={r.shape === "box" ? "h-2.5 w-2.5 rounded-sm" : "h-0.5 w-3 rounded-full"}
              style={{ background: r.color }}
            />
          )}
          <span className="font-bold tabular-nums text-slate-900">{r.value}</span>
          <span className="text-slate-500">{r.label}</span>
        </p>
      ))}
      {footer && <div className="mt-1 border-t border-slate-100 pt-1 text-slate-400">{footer}</div>}
    </div>
  )
}
