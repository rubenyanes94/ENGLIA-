import {
  faArrowLeft,
  faArrowRight,
  faBookOpen,
  faCircleCheck,
  faClipboardCheck,
  faRotateRight,
  faSpinner,
  faTriangleExclamation,
  faXmark,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { api } from "../api/client"
import type { ExamResult, ModuleExam } from "../api/types"
import { ApiError } from "../api/types"
import Modal from "./Modal"

type Step = "loading" | "intro" | "answering" | "submitting" | "result" | "error"

/** Examen de un módulo: si el alumno aprueba, el módulo queda completado
 * y pasa directamente al siguiente.
 *
 * Las preguntas van de una en una en vez de todas en una lista larga: en
 * el móvil, que es donde estudia la mayoría, una pantalla por pregunta se
 * lee sin hacer scroll y deja claro cuánto falta.
 */
export default function ModuleExamModal({
  moduleId,
  moduleTitle,
  position,
  onClose,
  onGoToNext,
  onCompleted,
}: {
  moduleId: string
  moduleTitle: string
  position: number
  onClose: () => void
  onGoToNext: (nextModuleId: string) => void
  /** Se llama al aprobar, para que la página refresque el estado del módulo. */
  onCompleted: () => void
}) {
  const [step, setStep] = useState<Step>("loading")
  const [exam, setExam] = useState<ModuleExam | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [index, setIndex] = useState(0)
  const [result, setResult] = useState<ExamResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<ModuleExam>(`/modules/${moduleId}/exam`)
      .then((data) => {
        setExam(data)
        setStep("intro")
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el examen.")
        setStep("error")
      })
  }, [moduleId])

  function restart() {
    setAnswers({})
    setIndex(0)
    setResult(null)
    setStep("answering")
  }

  async function submit() {
    setStep("submitting")
    try {
      const data = await api.post<ExamResult>(`/modules/${moduleId}/exam`, { answers })
      setResult(data)
      setStep("result")
      if (data.module_completed) onCompleted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo entregar el examen.")
      setStep("error")
    }
  }

  const questions = exam?.questions ?? []
  const current = questions[index]
  const answeredCount = questions.filter((question) => answers[question.id]).length
  const allAnswered = questions.length > 0 && answeredCount === questions.length

  return (
    // Mientras responde no se cierra con un clic fuera ni con Escape: se
    // perderían todas las respuestas marcadas. Para salir está la X.
    <Modal onClose={onClose} wide dismissible={step !== "answering" && step !== "submitting"}>
      <div className="flex items-start justify-between gap-4">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-blue-600">
          <FontAwesomeIcon icon={faClipboardCheck} /> Examen · Módulo {position}
        </p>
        {step !== "submitting" && (
          <button
            onClick={onClose}
            aria-label="Cerrar examen"
            className="-mr-2 -mt-2 flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        )}
      </div>

      {step === "loading" && (
        <p className="flex items-center justify-center gap-2 py-16 text-slate-400">
          <FontAwesomeIcon icon={faSpinner} spin /> Preparando el examen...
        </p>
      )}

      {step === "error" && (
        <div className="py-10 text-center">
          <FontAwesomeIcon icon={faTriangleExclamation} className="text-3xl text-amber-500" />
          <p className="mt-3 font-semibold text-slate-800">{error}</p>
          <button
            onClick={onClose}
            className="mt-6 rounded-full bg-slate-100 px-6 py-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-200"
          >
            Cerrar
          </button>
        </div>
      )}

      {step === "intro" && exam && (
        <div className="pt-4 text-center">
          <h2 className="text-2xl font-extrabold tracking-tight text-slate-900">{moduleTitle}</h2>
          <p className="mx-auto mt-3 max-w-md text-slate-600">
            Si ya dominas este módulo, demuéstralo y pasa directo al siguiente.
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <Stat value={exam.total} label="preguntas" />
            <Stat value={exam.pass_count} label="aciertos para aprobar" />
          </div>

          <p className="mt-5 text-xs text-slate-400">
            Puedes volver a presentarlo si no apruebas. Cuenta tu mejor resultado.
          </p>

          <button
            onClick={() => setStep("answering")}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 py-4 font-bold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500"
          >
            Empezar examen <FontAwesomeIcon icon={faArrowRight} className="text-sm" />
          </button>
        </div>
      )}

      {(step === "answering" || step === "submitting") && current && (
        <div className="pt-4">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
            <span>
              Pregunta {index + 1} de {questions.length}
            </span>
            <span>{answeredCount} respondidas</span>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-600 transition-[width] duration-300"
              style={{ width: `${((index + 1) / questions.length) * 100}%` }}
            />
          </div>

          <h2 className="mt-6 text-xl font-extrabold leading-snug text-slate-900">{current.prompt}</h2>

          <div className="mt-5 space-y-2.5" role="radiogroup">
            {current.options.map((option, optionIndex) => {
              const selected = answers[current.id] === option
              return (
                <button
                  key={option}
                  role="radio"
                  aria-checked={selected}
                  disabled={step === "submitting"}
                  onClick={() => setAnswers((prev) => ({ ...prev, [current.id]: option }))}
                  className={`flex w-full items-center gap-3 rounded-2xl border-2 px-4 py-3.5 text-left font-semibold transition active:scale-[0.99] ${
                    selected
                      ? "border-blue-600 bg-blue-50 text-blue-900"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  <span
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      selected ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {String.fromCharCode(65 + optionIndex)}
                  </span>
                  {option}
                </button>
              )
            })}
          </div>

          <div className="mt-6 flex items-center justify-between gap-3">
            <button
              onClick={() => setIndex((i) => i - 1)}
              disabled={index === 0 || step === "submitting"}
              className="flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-slate-500 transition hover:bg-slate-100 disabled:invisible"
            >
              <FontAwesomeIcon icon={faArrowLeft} className="text-xs" /> Anterior
            </button>

            {index < questions.length - 1 ? (
              <button
                onClick={() => setIndex((i) => i + 1)}
                disabled={!answers[current.id]}
                className="flex items-center gap-2 rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
              >
                Siguiente <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
              </button>
            ) : (
              <button
                onClick={submit}
                // Solo con todo respondido: una pregunta en blanco cuenta
                // como fallo, y entregar sin darse cuenta costaría el aprobado.
                disabled={!allAnswered || step === "submitting"}
                className="flex items-center gap-2 rounded-full bg-blue-600 px-6 py-3 text-sm font-bold text-white shadow-md shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
              >
                {step === "submitting" ? (
                  <>
                    <FontAwesomeIcon icon={faSpinner} spin /> Corrigiendo...
                  </>
                ) : (
                  "Entregar examen"
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {step === "result" && result && (
        <ResultView
          result={result}
          onRetry={restart}
          onClose={onClose}
          onGoToNext={() => result.next_module_id && onGoToNext(result.next_module_id)}
        />
      )}
    </Modal>
  )
}

function ResultView({
  result,
  onRetry,
  onClose,
  onGoToNext,
}: {
  result: ExamResult
  onRetry: () => void
  onClose: () => void
  onGoToNext: () => void
}) {
  if (result.passed) {
    return (
      <div className="pt-4 text-center">
        <span className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-50 text-4xl text-emerald-500">
          <FontAwesomeIcon icon={faCircleCheck} />
        </span>
        <h2 className="mt-5 text-2xl font-extrabold tracking-tight text-slate-900">¡Aprobaste el módulo!</h2>
        <p className="mt-2 text-slate-600">
          {result.correct} de {result.total} respuestas correctas.
        </p>

        {result.next_module_id ? (
          <button
            onClick={onGoToNext}
            className="mt-7 flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 py-4 font-bold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500"
          >
            Ir al módulo siguiente <FontAwesomeIcon icon={faArrowRight} className="text-sm" />
          </button>
        ) : (
          <>
            <p className="mt-4 text-sm text-slate-500">Era el último módulo del nivel.</p>
            <button
              onClick={onClose}
              className="mt-6 w-full rounded-2xl bg-slate-900 py-4 font-bold text-white transition hover:bg-slate-800"
            >
              Cerrar
            </button>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="pt-4">
      <div className="text-center">
        <p className="text-5xl font-black tracking-tight text-slate-900">
          {result.correct}
          <span className="text-2xl text-slate-300">/{result.total}</span>
        </p>
        <h2 className="mt-3 text-xl font-extrabold text-slate-900">Casi. Necesitas {result.pass_count} aciertos.</h2>
        <p className="mt-1 text-sm text-slate-500">Te faltaron {result.pass_count - result.correct}.</p>
      </div>

      {/* Se dice QUÉ repasar, no cuál era la respuesta: con cuatro
          opciones, enseñarla convertiría el examen en copiar a la segunda. */}
      {result.review.length > 0 && (
        <div className="mt-6 rounded-2xl bg-amber-50 p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-amber-700">Repasa esto antes de volver</p>
          <ul className="mt-2 space-y-1.5">
            {result.review.map((item) => (
              <li key={item.descriptor_code} className="flex items-start gap-2 text-sm text-amber-900">
                <FontAwesomeIcon icon={faBookOpen} className="mt-1 shrink-0 text-xs text-amber-500" />
                {item.statement_es}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        <button
          onClick={onClose}
          className="rounded-2xl bg-slate-100 py-3.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-200"
        >
          Repasar la lección
        </button>
        <button
          onClick={onRetry}
          className="flex items-center justify-center gap-2 rounded-2xl bg-blue-600 py-3.5 text-sm font-bold text-white transition active:scale-[0.98] hover:bg-blue-500"
        >
          <FontAwesomeIcon icon={faRotateRight} className="text-xs" /> Intentar de nuevo
        </button>
      </div>
    </div>
  )
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 px-4 py-4">
      <p className="text-3xl font-black text-slate-900">{value}</p>
      <p className="mt-0.5 text-xs font-semibold text-slate-500">{label}</p>
    </div>
  )
}
