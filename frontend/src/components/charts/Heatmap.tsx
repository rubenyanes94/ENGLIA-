import { useState, type ReactNode } from "react"
import { SEQUENTIAL, inkOn, sequentialColor } from "./tokens"

export interface HeatmapProps {
  rows: { key: string; label: string; sub?: string }[]
  columns: { key: string; label: string; showLabel?: boolean }[]
  /** values[fila][columna]. null = la celda no aplica (p. ej. una semana
   * que todavía no ha pasado) y se deja en blanco, no como cero. */
  values: (number | null)[][]
  /** Posición 0..1 del valor en la escala de color. */
  scale: (v: number) => number
  /** Rotular el valor dentro de la celda (matriz de cohortes: sí; mapa
   * de horas: no, serían 168 números que nadie lee). */
  showValues?: boolean
  formatValue: (v: number) => string
  describe: (row: number, col: number, v: number) => string
  legend: [string, string]
  minCell?: number
}

/** Rejilla de magnitud con rampa secuencial de un solo tono. Celdas
 * separadas por 2 px de fondo, no por bordes. Pasar el ratón o el foco
 * por una celda escribe su lectura completa debajo (aria-live), así el
 * valor exacto nunca depende de adivinar un tono. */
export default function Heatmap({ rows, columns, values, scale, showValues = false, formatValue, describe, legend, minCell = 18 }: HeatmapProps) {
  const [active, setActive] = useState<[number, number] | null>(null)
  const readout = active && values[active[0]]?.[active[1]] != null ? describe(active[0], active[1], values[active[0]][active[1]] as number) : null

  return (
    <div>
      <div className="overflow-x-auto pb-1">
        <div
          className="grid gap-[2px]"
          style={{ gridTemplateColumns: `minmax(5.5rem, max-content) repeat(${columns.length}, minmax(${minCell}px, 1fr))`, minWidth: `${88 + columns.length * (minCell + 2)}px` }}
        >
          <div />
          {columns.map((c) => (
            <div key={c.key} className="pb-1 text-center text-[10px] font-medium text-slate-400">
              {c.showLabel === false ? "" : c.label}
            </div>
          ))}
          {rows.map((r, ri) => (
            <Row key={r.key} label={r.label} sub={r.sub}>
              {columns.map((c, ci) => {
                const v = values[ri]?.[ci]
                if (v == null) return <div key={c.key} className="rounded-sm bg-white" style={{ minHeight: minCell }} />
                const bg = sequentialColor(scale(v))
                const isActive = active?.[0] === ri && active?.[1] === ci
                return (
                  <div
                    key={c.key}
                    tabIndex={0}
                    role="gridcell"
                    aria-label={describe(ri, ci, v)}
                    onPointerEnter={() => setActive([ri, ci])}
                    onPointerLeave={() => setActive(null)}
                    onFocus={() => setActive([ri, ci])}
                    onBlur={() => setActive(null)}
                    className={`flex items-center justify-center rounded-sm text-[10px] font-semibold tabular-nums outline-none ${isActive ? "ring-2 ring-slate-900 ring-offset-1" : ""}`}
                    style={{ background: bg, color: inkOn(bg), minHeight: minCell }}
                  >
                    {showValues ? formatValue(v) : ""}
                  </div>
                )
              })}
            </Row>
          ))}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p aria-live="polite" className="min-h-[1.25rem] text-xs text-slate-600">
          {readout ?? <span className="text-slate-400">Pasa el ratón o el foco por una celda para ver su valor.</span>}
        </p>
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          {legend[0]}
          <span aria-hidden className="flex h-2.5 w-24 overflow-hidden rounded-sm">
            {SEQUENTIAL.map((c) => (
              <span key={c} className="flex-1" style={{ background: c }} />
            ))}
          </span>
          {legend[1]}
        </div>
      </div>
    </div>
  )
}

function Row({ label, sub, children }: { label: string; sub?: string; children: ReactNode }) {
  return (
    <>
      <div className="flex flex-col justify-center pr-2 text-xs leading-tight">
        <span className="font-medium text-slate-700">{label}</span>
        {sub && <span className="text-[10px] text-slate-400">{sub}</span>}
      </div>
      {children}
    </>
  )
}
