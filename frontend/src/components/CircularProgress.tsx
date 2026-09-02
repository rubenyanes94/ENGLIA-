interface Props {
  percentage: number
  size?: number
  strokeWidth?: number
  trackColor?: string
  progressColor?: string
}

/** Anillo de progreso en SVG puro (sin librería) — usado en la tarjeta de
 * nivel del dashboard. `percentage` se recorta a [0, 100] a propósito:
 * un progreso "certificado" nunca debería pasar de 100, pero si algún
 * cálculo del backend lo hiciera por redondeo, esto evita un anillo roto. */
export default function CircularProgress({
  percentage,
  size = 64,
  strokeWidth = 6,
  trackColor = "rgba(255,255,255,0.25)",
  progressColor = "white",
}: Props) {
  const clamped = Math.max(0, Math.min(100, percentage))
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clamped / 100) * circumference

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={trackColor} strokeWidth={strokeWidth} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={progressColor}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white">
        {Math.round(clamped)}%
      </span>
    </div>
  )
}
