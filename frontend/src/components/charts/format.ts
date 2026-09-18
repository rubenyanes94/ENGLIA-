/** Formato de cifras del panel. Español de Venezuela: punto de miles,
 * coma decimal. Una sola fuente para que la misma cifra se lea igual en
 * una tarjeta, un gráfico y su tabla. */

const LOCALE = "es-VE"

const intFmt = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 })
const decFmt = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 })
const compactFmt = new Intl.NumberFormat(LOCALE, { notation: "compact", maximumFractionDigits: 1 })
// narrowSymbol: "$210" en vez del "USD 210" que da es-VE por defecto.
const usdFmt = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "USD", currencyDisplay: "narrowSymbol", maximumFractionDigits: 0 })
const usdCentsFmt = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "USD", currencyDisplay: "narrowSymbol", minimumFractionDigits: 2 })

export const NO_DATA = "—"

export function int(n: number | null | undefined): string {
  return n == null ? NO_DATA : intFmt.format(n)
}

export function dec(n: number | null | undefined): string {
  return n == null ? NO_DATA : decFmt.format(n)
}

/** 12.900 → "12,9 mil". Solo para valores grandes que no caben. */
export function compact(n: number | null | undefined): string {
  if (n == null) return NO_DATA
  return Math.abs(n) < 10000 ? intFmt.format(n) : compactFmt.format(n)
}

/** Fracción 0-1 → "12 %"; con un decimal por debajo del 10 %, donde el
 * redondeo a entero borraría diferencias que importan (2 % vs 2,4 %). */
export function pct(fraction: number | null | undefined): string {
  if (fraction == null) return NO_DATA
  const v = fraction * 100
  return `${v < 10 ? decFmt.format(v) : intFmt.format(v)} %`
}

export function money(cents: number | null | undefined, withCents = false): string {
  if (cents == null) return NO_DATA
  return (withCents ? usdCentsFmt : usdFmt).format(cents / 100)
}

/** Las fechas del backend llegan en hora local del negocio y SIN zona
 * ("2026-09-18T11:00:00"). new Date() las leería como hora local del
 * NAVEGADOR, que puede ser otra: se parsean a mano para no moverlas. */
export function parseLocal(iso: string): Date {
  const [d, t = "00:00:00"] = iso.split("T")
  const [y, m, day] = d.split("-").map(Number)
  const [hh, mm, ss] = t.split(":").map((x) => Number(x.split(".")[0]))
  return new Date(y, m - 1, day, hh || 0, mm || 0, ss || 0)
}

const dayMonth = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short" })
const dayMonthYear = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", year: "numeric" })
const dateTime = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })

export function shortDate(iso: string | null | undefined): string {
  return iso ? dayMonth.format(parseLocal(iso)) : NO_DATA
}

export function longDate(iso: string | null | undefined): string {
  return iso ? dayMonthYear.format(parseLocal(iso)) : NO_DATA
}

export function dateAndTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(parseLocal(iso)) : NO_DATA
}

/** "hace 3 días" frente a la hora del negocio de la respuesta. */
export function relativeDays(iso: string | null | undefined, nowIso: string): string {
  if (!iso) return "Nunca"
  const days = Math.floor((parseLocal(nowIso).getTime() - parseLocal(iso).getTime()) / 86_400_000)
  if (days <= 0) return "Hoy"
  if (days === 1) return "Ayer"
  if (days < 30) return `Hace ${days} días`
  const months = Math.floor(days / 30)
  return months === 1 ? "Hace 1 mes" : `Hace ${months} meses`
}

/** Variación relativa entre dos periodos; null si el anterior es 0
 * (de 0 a 5 no es "+∞ %", es "sin base para comparar"). */
export function change(current: number, previous: number): number | null {
  return previous ? (current - previous) / previous : null
}

/** Duración de una llamada: "350 ms" por debajo de un segundo, "1,2 s" por encima. */
export function duration(ms: number | null | undefined): string {
  if (ms == null) return NO_DATA
  return ms < 1000 ? `${intFmt.format(Math.round(ms))} ms` : `${decFmt.format(ms / 1000)} s`
}

const hourMinute = new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit" })
const dayHourMinute = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })

/** Eje X de las series técnicas: la hora si la ventana cabe en un día,
 * día + hora si abarca varios, y solo el día a partir de un mes. */
export function bucketLabel(iso: string, hours: number): string {
  const d = parseLocal(iso)
  if (hours <= 24) return hourMinute.format(d)
  if (hours <= 168) return dayHourMinute.format(d)
  return dayMonth.format(d)
}

/** "hace 12 s" / "hace 3 min" para la marca de "actualizado". */
export function agoShort(date: Date, now: Date): string {
  const s = Math.max(0, Math.round((now.getTime() - date.getTime()) / 1000))
  if (s < 60) return `hace ${s} s`
  return `hace ${Math.floor(s / 60)} min`
}

