import { faArrowLeft, faCircleCheck, faMasksTheater, faPaperPlane, faShieldHalved, faSpinner, faXmark } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useRef, useState, type FormEvent } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { api } from "../api/client"
import type { CreateSessionResponse, FlashCourseDetail, SendMessageResponse } from "../api/types"
import { ApiError } from "../api/types"

const LEVEL_CODE = "A1" // único nivel con tutor+currículo sembrado hoy

interface DisplayMessage {
  role: "user" | "assistant"
  content: string
  corrections?: { error: string; correction: string; rule: string }[]
  moderationBlocked?: boolean
  taskCompleted?: boolean | null
}

export default function ChatPage() {
  const [searchParams] = useSearchParams()
  const moduleId = searchParams.get("module")
  // Curso de la Biblioteca (su slug). Con `task` indica qué escenario se ensaya.
  const courseSlug = searchParams.get("course")
  const taskId = searchParams.get("task")

  const [session, setSession] = useState<CreateSessionResponse | null>(null)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [input, setInput] = useState("")
  const [starting, setStarting] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [course, setCourse] = useState<FlashCourseDetail | null>(null)

  useEffect(() => {
    setStarting(true)
    setError(null)
    api
      .post<CreateSessionResponse>("/chat/sessions", {
        level_code: LEVEL_CODE,
        module_id: moduleId || undefined,
        flash_course_slug: courseSlug || undefined,
      })
      .then(setSession)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo abrir la sesión con el tutor."))
      .finally(() => setStarting(false))

    // El curso se pide aparte para enseñar la instrucción del escenario
    // durante la conversación: sin ella a la vista, a los dos turnos el
    // alumno ya no recuerda qué tenía que conseguir.
    setCourse(null)
    if (courseSlug) {
      api.get<FlashCourseDetail>(`/library/courses/${courseSlug}`).then(setCourse).catch(() => setCourse(null))
    }
    // Nueva sesión si cambia el módulo objetivo (ej. el alumno vuelve al
    // detalle y elige "practicar" otra tarea) — a propósito, no se reusa
    // la sesión anterior entre módulos distintos.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moduleId, courseSlug])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, sending])

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    if (!session || !input.trim() || sending) return

    const userMessage = input.trim()
    setInput("")
    setMessages((prev) => [...prev, { role: "user", content: userMessage }])
    setSending(true)
    setError(null)

    try {
      const res = await api.post<SendMessageResponse>(`/chat/sessions/${session.session_id}/messages`, {
        message: userMessage,
        task_id: taskId || undefined,
      })
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
          corrections: res.corrections,
          taskCompleted: res.task_completed,
          moderationBlocked: res.moderation_blocked,
        },
      ])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "El tutor no pudo responder. Inténtalo de nuevo.")
    } finally {
      setSending(false)
    }
  }

  const scenario = course?.scenarios.find((item) => item.id === taskId) ?? null
  const scenarioCompleted = messages.some((message) => message.taskCompleted === true)

  if (starting) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Abriendo sesión con el tutor...
      </div>
    )
  }

  if (!session) {
    return <div className="text-red-500">{error ?? "No se pudo abrir la sesión."}</div>
  }

  return (
    // max-w-4xl dentro del contenedor ancho: una conversación a 1400px de
    // ancho es incómoda de leer (líneas larguísimas). El ancho completo lo
    // aprovechan las vistas de contenido, no esta.
    <div className="mx-auto flex h-[calc(100vh-200px)] w-full max-w-4xl flex-col md:h-[calc(100vh-190px)]">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div>
          <h1 className="text-lg font-bold text-slate-900">{session.persona_name}</h1>
          <p className="text-sm text-slate-500">
            Nivel {session.level_code}
            {session.module_title && ` · ${session.module_title}`}
            {session.course_title && ` · ${session.course_title}`}
          </p>
        </div>
        {courseSlug ? (
          <Link
            to={`/library/${courseSlug}`}
            className="flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-200"
          >
            <FontAwesomeIcon icon={faArrowLeft} className="text-[10px]" /> Volver al curso
          </Link>
        ) : (
          taskId && (
            <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-600">
              Practicando: {taskId}
            </span>
          )
        )}
      </header>

      {scenario && (
        <div
          className={`mb-4 rounded-2xl border px-5 py-4 ${
            scenarioCompleted ? "border-emerald-200 bg-emerald-50" : "border-blue-100 bg-blue-50"
          }`}
        >
          <p
            className={`flex items-center gap-2 text-xs font-bold uppercase tracking-wide ${
              scenarioCompleted ? "text-emerald-700" : "text-blue-700"
            }`}
          >
            <FontAwesomeIcon icon={scenarioCompleted ? faCircleCheck : faMasksTheater} />
            {scenarioCompleted ? "¡Escenario logrado!" : scenario.title}
          </p>
          <p className="mt-1 text-sm text-slate-700">{scenario.prompt}</p>
          <p className="mt-1 text-xs text-slate-500">
            <span className="font-semibold">El tutor es:</span> {scenario.tutor_role}
          </p>
          {scenarioCompleted && (
            <Link
              to={`/library/${courseSlug}`}
              className="mt-3 inline-flex items-center gap-2 rounded-full bg-emerald-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500"
            >
              Seguir con el curso
            </Link>
          )}
        </div>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {messages.length === 0 && (
          <p className="py-10 text-center text-sm text-slate-400">
            Escribe un mensaje para empezar a conversar con {session.persona_name}.
          </p>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm sm:max-w-[70%] ${
                msg.role === "user" ? "bg-blue-600 text-white" : "bg-white text-slate-800"
              }`}
            >
              {/* Se avisa de que el mensaje anterior no se procesó, en vez
                  de bloquear en silencio: sin esto, el alumno ve al tutor
                  cambiar de tema sin motivo y lo lee como un fallo de la
                  app. Ámbar y no rojo — no ha hecho nada malo
                  necesariamente, la mayoría de bloqueos aquí serán un
                  chico compartiendo datos que no debe. */}
              {msg.moderationBlocked && (
                <p className="mb-2 flex items-center gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs font-medium text-amber-700">
                  <FontAwesomeIcon icon={faShieldHalved} />
                  Ese mensaje no se pudo procesar
                </p>
              )}

              <p className="whitespace-pre-wrap">{msg.content}</p>

              {msg.corrections && msg.corrections.length > 0 && (
                <div className="mt-3 space-y-1.5 border-t border-black/10 pt-2">
                  {msg.corrections.map((c, j) => (
                    <div key={j} className="text-xs">
                      <span className="text-red-500 line-through decoration-red-300">{c.error}</span>
                      {" → "}
                      <span className="font-semibold text-emerald-600">{c.correction}</span>
                      <p className="text-slate-400">{c.rule}</p>
                    </div>
                  ))}
                </div>
              )}

              {msg.taskCompleted !== null && msg.taskCompleted !== undefined && (
                <div
                  className={`mt-3 flex items-center gap-1.5 border-t border-black/10 pt-2 text-xs font-medium ${
                    msg.taskCompleted ? "text-emerald-600" : "text-slate-400"
                  }`}
                >
                  <FontAwesomeIcon icon={msg.taskCompleted ? faCircleCheck : faXmark} />
                  {msg.taskCompleted ? "Tarea completada" : "Todavía no — sigue intentándolo"}
                </div>
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl bg-white px-4 py-3 text-slate-400 shadow-sm">
              <FontAwesomeIcon icon={faSpinner} spin />
              <span className="text-sm">
                Pensando...
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

      <form onSubmit={handleSend} className="mt-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
          placeholder="Escribe en inglés..."
          className="flex-1 rounded-full border border-slate-200 bg-white px-5 py-3 text-sm text-slate-900 shadow-sm outline-none ring-blue-500 focus:ring-2 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="flex items-center gap-2 rounded-full bg-blue-600 px-6 py-3 text-sm font-medium text-white transition active:scale-[0.98] hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-200"
        >
          <FontAwesomeIcon icon={faPaperPlane} />
        </button>
      </form>
    </div>
  )
}
