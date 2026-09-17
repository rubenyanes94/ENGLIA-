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
  const activeRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  // Marca de tiempo del último scroll hecho a mano por el alumno.
  const userScrolledAt = useRef(0)

  useEffect(() => {
    // Si el alumno acaba de desplazarse para releer algo, no se le
    // arrastra de vuelta: es lo que hace Spotify, y sin esto cada cambio
    // de frase le quitaría de delante lo que estaba leyendo.
    if (Date.now() - userScrolledAt.current < USER_SCROLL_GRACE_MS) return

    const node = activeRef.current
    const box = containerRef.current
    if (!node || !box) return
    // La frase activa se coloca en el tercio superior, no en el centro:
    // así se ve lo que viene justo después, que es lo que el ojo busca
    // al seguir una letra.
    const offset = node.offsetTop - box.clientHeight * ACTIVE_LINE_POSITION
    // Solo se mueve el contenedor, nunca la página: scrollIntoView
    // desplazaría la ventana entera y sacaría el reproductor de la vista.
    box.scrollTo({ top: Math.max(offset, 0), behavior: "smooth" })
  }, [activeIndex])

  const markUserScroll = () => {
    userScrolledAt.current = Date.now()
  }

  return (
    <div
      ref={containerRef}
      onWheel={markUserScroll}
      onTouchMove={markUserScroll}
      className="lyrics-scroll relative h-80 overflow-y-auto rounded-3xl bg-gradient-to-br from-brand-900 via-brand-950 to-ink-950 px-6 sm:h-96 sm:px-10"
    >
      {/* Relleno arriba y abajo para que la primera y la última frase
          también puedan subir a su sitio en vez de quedarse pegadas al
          borde, donde el degradado las taparía. */}
      <div className="space-y-4 py-28 sm:space-y-5">
        {lines.map((segment, index) => {
          const isActive = index === activeIndex
          const isPast = activeIndex >= 0 && index < activeIndex
          return (
            // La referencia va en la FILA, no en el botón de dentro. La
            // fila es hija directa del contenedor, así que su offsetTop se
            // mide contra él. Con la referencia en el botón, el offsetTop
            // se medía contra la fila y valía ~0 en todas: el panel no
            // seguía la frase que sonaba.
            <div
              key={index}
              ref={isActive ? activeRef : undefined}
              className="group/line flex items-center gap-3"
            >
              <button
                onClick={() => onSeek(segment.start)}
                // Cada frase se puede pulsar para oírla otra vez: es lo
                // que pide un alumno de idiomas ("repite esa"), y sin esto
                // tendría que buscarla a ciegas en la barra.
                title="Clic para repetir esta frase"
                className={[
                  "text-left text-2xl font-extrabold leading-snug tracking-tight transition-colors duration-500 sm:text-3xl",
                  lineColor(segment.english, isActive, isPast),
                ].join(" ")}
              >
                {segment.text}
              </button>

              {segment.english && onPractice && (
                <button
                  onClick={() => onPractice(segment.text)}
                  title="Repetir en voz alta y recibir corrección"
                  aria-label={`Practicar la pronunciación de ${segment.text}`}
                  // Solo visible al pasar el ratón o en la frase activa: un
                  // micrófono en cada línea convertiría la letra en una
                  // botonera y taparía lo que se está diciendo.
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-sm text-brand-200 transition hover:bg-white/20 hover:text-white ${
                    isActive ? "opacity-100" : "opacity-0 group-hover/line:opacity-100"
                  }`}
                >
                  <FontAwesomeIcon icon={faMicrophone} />
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** Tiempo que se respeta el scroll manual antes de volver a seguir la
 * frase activa. */
const USER_SCROLL_GRACE_MS = 3000

/** Altura (fracción del panel) a la que se coloca la frase activa. */
const ACTIVE_LINE_POSITION = 0.3

/** Color de una línea según su estado, como en la letra de Spotify: la
 * frase que suena en blanco pleno, lo ya dicho a media intensidad para
 * poder releerlo, y lo que viene tenue para que no compita.
 *
 * El inglés conserva su tono azul en los tres estados. Spotify pinta
 * todo igual, pero aquí distinguir la frase inglesa es lo que le dice al
 * alumno "esto es lo que tienes que repetir". */
function lineColor(english: boolean, active: boolean, past: boolean): string {
  if (active) return english ? "text-brand-300" : "text-white"
  if (past) return english ? "text-brand-300/50 hover:text-brand-300/80" : "text-white/50 hover:text-white/80"
  return english ? "text-brand-300/30 hover:text-brand-300/70" : "text-white/25 hover:text-white/70"
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
