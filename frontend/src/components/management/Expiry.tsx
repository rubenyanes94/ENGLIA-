import { daysUntil, longDate } from "../charts/format"

/** Cuándo se le acaba el acceso a un cliente.
 *
 * Ojo con el día que se muestra: la suscripción vence a las 12:00 a. m.
 * DE ese día (ver backend/app/billing/period.py), así que ese día el
 * cliente ya NO entra — el último día completo es el anterior. Por eso
 * "Último día" aparece cuando falta 1, y no cuando falta 0.
 *
 * El color solo grita cuando hay algo que hacer: rojo si un cliente que
 * figura como activo ya venció (hay que cobrarle o se quedó fuera),
 * ámbar en la última semana. Una suscripción cancelada o vencida hace
 * meses es historia, no una alarma: va en gris.
 */
export default function Expiry({
  iso,
  status,
  now,
  compact = false,
}: {
  iso: string | null
  status: string
  now: string
  /** En las tarjetas de móvil: una sola línea, sin la fecha completa. */
  compact?: boolean
}) {
  if (!iso) return <span className="text-slate-400">—</span>

  const days = daysUntil(iso, now)
  const vencida = days <= 0
  const texto = vencida
    ? days === 0
      ? "Venció hoy"
      : days === -1
        ? "Venció ayer"
        : `Venció hace ${-days} días`
    : days === 1
      ? "Último día"
      : `En ${days} días`

  const tono =
    status !== "active" ? "text-slate-500" : vencida ? "text-rose-600" : days <= 7 ? "text-amber-600" : "text-slate-500"

  if (compact) {
    return (
      <span className={tono}>
        {longDate(iso)} · {texto.toLowerCase()}
      </span>
    )
  }
  return (
    <div>
      <p className="text-slate-700">{longDate(iso)}</p>
      <p className={`text-xs ${tono}`}>{texto}</p>
    </div>
  )
}
