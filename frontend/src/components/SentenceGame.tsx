import {
  faArrowRight,
  faBolt,
  faCircleCheck,
  faCircleXmark,
  faFire,
  faPuzzlePiece,
  faRotateRight,
  faSpinner,
  faTrophy,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useCallback, useEffect, useRef, useState } from "react"
import { api } from "../api/client"
import type { GameAnswer, GameItem, GameNext, GameState } from "../api/types"
import { ApiError } from "../api/types"

/** Juego de completar oraciones del inicio.
 *
 * La dificultad la decide el servidor: empieza con el verbo to be y sube
 * un nivel cada cinco aciertos, hasta condicionales y voz pasiva. Aquí
 * solo se pinta y se responde; la corrección también es del servidor, así
 * que la respuesta correcta no llega al navegador antes de contestar.
 */
export default function SentenceGame({ onStateChange }: { onStateChange?: (state: GameState) => void }) {
  const [item, setItem] = useState<GameItem | null>(null)
  const [state, setState] = useState<GameState | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)
  const [result, setResult] = useState<GameAnswer | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // El callback de la página se guarda en una referencia y no como
  // dependencia: si la página pasa una función en línea, cambia en cada
  // render, arrastra a `loadNext` y el efecto de carga pediría oraciones
  // al servidor en bucle.
  const onStateChangeRef = useRef(onStateChange)
  useEffect(() => {
    onStateChangeRef.current = onStateChange
  })

  const applyState = useCallback((next: GameState) => {
    setState(next)
    onStateChangeRef.current?.(next)
  }, [])

  const loadNext = useCallback(async () => {
    setBusy(true)
    setError(null)
    setChosen(null)
    setResult(null)
    try {
      const data = await api.post<GameNext>("/game/sentences/next")
      setItem(data.item)
      applyState(data.state)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la oración.")
    } finally {
      setBusy(false)
    }
  }, [applyState])

  useEffect(() => {
    void loadNext()
  }, [loadNext])

  const answer = useCallback(
    async (option: string) => {
      if (!item || result || busy) return
      setChosen(option)
      setBusy(true)
      try {
        const data = await api.post<GameAnswer>("/game/sentences/answer", { item_id: item.id, answer: option })
        setResult(data)
        applyState(data.state)
      } catch (err) {
        // 409: la oración ya no estaba pendiente (se respondió en otra
        // pestaña). No es un error del alumno: se pasa a la siguiente.
        if (err instanceof ApiError && err.status === 409) {
          await loadNext()
          return
        }
        setChosen(null)
        setError(err instanceof ApiError ? err.message : "No se pudo enviar tu respuesta.")
      } finally {
        setBusy(false)
      }
    },
    [item, result, busy, applyState, loadNext],
  )

  // Atajos de teclado en escritorio: 1-4 responde, Enter pasa a la siguiente.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return
      if (!result && item && ["1", "2", "3", "4"].includes(event.key)) {
        const option = item.options[Number(event.key) - 1]
        if (option) void answer(option)
      } else if (result && event.key === "Enter") {
        void loadNext()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [item, result, answer, loadNext])

  const accuracy = state && state.total_answered ? Math.round((state.total_correct / state.total_answered) * 100) : null
  const atMaxLevel = state ? state.level >= state.max_level : false

  return (
    <section className="flex h-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      {/* Cabecera: nivel, tema y avance hacia el siguiente */}
      <div className="border-b border-slate-100 bg-gradient-to-br from-brand-50 via-white to-brand-50 p-6 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-md shadow-brand-600/25">
              <FontAwesomeIcon icon={faPuzzlePiece} />
            </span>
            <div>
              <h2 className="text-lg font-extrabold tracking-tight text-slate-900">Completa la oración</h2>
              <p className="text-sm text-slate-500">Elige la palabra correcta. La dificultad sube contigo.</p>
            </div>
          </div>
          {state && (
            <div className="text-right">
              <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
                Nivel {state.level} de {state.max_level}
              </p>
              <p className="font-bold text-slate-900">{state.level_name}</p>
              <p className="text-xs text-slate-500">{state.level_topic}</p>
            </div>
          )}
        </div>

        {state && (
          <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-3">
            <div className="min-w-[180px] flex-1">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                <span>{atMaxLevel ? "Nivel máximo alcanzado" : `Para el nivel ${state.level + 1}`}</span>
                <span>
                  {state.level_progress}/{state.level_goal}
                </span>
              </div>
              <div className="mt-1.5 grid gap-1.5" style={{ gridTemplateColumns: `repeat(${state.level_goal}, 1fr)` }}>
                {Array.from({ length: state.level_goal }, (_, index) => (
                  <span
                    key={index}
                    className={`h-2 rounded-full transition-colors duration-300 ${
                      index < state.level_progress ? "bg-brand-600" : "bg-slate-200"
                    }`}
                  />
                ))}
              </div>
            </div>
            <Stat icon={faFire} tone="text-orange-500" value={state.streak} label="racha" />
            <Stat icon={faTrophy} tone="text-amber-500" value={state.best_streak} label="mejor racha" />
            <Stat icon={faBolt} tone="text-emerald-500" value={accuracy === null ? "—" : `${accuracy}%`} label="aciertos" />
          </div>
        )}
      </div>

      {/* Oración y opciones */}
      <div className="flex flex-1 flex-col justify-center p-6 sm:p-8">
        {error && (
          <div className="flex flex-1 flex-col items-center justify-center py-8 text-center">
            <p className="text-sm text-red-500">{error}</p>
            <button
              onClick={() => void loadNext()}
              className="mt-4 flex items-center gap-2 rounded-full bg-slate-100 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-200"
            >
              <FontAwesomeIcon icon={faRotateRight} className="text-xs" /> Reintentar
            </button>
          </div>
        )}

        {!error && !item && (
          <p className="flex flex-1 items-center justify-center gap-2 py-10 text-slate-400">
            <FontAwesomeIcon icon={faSpinner} spin /> Preparando tu oración...
          </p>
        )}

        {!error && item && (
          <>
            {/* Alto reservado para dos líneas: al fallar se muestran dos
                palabras en el hueco (la elegida tachada y la correcta), y en
                una oración larga eso la parte en dos líneas. Sin reserva,
                la tarjeta crecería justo al responder. */}
            <div className="flex min-h-[6.5rem] items-center justify-center">
              <p className="text-center text-2xl font-bold leading-relaxed text-slate-900 sm:text-3xl">
                <Sentence sentence={item.sentence} chosen={chosen} result={result} />
              </p>
            </div>

            <div className="mx-auto mt-6 grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-2">
              {item.options.map((option, index) => (
                <OptionButton
                  key={option}
                  option={option}
                  shortcut={index + 1}
                  chosen={chosen}
                  result={result}
                  disabled={busy || result !== null}
                  onClick={() => void answer(option)}
                />
              ))}
            </div>

            {/* Zona de corrección: SIEMPRE visible y del mismo tamaño.
                La tarjeta comparte fila con Teacher David y la práctica de
                hoy, y la fila mide lo que la más alta: si la corrección
                apareciera al responder y desapareciera al pedir la
                siguiente, la tarjeta cambiaría de alto y arrastraría el
                botón "Practicar con Teacher David".

                Antes esto se resolvía reservando el hueco en blanco, y el
                espacio vacío bajo las opciones parecía un error. Ahora el
                hueco está ocupado desde el principio: un panel con la
                instrucción que luego se convierte en la corrección, y el
                botón "Siguiente" presente pero desactivado hasta responder. */}
            <div className="mx-auto mt-6 w-full max-w-2xl">
              <div
                // min-h calculado para el caso más alto en escritorio:
                // título + la explicación más larga del banco (77
                // caracteres, una línea) + el aviso de subida de nivel.
                className={`flex min-h-[7.5rem] items-start gap-3 rounded-2xl px-5 py-4 transition-colors duration-200 ${
                  !result
                    ? "items-center justify-center border border-dashed border-slate-200 bg-slate-50/70 text-slate-500"
                    : result.correct
                      ? "bg-emerald-50 text-emerald-900"
                      : "bg-rose-50 text-rose-900"
                }`}
              >
                {!result ? (
                  <p className="text-center text-sm">
                    <FontAwesomeIcon icon={faPuzzlePiece} className="mr-2 text-brand-400" />
                    Elige la palabra que completa la oración
                    <span className="hidden sm:inline"> · o pulsa las teclas 1 a 4</span>
                  </p>
                ) : (
                  <>
                    <FontAwesomeIcon
                      icon={result.correct ? faCircleCheck : faCircleXmark}
                      className={`mt-0.5 text-lg ${result.correct ? "text-emerald-500" : "text-rose-500"}`}
                    />
                    <div>
                      <p className="font-bold">
                        {result.correct ? "¡Correcto!" : `La respuesta era "${result.correct_answer}"`}
                      </p>
                      <p className="mt-0.5 text-sm opacity-80">{result.explanation_es}</p>
                      {result.leveled_up && state && (
                        <p className="mt-2 flex items-center gap-2 text-sm font-bold text-brand-700">
                          <FontAwesomeIcon icon={faTrophy} className="text-amber-500" />
                          ¡Subiste al nivel {state.level}: {state.level_name}!
                        </p>
                      )}
                    </div>
                  </>
                )}
              </div>

              <button
                onClick={() => void loadNext()}
                disabled={busy || !result}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-ink-900 py-3.5 font-semibold text-white transition active:scale-[0.99] hover:bg-ink-800 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
              >
                {result ? (
                  <>
                    Siguiente oración <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
                    <kbd className="ml-2 hidden rounded bg-white/15 px-1.5 py-0.5 text-[10px] font-medium sm:inline">
                      Enter
                    </kbd>
                  </>
                ) : (
                  "Responde para continuar"
                )}
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  )
}

/** Pinta la oración con el hueco convertido en una casilla: vacía antes de
 * responder y con la palabra elegida después, en verde o en rojo. */
function Sentence({ sentence, chosen, result }: { sentence: string; chosen: string | null; result: GameAnswer | null }) {
  const [before, after] = sentence.split("___")
  const slotTone = !chosen
    ? "border-dashed border-slate-300 bg-slate-50 text-transparent"
    : !result
      ? "border-brand-300 bg-brand-50 text-brand-700"
      : result.correct
        ? "border-emerald-300 bg-emerald-50 text-emerald-700"
        : "border-rose-300 bg-rose-50 text-rose-700 line-through decoration-2"

  return (
    <>
      {before}
      <span
        className={`mx-1 inline-block min-w-[5.5rem] rounded-xl border-2 px-3 py-0.5 align-baseline transition-colors ${slotTone}`}
      >
        {chosen ?? "____"}
      </span>
      {result && !result.correct && (
        <span className="mr-1 inline-block rounded-xl border-2 border-emerald-300 bg-emerald-50 px-3 py-0.5 text-emerald-700">
          {result.correct_answer}
        </span>
      )}
      {after}
    </>
  )
}

function OptionButton({
  option,
  shortcut,
  chosen,
  result,
  disabled,
  onClick,
}: {
  option: string
  shortcut: number
  chosen: string | null
  result: GameAnswer | null
  disabled: boolean
  onClick: () => void
}) {
  const isChosen = chosen === option
  const isCorrect = result !== null && option === result.correct_answer
  const tone =
    result === null
      ? isChosen
        ? "border-brand-500 bg-brand-50 text-brand-900"
        : "border-slate-200 bg-white text-slate-800 hover:border-brand-300 hover:bg-brand-50/40"
      : isCorrect
        ? "border-emerald-400 bg-emerald-50 text-emerald-900"
        : isChosen
          ? "border-rose-400 bg-rose-50 text-rose-900"
          : "border-slate-100 bg-white text-slate-400"

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-3 rounded-2xl border-2 px-4 py-3.5 text-left text-lg font-semibold transition active:scale-[0.98] disabled:cursor-default ${tone}`}
    >
      <kbd className="hidden h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500 sm:flex">
        {shortcut}
      </kbd>
      <span className="flex-1">{option}</span>
      {result !== null && isCorrect && <FontAwesomeIcon icon={faCircleCheck} className="text-emerald-500" />}
      {result !== null && isChosen && !isCorrect && <FontAwesomeIcon icon={faCircleXmark} className="text-rose-500" />}
    </button>
  )
}

function Stat({
  icon,
  tone,
  value,
  label,
}: {
  icon: typeof faFire
  tone: string
  value: number | string
  label: string
}) {
  return (
    <div className="flex items-center gap-2">
      <FontAwesomeIcon icon={icon} className={tone} />
      <span className="text-lg font-extrabold text-slate-900">{value}</span>
      <span className="text-xs font-medium text-slate-500">{label}</span>
    </div>
  )
}
