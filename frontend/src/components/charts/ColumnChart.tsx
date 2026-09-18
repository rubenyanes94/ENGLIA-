import { useState } from "react"
import { niceScale, xLabelIndices } from "./scale"
import { ACCENT, CHROME } from "./tokens"
import Tooltip from "./Tooltip"
import { useElementWidth } from "./useElementWidth"

const M = { top: 12, right: 8, bottom: 28, left: 52 }

/** Columnas en el tiempo, una sola serie (p. ej. ingresos por día).
 * Columnas finas (≤ 24 px) con el extremo redondeado y la base recta; el
 * hueco entre ellas es aire, no un borde. Cada columna es su propio
 * objetivo de hover y de foco, con un área más ancha que la marca. */
export default function ColumnChart({
  data,
  label,
  formatValue,
  formatX,
  height = 220,
  color = ACCENT,
  partialLast = false,
}: {
  /** Última columna = tramo sin terminar: atenuada y rotulada "en curso". */
  partialLast?: boolean
  data: { x: string; value: number }[]
  label: string
  formatValue: (n: number) => string
  formatX: (iso: string) => string
  height?: number
  color?: string
}) {
  const [ref, width] = useElementWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)

  const innerW = Math.max(10, width - M.left - M.right)
  const innerH = height - M.top - M.bottom
  const { max, ticks } = niceScale(Math.max(0, ...data.map((d) => d.value)))
  const band = innerW / Math.max(1, data.length)
  const barW = Math.max(2, Math.min(24, band - 2))
  const y = (v: number) => M.top + innerH - (v / max) * innerH
  const labelled = xLabelIndices(data.length, Math.max(2, Math.floor(innerW / 90)))

  return (
    <div ref={ref} className="relative w-full">
      <svg width={width} height={height} role="img" aria-label={`Gráfico de columnas: ${label}`} className="block">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={M.left + innerW} y1={y(t)} y2={y(t)} stroke={t === 0 ? CHROME.axis : CHROME.grid} strokeWidth={1} />
            <text x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} fill={CHROME.muted} className="tabular-nums">
              {formatValue(t)}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const cx = M.left + band * i + band / 2
          const h = Math.max(0, innerH - (y(d.value) - M.top))
          const top = y(d.value)
          const r = Math.min(4, barW / 2, h)
          const x0 = cx - barW / 2
          const base = M.top + innerH
          return (
            <g key={d.x}>
              {h > 0 && (
                <path
                  d={`M${x0},${base} L${x0},${top + r} Q${x0},${top} ${x0 + r},${top} L${x0 + barW - r},${top} Q${x0 + barW},${top} ${x0 + barW},${top + r} L${x0 + barW},${base} Z`}
                  fill={color}
                  opacity={(hover == null || hover === i ? 1 : 0.55) * (partialLast && i === data.length - 1 ? 0.45 : 1)}
                />
              )}
              <rect
                x={M.left + band * i}
                y={M.top}
                width={band}
                height={innerH}
                fill="transparent"
                tabIndex={0}
                aria-label={`${formatX(d.x)}: ${formatValue(d.value)}`}
                onPointerEnter={() => setHover(i)}
                onPointerLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                className="outline-none"
              />
              {labelled.has(i) && (
                <text x={cx} y={height - 8} textAnchor={i === data.length - 1 ? "end" : "middle"} fontSize={11} fill={CHROME.muted}>
                  {formatX(d.x)}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      {hover != null && data[hover] && (
        <Tooltip
          x={M.left + band * hover + band / 2}
          y={M.top}
          containerWidth={width}
          title={`${formatX(data[hover].x)}${partialLast && hover === data.length - 1 ? " (en curso)" : ""}`}
          rows={[{ color, shape: "box", label, value: formatValue(data[hover].value) }]}
        />
      )}
    </div>
  )
}
