/** Escala Y "limpia": máximo y marcas en números redondos (0 / 50 / 100),
 * nunca 0 / 37 / 74. Devuelve el tope del eje y las marcas. */
export function niceScale(maxValue: number, tickCount = 4): { max: number; ticks: number[] } {
  if (maxValue <= 0) return { max: 1, ticks: [0, 1] }
  const rough = maxValue / tickCount
  const magnitude = 10 ** Math.floor(Math.log10(rough))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? 10 * magnitude
  const max = Math.ceil(maxValue / step) * step
  const ticks: number[] = []
  for (let v = 0; v <= max + step / 2; v += step) ticks.push(Math.round(v * 1e6) / 1e6)
  return { max, ticks }
}

/** Qué índices del eje X llevan etiqueta: como mucho `max`, repartidas,
 * y siempre la última (el dato más reciente es el que más se mira). */
export function xLabelIndices(length: number, max: number): Set<number> {
  if (length <= max) return new Set(Array.from({ length }, (_, i) => i))
  const step = Math.ceil(length / max)
  const out = new Set<number>()
  for (let i = length - 1; i >= 0; i -= step) out.add(i)
  return out
}
