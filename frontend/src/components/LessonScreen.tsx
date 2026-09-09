import { faMicrophone } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useMemo, useRef } from "react"
import type { ScriptSegment } from "../api/types"

/** La "pantalla" de la lección: en vez de un muro de texto estático
 * debajo del reproductor, el guión se va revelando conforme el tutor lo
 * dice, con la frase actual destacada.
 *
 * Por qué importa en una app de idiomas y no es solo estética: el alumno
 * de A1 no distingue todavía dónde acaba una palabra inglesa y empieza
 * la siguiente. Ver el texto EXACTO que está sonando en ese instante es
 * lo que convierte un sonido continuo en frases separables. Es el mismo
 * principio que subtitular en el idioma que estás aprendiendo.
 *
 * Los tiempos vienen del sintetizador (duración real de cada fragmento),
 * no de estimar por longitud: ver backend/app/media/wav.py.
 */
/** Parte los tramos largos en frases, repartiendo su tiempo de forma
 * proporcional a la longitud del texto.
 *
 * Hace falta porque el backend mide el tiempo REAL de cada fragmento, y
 * esos fragmentos los define el guión: entre dos frases inglesas puede
 * haber catorce segundos seguidos de español. Resaltar ese bloque entero
 * de golpe no es "lo que se está diciendo", es "el párrafo en el que
 * vamos".
 *
 * El reparto proporcional es fiable AQUÍ y no lo sería entre idiomas:
 * dentro de un tramo hay una sola voz a un solo ritmo, así que los
 * caracteres predicen bien el tiempo. Es justo la suposición que se
 * evitó al medir los tramos en el backend, donde sí cambia la voz.
 *
 * Los tramos en inglés NO se parten: son la unidad que el alumno tiene
 * que repetir entera.
 */
function splitIntoLines(segments: ScriptSegment[]): ScriptSegment[] {
  const lines: ScriptSegment[] = []

  for (const segment of segments) {
    const duration = segment.end - segment.start
    // Corta tras . ! ? … conservando el signo.
    const sentences = segment.english
      ? [segment.text]
      : segment.text.split(/(?<=[.!?…])\s+/).filter((piece) => piece.trim())

    if (sentences.length <= 1) {
      lines.push(segment)
      continue
    }

    const total = sentences.reduce((sum, piece) => sum + piece.length, 0)
    let cursor = segment.start
    sentences.forEach((piece, index) => {
      const share = (piece.length / total) * duration
      lines.push({
        text: piece,
        english: segment.english,
        start: cursor,
        // La última hereda el final medido, para que ningún redondeo
        // deje un hueco justo antes del siguiente fragmento real.
        end: index === sentences.length - 1 ? segment.end : cursor + share,
      })
      cursor += share
    })
  }

  return mergeOrphanPunctuation(lines)
}

/** Pega a la línea anterior los restos que son solo puntuación.
 *
 * Aparecen sin falta tras cada frase inglesa: el guión dice
 * "...decimos [[Good morning]]. Por la tarde..." y al extraer la marca
 * queda un "." suelto entre dos fragmentos. Sin esto, la pantalla pinta
 * una línea entera que contiene únicamente un punto — y llega a
 * destacarse como si fuera lo que el tutor está diciendo. Es el mismo
 * resto que en el backend hacía fallar la síntesis (ver
 * piper_tts._has_speakable_content); aquí no rompe nada, solo se ve mal. */
function mergeOrphanPunctuation(lines: ScriptSegment[]): ScriptSegment[] {
  const merged: ScriptSegment[] = []

  for (const line of lines) {
    const hasWords = /[\p{L}\p{N}]/u.test(line.text)
    const previous = merged[merged.length - 1]
    if (!hasWords && previous) {
      previous.text += line.text
      previous.end = line.end
      continue
    }
    merged.push({ ...line })
  }

  return merged
}

