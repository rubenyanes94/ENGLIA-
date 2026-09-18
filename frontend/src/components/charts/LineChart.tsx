import { useState, type KeyboardEvent, type PointerEvent } from "react"
import { niceScale, xLabelIndices } from "./scale"
import { CHROME } from "./tokens"
import Tooltip from "./Tooltip"
import { useElementWidth } from "./useElementWidth"

export interface LineSeries {
  name: string
  color: string
}

const M = { top: 12, right: 16, bottom: 28, left: 44 }

/** Evolución en el tiempo, una o varias series sobre UN solo eje Y.
 *
 * - Una serie: línea + lavado de área al 10 % y su último valor rotulado.
 * - Varias: leyenda arriba (siempre, a partir de dos) y sin área.
 * - La cruz vertical busca la X más cercana al puntero: nadie apunta a
 *   una línea de 2 px. El tooltip lista TODAS las series en esa fecha.
 * - Con foco de teclado, ← y → recorren los puntos igual que el ratón.
 *
 * Nunca dos ejes Y: medidas de distinta escala van en gráficos distintos. */
export default function LineChart({
  data,
  series,
  formatValue,
  formatX,
  height = 220,
  partialLast = false,
}: {
  /** El último punto es un tramo que todavía no ha terminado (hoy, esta
   * semana): se dibuja atenuado y se rotula "en curso". Sin esto, la
   * bajada natural de un día a medias se lee como una caída real. */
  partialLast?: boolean
  data: { x: string; values: number[] }[]
  series: LineSeries[]
  formatValue: (n: number) => string
  formatX: (iso: string) => string
  height?: number
}) {
  const [ref, width] = useElementWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)

  const innerW = Math.max(10, width - M.left - M.right)
  const innerH = height - M.top - M.bottom
  const maxValue = Math.max(0, ...data.flatMap((d) => d.values))
  const { max, ticks } = niceScale(maxValue)
  const x = (i: number) => M.left + (data.length <= 1 ? innerW / 2 : (i / (data.length - 1)) * innerW)
  const y = (v: number) => M.top + innerH - (v / max) * innerH
  const labelled = xLabelIndices(data.length, Math.max(2, Math.floor(innerW / 90)))
  const single = series.length === 1

  function indexAt(clientX: number, rect: DOMRect) {
    const rel = clientX - rect.left - M.left
    const i = Math.round((rel / innerW) * (data.length - 1))
    return Math.max(0, Math.min(data.length - 1, i))
  }

  function onPointerMove(e: PointerEvent<SVGSVGElement>) {
    if (data.length) setHover(indexAt(e.clientX, e.currentTarget.getBoundingClientRect()))
  }

  function onKeyDown(e: KeyboardEvent<SVGSVGElement>) {
    if (!data.length) return
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault()
      const delta = e.key === "ArrowRight" ? 1 : -1
      setHover((h) => Math.max(0, Math.min(data.length - 1, (h ?? data.length - 1) + (h == null ? 0 : delta))))
    }
  }

  const last = data.length - 1

  return (
    <div>
      {!single && (
        <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
          {series.map((s) => (
            <li key={s.name} className="flex items-center gap-1.5">
              <span aria-hidden className="h-0.5 w-4 rounded-full" style={{ background: s.color }} />
              {s.name}
            </li>
          ))}
        </ul>
      )}
      <div ref={ref} className="relative w-full">
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`Gráfico de ${series.map((s) => s.name).join(", ")}. Usa las flechas para recorrerlo.`}
          tabIndex={0}
          onPointerMove={onPointerMove}
          onPointerLeave={() => setHover(null)}
          onFocus={() => setHover(last)}
          onBlur={() => setHover(null)}
          onKeyDown={onKeyDown}
          className="block touch-pan-y outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
        >
          {ticks.map((t) => (
            <g key={t}>
              <line x1={M.left} x2={M.left + innerW} y1={y(t)} y2={y(t)} stroke={t === 0 ? CHROME.axis : CHROME.grid} strokeWidth={1} />
              <text x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} fill={CHROME.muted} className="tabular-nums">
                {formatValue(t)}
              </text>
            </g>
          ))}
          {data.map((d, i) =>
            labelled.has(i) ? (
              <text key={d.x} x={x(i)} y={height - 8} textAnchor={i === last ? "end" : i === 0 ? "start" : "middle"} fontSize={11} fill={CHROME.muted}>
                {formatX(d.x)}
              </text>
            ) : null,
          )}

          {series.map((s, si) => {
            const points = data.map((d, i) => `${x(i)},${y(d.values[si] ?? 0)}`)
            const solid = partialLast && data.length > 1 ? points.slice(0, -1) : points
            return (
              <g key={s.name}>
                {single && data.length > 1 && (
                  <path
                    d={`M${x(0)},${y(0)} L${points.join(" L")} L${x(last)},${y(0)} Z`}
                    fill={s.color}
                    opacity={0.1}
                  />
                )}
                <polyline points={solid.join(" ")} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                {solid.length < points.length && (
                  <polyline points={points.slice(-2).join(" ")} fill="none" stroke={s.color} strokeOpacity={0.35} strokeWidth={2} strokeLinecap="round" />
                )}
              </g>
            )
          })}

          {/* Único rótulo directo: el valor más reciente de una serie sola. */}
          {single && data.length > 0 && hover == null && (
            <g>
              <circle cx={x(last)} cy={y(data[last].values[0])} r={4} fill={series[0].color} fillOpacity={partialLast ? 0.4 : 1} stroke={CHROME.surface} strokeWidth={2} />
            </g>
          )}

          {hover != null && data[hover] && (
            <g pointerEvents="none">
              <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={M.top + innerH} stroke={CHROME.axis} strokeWidth={1} />
              {series.map((s, si) => (
                <circle key={s.name} cx={x(hover)} cy={y(data[hover].values[si] ?? 0)} r={4} fill={s.color} stroke={CHROME.surface} strokeWidth={2} />
              ))}
            </g>
          )}
        </svg>
        {hover != null && data[hover] && (
          <Tooltip
            x={x(hover)}
            y={M.top}
            containerWidth={width}
            title={`${formatX(data[hover].x)}${partialLast && hover === last ? " (en curso)" : ""}`}
            rows={series.map((s, si) => ({ color: s.color, shape: "line", label: s.name, value: formatValue(data[hover].values[si] ?? 0) }))}
          />
        )}
      </div>
    </div>
  )
}
