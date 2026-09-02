import { faCircleCheck, faPaperPlane, faSpinner, faXmark } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useRef, useState, type FormEvent } from "react"
import { useSearchParams } from "react-router-dom"
import { api } from "../api/client"
import type { ChatMessage, CreateSessionResponse, SendMessageResponse } from "../api/types"
import { ApiError } from "../api/types"

const LEVEL_CODE = "A1" // único nivel con tutor+currículo sembrado hoy

interface DisplayMessage {
  role: "user" | "assistant"
  content: string
  corrections?: { error: string; correction: string; rule: string }[]
  taskCompleted?: boolean | null
}

export default function ChatPage() {
  const [searchParams] = useSearchParams()
  const moduleId = searchParams.get("module")
  const taskId = searchParams.get("task")

  const [session, setSession] = useState<CreateSessionResponse | null>(null)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [input, setInput] = useState("")
  const [starting, setStarting] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setStarting(true)
    setError(null)
    api
      .post<CreateSessionResponse>("/chat/sessions", { level_code: LEVEL_CODE, module_id: moduleId || undefined })
      .then(setSession)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo abrir la sesión con el tutor."))
      .finally(() => setStarting(false))
    // Nueva sesión si cambia el módulo objetivo (ej. el alumno vuelve al
    // detalle y elige "practicar" otra tarea) — a propósito, no se reusa
    // la sesión anterior entre módulos distintos.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moduleId])

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
        { role: "assistant", content: res.reply, corrections: res.corrections, taskCompleted: res.task_completed },
      ])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "El tutor no pudo responder. Inténtalo de nuevo.")
    } finally {
      setSending(false)
    }
  }

  if (starting) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Abriendo sesión con el tutor...
      </div>
    )
  }

  if (!session) {
    return <div className="text-red-400">{error ?? "No se pudo abrir la sesión."}</div>
  }

  return (
    <div className="flex h-[calc(100vh-160px)] flex-col">
      <header className="mb-4 flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold">{session.persona_name}</h1>
          <p className="text-sm text-slate-500">
            Nivel {session.level_code}
            {session.module_title && ` · Módulo: ${session.module_title}`}
            {taskId && ` · Tarea: ${taskId}`}
          </p>
        </div>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto pr-2">
        {messages.length === 0 && (
          <p className="text-center text-sm text-slate-500">
            Escribe un mensaje para empezar a conversar con {session.persona_name}.
          </p>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
                msg.role === "user" ? "bg-emerald-600 text-white" : "bg-slate-800 text-slate-100"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {msg.corrections && msg.corrections.length > 0 && (
                <div className="mt-2 space-y-1.5 border-t border-white/10 pt-2">
                  {msg.corrections.map((c, j) => (
                    <div key={j} className="text-xs text-amber-200/90">
                      <span className="line-through decoration-red-400/60">{c.error}</span>
                      {" → "}
                      <span className="font-medium text-emerald-300">{c.correction}</span>
                      <p className="text-slate-400">{c.rule}</p>
                    </div>
                  ))}
                </div>
              )}

              {msg.taskCompleted !== null && msg.taskCompleted !== undefined && (
                <div
                  className={`mt-2 flex items-center gap-1.5 border-t border-white/10 pt-2 text-xs ${
                    msg.taskCompleted ? "text-emerald-300" : "text-slate-400"
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
            <div className="flex items-center gap-2 rounded-2xl bg-slate-800 px-4 py-2.5 text-slate-400">
              <FontAwesomeIcon icon={faSpinner} spin />
              <span className="text-sm">
                Pensando... (puede tardar hasta un minuto en este entorno de desarrollo sin GPU)
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}

      <form onSubmit={handleSend} className="mt-4 flex gap-2 border-t border-slate-800 pt-4">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
          placeholder="Escribe en inglés..."
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-emerald-500 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          <FontAwesomeIcon icon={faPaperPlane} />
        </button>
      </form>
    </div>
  )
}
