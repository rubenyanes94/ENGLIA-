import {
  faArrowLeft,
  faBookOpen,
  faCommentDots,
  faSpinner,
  faTriangleExclamation,
  faVolumeHigh,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState, type ReactNode } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { api } from "../api/client"
import type { ModuleDetail } from "../api/types"
import { ApiError } from "../api/types"

const SEVERITY_STYLES: Record<string, string> = {
  low: "bg-slate-700/50 text-slate-300",
  medium: "bg-amber-500/10 text-amber-300",
  high: "bg-orange-500/10 text-orange-300",
  critical: "bg-red-500/10 text-red-300",
}

export default function ModuleDetailPage() {
  const { moduleId } = useParams<{ moduleId: string }>()
  const navigate = useNavigate()
  const [module, setModule] = useState<ModuleDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [enrolling, setEnrolling] = useState(false)
  const [enrolled, setEnrolled] = useState(false)

  useEffect(() => {
    if (!moduleId) return
    setLoading(true)
    api
      .get<ModuleDetail>(`/modules/${moduleId}`)
      .then(setModule)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar el módulo."))
      .finally(() => setLoading(false))
  }, [moduleId])

  async function handleEnroll() {
    if (!moduleId) return
    setEnrolling(true)
    try {
      await api.post(`/modules/${moduleId}/enroll`)
      setEnrolled(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo inscribir en el módulo.")
    } finally {
      setEnrolling(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Cargando módulo...
      </div>
    )
  }

  if (!module) {
    return <div className="text-red-400">{error ?? "Módulo no encontrado."}</div>
  }

  return (
    <div className="space-y-8">
      <Link to="/" className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200">
        <FontAwesomeIcon icon={faArrowLeft} /> Volver a la certificación
      </Link>

      <header>
        <span className="text-xs font-mono text-slate-500">{module.code}</span>
        <h1 className="mt-1 text-2xl font-bold">{module.title}</h1>
        <p className="text-slate-400">{module.title_es}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-slate-800 px-3 py-1 text-slate-300">{module.estimated_hours}h</span>
          <span className="rounded-full bg-slate-800 px-3 py-1 text-slate-300">{module.skill_focus}</span>
          {module.recycles.length > 0 && (
            <span className="rounded-full bg-slate-800 px-3 py-1 text-slate-400">Recicla: {module.recycles.join(", ")}</span>
          )}
        </div>

        <button
          onClick={handleEnroll}
          disabled={enrolling || enrolled}
          className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {enrolling && <FontAwesomeIcon icon={faSpinner} spin />}
          {enrolled ? "Inscrito ✓" : "Inscribirme en este módulo"}
        </button>
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      </header>

      {module.communicative_objectives.length > 0 && (
        <Section title="Objetivos comunicativos">
          <ul className="list-inside list-disc space-y-1 text-slate-300">
            {module.communicative_objectives.map((objective) => (
              <li key={objective}>{objective}</li>
            ))}
          </ul>
        </Section>
      )}

      {module.grammar.focus && module.grammar.focus.length > 0 && (
        <Section title="Gramática (al servicio de los objetivos)">
          <ul className="list-inside list-disc space-y-1 text-slate-300">
            {module.grammar.focus.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {module.grammar.note && <p className="mt-3 text-sm italic text-slate-500">{module.grammar.note}</p>}
        </Section>
      )}

      {(module.lexis.sets?.length || module.lexis.chunks?.length) && (
        <Section title="Léxico">
          {module.lexis.sets && module.lexis.sets.length > 0 && (
            <div className="mb-3">
              <p className="mb-2 text-sm text-slate-500">Campos léxicos ({module.lexis.target_items ?? "?"} ítems objetivo)</p>
              <div className="flex flex-wrap gap-2">
                {module.lexis.sets.map((set) => (
                  <span key={set} className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                    {set}
                  </span>
                ))}
              </div>
            </div>
          )}
          {module.lexis.chunks && module.lexis.chunks.length > 0 && (
            <div>
              <p className="mb-2 text-sm text-slate-500">Chunks prefabricados</p>
              <ul className="space-y-1">
                {module.lexis.chunks.map((chunk) => (
                  <li key={chunk} className="rounded-lg bg-slate-800/60 px-3 py-1.5 text-sm text-emerald-300">
                    "{chunk}"
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Section>
      )}

      {module.pronunciation.focus && (
        <Section title="Pronunciación" icon={faVolumeHigh}>
          <p className="text-slate-300">{module.pronunciation.focus}</p>
          {module.pronunciation.l1_alerts && module.pronunciation.l1_alerts.length > 0 && (
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-amber-300/80">
              {module.pronunciation.l1_alerts.map((alert) => (
                <li key={alert}>{alert}</li>
              ))}
            </ul>
          )}
        </Section>
      )}

      {module.l1_interference.length > 0 && (
        <Section title="Interferencia L1 (hispanohablantes)" icon={faTriangleExclamation}>
          <div className="space-y-2">
            {module.l1_interference.map((item) => (
              <div key={item.error} className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[item.severity]}`}>
                    {item.severity}
                  </span>
                  <span className="font-mono text-sm text-red-300 line-through decoration-red-500/50">{item.error}</span>
                  <span className="text-slate-600">→</span>
                  <span className="font-mono text-sm text-emerald-300">{item.target}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">Origen: {item.origin}</p>
                {item.note && <p className="mt-1 text-xs italic text-slate-400">{item.note}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {module.tasks.length > 0 && (
        <Section title="Tareas comunicativas" icon={faCommentDots}>
          <div className="space-y-3">
            {module.tasks.map((task) => (
              <div key={task.id} className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-mono text-slate-500">
                    {task.type} · {task.descriptor}
                  </span>
                  <button
                    onClick={() => navigate(`/chat?module=${module.id}&task=${task.id}`)}
                    className="flex shrink-0 items-center gap-1.5 rounded-full bg-sky-600/20 px-3 py-1 text-xs font-medium text-sky-300 transition hover:bg-sky-600/30"
                  >
                    <FontAwesomeIcon icon={faCommentDots} /> Practicar con el tutor
                  </button>
                </div>
                <p className="mt-2 text-slate-200">{task.prompt}</p>
                {task.success_criteria && <p className="mt-1 text-sm text-slate-500">Se logra si: {task.success_criteria}</p>}
                {task.note && <p className="mt-1 text-xs italic text-slate-500">{task.note}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {module.lessons.length > 0 && (
        <Section title="Lecciones" icon={faBookOpen}>
          <ul className="space-y-1">
            {module.lessons.map((lesson) => (
              <li key={lesson.id} className="rounded-lg bg-slate-800/60 px-3 py-2 text-sm text-slate-300">
                {lesson.order}. {lesson.title}
                {lesson.audio_duration_seconds && (
                  <span className="ml-2 text-xs text-slate-500">{Math.round(lesson.audio_duration_seconds)}s de audio</span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}

function Section({
  title,
  icon,
  children,
}: {
  title: string
  icon?: typeof faBookOpen
  children: ReactNode
}) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
        {icon && <FontAwesomeIcon icon={icon} className="text-slate-500" />}
        {title}
      </h2>
      {children}
    </section>
  )
}
