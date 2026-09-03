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
  low: "bg-slate-100 text-slate-500",
  medium: "bg-amber-50 text-amber-600",
  high: "bg-orange-50 text-orange-600",
  critical: "bg-red-50 text-red-600",
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
    return <div className="text-red-500">{error ?? "Módulo no encontrado."}</div>
  }

  return (
    <div className="space-y-6">
      <Link to="/classroom" className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-600">
        <FontAwesomeIcon icon={faArrowLeft} /> Volver al classroom
      </Link>

      <header>
        <span className="text-xs font-mono text-slate-400">{module.code}</span>
        <h1 className="mt-1 text-2xl font-extrabold text-slate-900">{module.title}</h1>
        <p className="text-slate-500">{module.title_es}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{module.estimated_hours}h</span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{module.skill_focus}</span>
          {module.recycles.length > 0 && (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-500">Recicla: {module.recycles.join(", ")}</span>
          )}
        </div>

        <button
          onClick={handleEnroll}
          disabled={enrolling || enrolled}
          className="mt-4 flex items-center gap-2 rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
        >
          {enrolling && <FontAwesomeIcon icon={faSpinner} spin />}
          {enrolled ? "Inscrito ✓" : "Inscribirme en este módulo"}
        </button>
        {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
      </header>

      {module.communicative_objectives.length > 0 && (
        <Section title="Objetivos comunicativos">
          <ul className="list-inside list-disc space-y-1 text-slate-600">
            {module.communicative_objectives.map((objective) => (
              <li key={objective}>{objective}</li>
            ))}
          </ul>
        </Section>
      )}

      {module.grammar.focus && module.grammar.focus.length > 0 && (
        <Section title="Gramática (al servicio de los objetivos)">
          <ul className="list-inside list-disc space-y-1 text-slate-600">
            {module.grammar.focus.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {module.grammar.note && <p className="mt-3 text-sm italic text-slate-400">{module.grammar.note}</p>}
        </Section>
      )}

      {(module.lexis.sets?.length || module.lexis.chunks?.length) && (
        <Section title="Léxico">
          {module.lexis.sets && module.lexis.sets.length > 0 && (
            <div className="mb-3">
              <p className="mb-2 text-sm text-slate-400">Campos léxicos ({module.lexis.target_items ?? "?"} ítems objetivo)</p>
              <div className="flex flex-wrap gap-2">
                {module.lexis.sets.map((set) => (
                  <span key={set} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                    {set}
                  </span>
                ))}
              </div>
            </div>
          )}
          {module.lexis.chunks && module.lexis.chunks.length > 0 && (
            <div>
              <p className="mb-2 text-sm text-slate-400">Chunks prefabricados</p>
              <ul className="space-y-1">
                {module.lexis.chunks.map((chunk) => (
                  <li key={chunk} className="rounded-xl bg-blue-50 px-3 py-1.5 text-sm text-blue-700">
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
          <p className="text-slate-600">{module.pronunciation.focus}</p>
          {module.pronunciation.l1_alerts && module.pronunciation.l1_alerts.length > 0 && (
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-amber-600">
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
              <div key={item.error} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[item.severity]}`}>
                    {item.severity}
                  </span>
                  <span className="font-mono text-sm text-red-500 line-through decoration-red-300">{item.error}</span>
                  <span className="text-slate-300">→</span>
                  <span className="font-mono text-sm text-emerald-600">{item.target}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">Origen: {item.origin}</p>
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
              <div key={task.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-mono text-slate-400">
                    {task.type} · {task.descriptor}
                  </span>
                  <button
                    onClick={() => navigate(`/chat?module=${module.id}&task=${task.id}`)}
                    className="flex shrink-0 items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 transition active:scale-[0.98] hover:bg-blue-200"
                  >
                    <FontAwesomeIcon icon={faCommentDots} /> Practicar con el tutor
                  </button>
                </div>
                <p className="mt-2 text-slate-700">{task.prompt}</p>
                {task.success_criteria && <p className="mt-1 text-sm text-slate-400">Se logra si: {task.success_criteria}</p>}
                {task.note && <p className="mt-1 text-xs italic text-slate-400">{task.note}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {module.lessons.length > 0 && (
        <Section title="Lecciones" icon={faBookOpen}>
          <ul className="space-y-1">
            {module.lessons.map((lesson) => (
              <li key={lesson.id} className="rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-600">
                {lesson.order}. {lesson.title}
                {lesson.audio_duration_seconds && (
                  <span className="ml-2 text-xs text-slate-400">{Math.round(lesson.audio_duration_seconds)}s de audio</span>
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
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-900">
        {icon && <FontAwesomeIcon icon={icon} className="text-slate-400" />}
        {title}
      </h2>
      {children}
    </section>
  )
}
