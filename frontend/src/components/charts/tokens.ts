/** Colores de los gráficos del panel de gerencia.
 *
 * NO son elegidos a ojo: cada lista pasó el validador de la guía de
 * visualización (bandas de luminosidad, croma mínimo, separación bajo
 * daltonismo protan/deutan y contraste) contra el fondo blanco de las
 * tarjetas. Si se cambia un solo hex hay que volver a validarlo.
 *
 * La app solo tiene modo claro (no hay ni un `dark:` en el código), así
 * que aquí tampoco hay variante oscura. */

/** Series distintas (identidad), SIEMPRE en este orden y sin reciclar.
 * El 1 es el violeta de la marca (brand-600). Aqua y amarillo quedan por
 * debajo de 3:1 contra blanco: por eso cada gráfico lleva etiquetas
 * visibles y vista de tabla. */
export const SERIES = ["#6D3BE6", "#eb6834", "#1baf7a", "#eda100"] as const

/** Un solo color cuando solo hay una serie (barras de categorías sin
 * orden: pasarelas, pantallas, reglas). Colorear cada barra distinto
 * gastaría el color en repetir lo que ya dice la longitud. */
export const ACCENT = SERIES[0]

/** Etapas ordenadas (embudo): un solo tono, de oscuro a claro. Validada
 * como rampa ordinal: el paso más claro aún supera 2:1 sobre blanco. Con
 * 6 pasos dos quedaban demasiado juntos, de ahí 5 (= 5 etapas). */
export const ORDINAL = ["#241254", "#4B25A5", "#6D3BE6", "#8559F4", "#A184FB"] as const

/** Magnitud continua (mapas de calor): la paleta brand de claro a oscuro. */
export const SEQUENTIAL = [
  "#F5F2FF", "#EDE7FF", "#DCD1FF", "#C2B0FF", "#A184FB",
  "#8559F4", "#6D3BE6", "#5B2CCB", "#4B25A5", "#3D2184",
] as const

/** Gris de "lo demás" cuando se resalta una sola cosa. */
export const DEEMPHASIS = "#cbd5e1"

export const CHROME = {
  grid: "#e2e8f0", // slate-200: líneas de guía, finas y sólidas
  axis: "#cbd5e1", // slate-300: línea base
  muted: "#64748b", // slate-500: texto de ejes
  ink: "#0f172a", // slate-900
  surface: "#ffffff",
}

/** Estado (bueno / aviso / grave / crítico). Reservado: nunca se usa
 * como "serie 4", y siempre va con icono y texto, no solo color. */
export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
}

/** Color del paso de la rampa secuencial para un valor 0..1. */
export function sequentialColor(fraction: number): string {
  const i = Math.max(0, Math.min(SEQUENTIAL.length - 1, Math.round(fraction * (SEQUENTIAL.length - 1))))
  return SEQUENTIAL[i]
}

/** Texto blanco o tinta sobre un relleno, según su luminancia: el único
 * caso en que un texto va DENTRO de una marca de color. */
export function inkOn(hex: string): string {
  const n = parseInt(hex.slice(1), 16)
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  })
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return luminance > 0.4 ? CHROME.ink : "#ffffff"
}