export default function LessonScreen({
  segments,
  currentTime,
  onSeek,
  onPractice,
}: {
  segments: ScriptSegment[]
  currentTime: number
  onSeek: (seconds: number) => void
  /** Practicar una frase inglesa en voz alta. Solo se ofrece sobre las
   * frases en inglés: pedirle al alumno que "repita" la explicación en
   * español no evalúa nada — su español ya es nativo. */
  onPractice?: (phrase: string) => void
}) {
  const lines = useMemo(() => splitIntoLines(segments), [segments])
  const activeIndex = findActiveIndex(lines, currentTime)
  const activeRef = useRef<HTMLButtonElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Solo se desplaza el contenedor, no la página: scrollIntoView movería
    // la ventana entera y le arrancaría el reproductor de la vista al
    // alumno cada vez que cambia de frase.
    const node = activeRef.current
    const box = containerRef.current
    if (!node || !box) return
    const offset = node.offsetTop - box.clientHeight / 2 + node.clientHeight / 2
    box.scrollTo({ top: Math.max(offset, 0), behavior: "smooth" })
  }, [activeIndex])

  return (
    <div
      ref={containerRef}
      className="relative h-52 overflow-y-auto rounded-2xl bg-slate-950/60 p-5 text-lg leading-relaxed sm:h-60 sm:p-6 sm:text-xl"
    >
      <div className="space-y-1">
        {lines.map((segment, index) => {
          const isActive = index === activeIndex
          const isPast = activeIndex >= 0 && index < activeIndex
          return (
            <span key={index} className="group/line relative flex items-start gap-1">
            <button
              ref={isActive ? activeRef : undefined}
              onClick={() => onSeek(segment.start)}
              // Cada frase es clicable para repetirla: es LA interacción
              // que pide un alumno de idiomas ("vuelve a decir esa"), y
              // sin ella tendría que buscarla a ciegas con la barra.
              title="Clic para repetir esta frase"
              className={[
                "block w-full rounded-lg px-2 py-0.5 text-left transition-colors duration-200",
                segment.english ? "font-semibold" : "",
                isActive
                  ? segment.english
                    ? "bg-blue-500/20 text-sky-200"
                    : "bg-white/10 text-white"
                  : isPast
                    ? segment.english
                      ? "text-sky-500/60"
                      : "text-slate-500"
                    : segment.english
                      ? "text-sky-400/40"
                      : "text-slate-600",
              ].join(" ")}
            >
              {segment.text}
            </button>
            {segment.english && onPractice && (
              <button
                onClick={() => onPractice(segment.text)}
                title="Repetir en voz alta y recibir corrección"
                aria-label={`Practicar la pronunciación de ${segment.text}`}
                // Solo visible al pasar por encima o en la frase activa:
                // un micrófono en cada línea a la vez convertiría la
                // pantalla en una botonera y taparía lo que se está
                // diciendo, que es para lo que existe.
                className={`mt-1 shrink-0 rounded-full p-1.5 text-[11px] text-sky-300 transition hover:bg-sky-500/20 hover:text-sky-200 ${
                  isActive ? "opacity-100" : "opacity-0 group-hover/line:opacity-100"
                }`}
              >
                <FontAwesomeIcon icon={faMicrophone} />
              </button>
            )}
            </span>
          )
        })}
      </div>

      {/* Degradado inferior: indica que hay más texto sin dibujar un
          borde duro que compita con la frase destacada. */}
      <div className="pointer-events-none sticky bottom-0 -mx-5 h-10 bg-gradient-to-t from-slate-950/80 to-transparent sm:-mx-6" />
    </div>
  )
}

/** Índice del fragmento que suena AHORA. Devuelve -1 antes de empezar.
 *
 * Se busca el último cuyo `start` ya pasó, en vez del que cumpla
 * start <= t < end: entre dos fragmentos hay microsilencios, y con la
 * condición estricta el texto parpadearía a "nada" en cada hueco. */
function findActiveIndex(segments: ScriptSegment[], time: number): number {
  let found = -1
  for (let i = 0; i < segments.length; i++) {
    if (segments[i].start <= time + 0.05) found = i
    else break
  }
  return found
}
