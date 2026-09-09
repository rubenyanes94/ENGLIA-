import { faCircleCheck, faMicrophone, faSpinner, faStop, faXmark } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"
import { api } from "../api/client"
import { useVoiceRecorder } from "../hooks/useVoiceRecorder"
import type { PronunciationFeedback } from "../api/types"

/** El alumno repite una frase de la lección y el tutor le dice qué oyó.
 *
 * Es la primera vez que Espikin escucha al estudiante. Hasta ahora el
 * producto era de una sola dirección — el tutor habla, el alumno escribe —
 * y una academia de idiomas que nunca oye hablar a su alumno no puede
 * corregir lo único que de verdad cuesta.
 */
export default function PronunciationPractice({
  phrase,
  levelCode,
  onClose,
}: {
  phrase: string
  levelCode: string
  onClose: () => void
}) {
  const { state, start, stop } = useVoiceRecorder()
  const [feedback, setFeedback] = useState<PronunciationFeedback | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function toggle() {
    if (state === "recording") {
      const wav = await stop()
      if (!wav) return setError("No se pudo procesar la grabación. Inténtalo otra vez.")

      setEvaluating(true)
      setError(null)
      try {
        const form = new FormData()
        form.append("audio", wav, "intento.wav")
        form.append("expected", phrase)
        form.append("level_code", levelCode)
        setFeedback(await api.postForm<PronunciationFeedback>("/pronunciation/attempts", form))
      } catch {
        setError("El evaluador no está disponible ahora mismo. Prueba en un momento.")
      } finally {
        setEvaluating(false)
      }
      return
    }

    setFeedback(null)
    setError(null)
    await start()
  }

  const busy = evaluating || state === "processing"

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Repite en voz alta</p>
          <p className="mt-1 text-xl font-bold text-blue-700">{phrase}</p>
        </div>
        <button onClick={onClose} aria-label="Cerrar" className="rounded-full p-2 text-slate-400 transition hover:bg-slate-100">
          <FontAwesomeIcon icon={faXmark} />
        </button>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={toggle}
          disabled={busy}
          className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-lg text-white shadow-lg transition active:scale-95 disabled:opacity-60 ${
            state === "recording" ? "animate-pulse bg-red-500 shadow-red-500/30" : "bg-blue-600 shadow-blue-600/30 hover:bg-blue-500"
          }`}
        >
          <FontAwesomeIcon icon={busy ? faSpinner : state === "recording" ? faStop : faMicrophone} spin={busy} />
        </button>
        <p className="text-sm text-slate-500">
          {state === "denied"
            ? "Necesitamos permiso para usar el micrófono."
            : state === "recording"
              ? "Grabando… pulsa para terminar."
              : busy
                ? "Escuchando lo que dijiste…"
                : "Pulsa y di la frase."}
        </p>
      </div>

      {error && <p className="mt-3 text-sm text-amber-700">{error}</p>}

      {feedback && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          {/* Lo que se OYÓ va primero y en grande. La nota es lo que el
              alumno mira, pero lo que le enseña es leer que dijo algo
              distinto de lo que creía haber dicho. */}
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Te oí decir</p>
          <p className={`mt-1 text-lg font-semibold ${feedback.matches ? "text-emerald-600" : "text-amber-600"}`}>
            “{feedback.transcript}”
          </p>

          <div className="mt-3 flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  feedback.score >= 80 ? "bg-emerald-500" : feedback.score >= 50 ? "bg-amber-400" : "bg-red-400"
                }`}
                style={{ width: `${feedback.score}%` }}
              />
            </div>
            <span className="w-12 text-right text-sm font-bold text-slate-700">{feedback.score}</span>
          </div>

          <p className="mt-3 flex items-start gap-2 text-sm text-slate-600">
            {feedback.matches && <FontAwesomeIcon icon={faCircleCheck} className="mt-0.5 text-emerald-500" />}
            {feedback.feedback_es}
          </p>
        </div>
      )}
    </div>
  )
}
