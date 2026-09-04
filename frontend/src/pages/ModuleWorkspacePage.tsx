import {
  faArrowLeft,
  faArrowRight,
  faBolt,
  faBookOpen,
  faCircleCheck,
  faClipboardCheck,
  faComments,
  faHeadphones,
  faLock,
  faQuoteLeft,
  faSpinner,
  faTriangleExclamation,
  faVolumeHigh,
  faXmark,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState, type ReactNode } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { api } from "../api/client"
import type { CertificationProgress, ModuleDetail, ModuleProgress } from "../api/types"
import { ApiError } from "../api/types"

const LEVEL_CODE = "A1"

type Tab = "leccion" | "practica" | "examen"

const SEVERITY_STYLES: Record<string, string> = {
  low: "bg-slate-100 text-slate-500",
  medium: "bg-amber-50 text-amber-700",
  high: "bg-orange-50 text-orange-700",
  critical: "bg-red-50 text-red-700",
}

/**
 * El aula: donde el alumno realmente pasa las horas.
 *
 * Sustituye a la antigua ficha de módulo, que era una página de lectura
 * sin salida: te inscribías y no pasaba nada. Aquí la inscripción abre
 * el módulo y te deja dentro del flujo Lección -> Práctica -> Examen.
 */
export default function ModuleWorkspacePage() {
  const { moduleId } = useParams<{ moduleId: string }>()
  const navigate = useNavigate()

  const [module, setModule] = useState<ModuleDetail | null>(null)
  const [siblings, setSiblings] = useState<ModuleProgress[]>([])
  const [tab, setTab] = useState<Tab>("leccion")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [enrolling, setEnrolling] = useState(false)

  useEffect(() => {
    if (!moduleId) return
    setLoading(true)
    setTab("leccion")
    Promise.all([
      api.get<ModuleDetail>(`/modules/${moduleId}`),
      api.get<CertificationProgress>(`/levels/${LEVEL_CODE}/certification-progress`).catch(() => null),
    ])
      .then(([moduleData, progressData]) => {
        setModule(moduleData)
        setSiblings(progressData?.modules ?? [])
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar el módulo."))
      .finally(() => setLoading(false))
    window.scrollTo({ top: 0 })
  }, [moduleId])

  const self = siblings.find((m) => m.id === moduleId)
  const position = self ? self.order : module?.order ?? 1
  const total = siblings.length
  const prev = siblings.find((m) => m.order === position - 1)
  const next = siblings.find((m) => m.order === position + 1)
  const enrolled = self ? self.status !== "available" && self.status !== "locked" : false
  const completed = self?.status === "completed"

  async function handleStart() {
    if (!moduleId) return
    setEnrolling(true)
    setError(null)
    try {
      await api.post(`/modules/${moduleId}/enroll`)
      // Refrescamos el estado real desde el servidor en vez de asumirlo:
      // el backend aplica bloqueo secuencial y podría rechazar la
      // inscripción, y fingir "inscrito" en local dejaría la UI mintiendo.
      const progressData = await api.get<CertificationProgress>(`/levels/${LEVEL_CODE}/certification-progress`)
      setSiblings(progressData.modules)
      setTab("practica")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo empezar el módulo.")
    } finally {
      setEnrolling(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Abriendo el módulo...
      </div>
    )
  }

  if (!module) {
    return <div className="text-red-500">{error ?? "Módulo no encontrado."}</div>
  }

  const TABS: { id: Tab; label: string; icon: typeof faBookOpen; count?: number }[] = [
    { id: "leccion", label: "Lección", icon: faBookOpen },
    { id: "practica", label: "Práctica", icon: faComments, count: module.tasks.length },
    { id: "examen", label: "Examen", icon: faClipboardCheck },
  ]

  return (
    <div className="space-y-6">
      {/* ---- Cabecera oscura del aula ---- */}
      <header className="relative overflow-hidden rounded-3xl bg-slate-900 p-5 text-white shadow-lg sm:p-7">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-blue-500/20 blur-3xl"
        />
        <div className="relative">
          <div className="flex items-center justify-between gap-3">
            <Link
              to="/classroom"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-sm transition hover:bg-white/20"
              title="Volver al classroom"
            >
              <FontAwesomeIcon icon={faXmark} />
            </Link>

            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-300">
              <NavArrow to={prev} direction="prev" />
              <span>
                Módulo {position} de {total || "—"}
              </span>
              <NavArrow to={next} direction="next" />
            </div>

            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-400 text-xs font-black text-slate-900">
              {LEVEL_CODE}
            </span>
          </div>

          <div className="mt-4 text-center">
            <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{module.title}</h1>
            <p className="mt-1 text-sm text-slate-300">{module.title_es}</p>
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-[11px] font-semibold uppercase tracking-wide">
              <span className="rounded-full bg-white/10 px-3 py-1 text-slate-200">{module.estimated_hours} h</span>
              <span className="rounded-full bg-white/10 px-3 py-1 text-slate-200">
                {module.descriptors.length} descriptores
              </span>
              {completed && (
                <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-emerald-300">
                  <FontAwesomeIcon icon={faCircleCheck} className="mr-1" /> Completado
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ---- Pestañas ---- */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        {TABS.map((t) => {
          const active = tab === t.id
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex flex-col items-center gap-1.5 rounded-2xl border px-3 py-4 text-xs font-bold uppercase tracking-wide transition active:scale-[0.98] ${
                active
                  ? "border-blue-600 bg-blue-600 text-white shadow-md shadow-blue-600/20"
                  : "border-slate-200 bg-white text-slate-400 hover:border-slate-300 hover:text-slate-600"
              }`}
            >
              <FontAwesomeIcon icon={t.icon} className="text-base" />
              {t.label}
              {t.count !== undefined && (
                <span className={`text-[10px] font-semibold ${active ? "text-blue-100" : "text-slate-400"}`}>
                  {t.count} {t.count === 1 ? "tarea" : "tareas"}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* ---- Barra de arranque / estado ---- */}
      {!enrolled && (
        <div className="flex flex-col gap-3 rounded-3xl border border-blue-200 bg-blue-50 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-bold text-slate-900">¿Listo para empezar este módulo?</p>
            <p className="mt-0.5 text-sm text-slate-600">
              Al empezar se activa tu progreso y desbloqueas la práctica con el tutor.
            </p>
          </div>
          <button
            onClick={handleStart}
            disabled={enrolling}
            className="flex shrink-0 items-center justify-center gap-2 rounded-full bg-blue-600 px-6 py-3 font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500 disabled:opacity-60"
          >
            {enrolling ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faBolt} />}
            Empezar módulo
          </button>
        </div>
      )}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {/* ---- Contenido ---- */}
      {tab === "leccion" && <LessonTab module={module} onGoPractice={() => setTab("practica")} />}
      {tab === "practica" && <PracticeTab module={module} enrolled={enrolled} onStart={handleStart} />}
      {tab === "examen" && <ExamTab module={module} />}

      {/* ---- Navegación entre módulos ---- */}
      <div className="flex items-center justify-between gap-3 border-t border-slate-200 pt-6">
        {prev && prev.status !== "locked" ? (
          <button
            onClick={() => navigate(`/modules/${prev.id}`)}
            className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-600 transition active:scale-[0.98] hover:bg-slate-50"
          >
            <FontAwesomeIcon icon={faArrowLeft} className="text-xs" /> Anterior
          </button>
        ) : (
          <span />
        )}
        {next &&
          (next.status === "locked" ? (
            <span className="flex items-center gap-2 rounded-full bg-slate-100 px-5 py-2.5 text-sm font-semibold text-slate-400">
              <FontAwesomeIcon icon={faLock} className="text-xs" /> Completa este módulo
            </span>
          ) : (
            <button
              onClick={() => navigate(`/modules/${next.id}`)}
              className="flex items-center gap-2 rounded-full bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800"
            >
              Siguiente <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </button>
          ))}
      </div>
    </div>
  )
}

function NavArrow({ to, direction }: { to?: ModuleProgress; direction: "prev" | "next" }) {
  const navigate = useNavigate()
  const disabled = !to || to.status === "locked"
  return (
    <button
      onClick={() => to && navigate(`/modules/${to.id}`)}
      disabled={disabled}
      className={`flex h-6 w-6 items-center justify-center rounded-full transition ${
        disabled ? "cursor-not-allowed bg-white/5 text-slate-600" : "bg-white/10 text-white hover:bg-white/20"
      }`}
      title={disabled ? "No disponible" : direction === "prev" ? "Módulo anterior" : "Módulo siguiente"}
    >
      <FontAwesomeIcon icon={direction === "prev" ? faArrowLeft : faArrowRight} className="text-[10px]" />
    </button>
  )
}

/* ------------------------- Pestaña: Lección ------------------------- */

function LessonTab({ module, onGoPractice }: { module: ModuleDetail; onGoPractice: () => void }) {
  return (
    <div className="space-y-4">
      {module.communicative_objectives.length > 0 && (
        <Card title="Al terminar este módulo sabrás" icon={faCircleCheck}>
          <ul className="space-y-2.5">
            {module.communicative_objectives.map((objective) => (
              <li key={objective} className="flex items-start gap-3 text-slate-700">
                <FontAwesomeIcon icon={faCircleCheck} className="mt-1 shrink-0 text-emerald-500" />
                {objective}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {module.lexis.chunks && module.lexis.chunks.length > 0 && (
        <Card title="Frases que debes automatizar" icon={faQuoteLeft}>
          <p className="mb-3 text-sm text-slate-500">
            No las analices: apréndelas como bloques. Es así como se producen sin pensar.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {module.lexis.chunks.map((chunk) => (
              <p
                key={chunk}
                className="rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 font-medium text-blue-800"
              >
                “{chunk}”
              </p>
            ))}
          </div>
        </Card>
      )}

      {module.grammar.focus && module.grammar.focus.length > 0 && (
        <Card title="Gramática al servicio de lo que quieres decir" icon={faBookOpen}>
          <ul className="list-inside list-disc space-y-1.5 text-slate-600">
            {module.grammar.focus.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {module.grammar.note && (
            <p className="mt-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm italic text-slate-500">{module.grammar.note}</p>
          )}
        </Card>
      )}

      {module.l1_interference.length > 0 && (
        <Card title="Errores que vas a cometer (y cómo evitarlos)" icon={faTriangleExclamation}>
          <p className="mb-3 text-sm text-slate-500">
            Anticipados porque piensas en español. Tu tutor los vigila mientras hablas.
          </p>
          <div className="grid gap-2.5 lg:grid-cols-2">
            {module.l1_interference.map((item) => (
              <div key={item.error} className="rounded-2xl border border-slate-200 p-4">
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${SEVERITY_STYLES[item.severity]}`}>
                  {item.severity}
                </span>
                <p className="mt-2 font-mono text-sm">
                  <span className="text-red-500 line-through decoration-red-300">{item.error}</span>
                  <span className="mx-2 text-slate-300">→</span>
                  <span className="font-semibold text-emerald-600">{item.target}</span>
                </p>
                <p className="mt-1.5 text-xs text-slate-400">Viene de: {item.origin}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {module.pronunciation.focus && (
        <Card title="Pronunciación" icon={faVolumeHigh}>
          <p className="text-slate-700">{module.pronunciation.focus}</p>
          {module.pronunciation.l1_alerts && module.pronunciation.l1_alerts.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {module.pronunciation.l1_alerts.map((alert) => (
                <li key={alert} className="flex items-start gap-2 text-sm text-amber-700">
                  <FontAwesomeIcon icon={faTriangleExclamation} className="mt-0.5 shrink-0 text-amber-500" />
                  {alert}
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {module.lessons.length > 0 && (
        <Card title="Lecciones narradas" icon={faHeadphones}>
          <ul className="space-y-2">
            {module.lessons.map((lesson) => (
              <li key={lesson.id} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                {lesson.order}. {lesson.title}
                {lesson.audio_duration_seconds && (
                  <span className="ml-2 text-xs text-slate-400">
                    {Math.round(lesson.audio_duration_seconds)}s de audio
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <button
        onClick={onGoPractice}
        className="flex w-full items-center justify-center gap-2 rounded-3xl bg-slate-900 px-6 py-4 font-bold text-white transition active:scale-[0.98] hover:bg-slate-800"
      >
        Ya lo tengo — ir a la práctica
        <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
      </button>
    </div>
  )
}

/* ------------------------- Pestaña: Práctica ------------------------ */

function PracticeTab({
  module,
  enrolled,
  onStart,
}: {
  module: ModuleDetail
  enrolled: boolean
  onStart: () => void
}) {
  if (module.tasks.length === 0) {
    return (
      <EmptyState
        icon={faComments}
        title="Este módulo aún no tiene tareas"
        text="El currículo de este módulo no declara tareas comunicativas todavía."
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-3xl border border-slate-200 bg-white p-5">
        <p className="text-sm text-slate-600">
          Aquí es donde de verdad aprendes: cada tarea es una conversación real con tu tutor. Completarlas suma
          evidencia hacia tus descriptores MCER — y esa evidencia es la que se convierte en horas certificadas.
        </p>
      </div>

      {module.tasks.map((task, i) => (
        <div key={task.id} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
              {i + 1}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-500">
              {task.type.replace(/_/g, " ")}
            </span>
            <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-blue-700">
              {task.descriptor}
            </span>
          </div>

          <p className="mt-3 text-slate-800">{task.prompt}</p>

          {task.success_criteria && (
            <p className="mt-3 flex items-start gap-2 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <FontAwesomeIcon icon={faCircleCheck} className="mt-0.5 shrink-0" />
              Lo logras si: {task.success_criteria}
            </p>
          )}

          {enrolled ? (
            <Link
              to={`/chat?module=${module.id}&task=${task.id}`}
              className="mt-4 flex items-center justify-center gap-2 rounded-full bg-blue-600 px-6 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500"
            >
              <FontAwesomeIcon icon={faComments} />
              Practicar con el tutor
            </Link>
          ) : (
            <button
              onClick={onStart}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-slate-900 px-6 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800"
            >
              <FontAwesomeIcon icon={faBolt} />
              Empezar el módulo para practicar
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

/* -------------------------- Pestaña: Examen ------------------------- */

function ExamTab({ module }: { module: ModuleDetail }) {
  const gate = module.assessment.gate_descriptors ?? []
  const required = module.assessment.evidence_required

  return (
    <div className="space-y-4">
      <Card title="Cómo se aprueba este módulo" icon={faClipboardCheck}>
        <p className="text-slate-600">
          No hay un examen de una sola vez. El módulo se supera acumulando evidencia: demostrar cada capacidad clave en
          contextos y sesiones distintas, practicando con tu tutor.
        </p>
        {required && (
          <p className="mt-4 flex items-center gap-2 rounded-2xl bg-blue-50 px-4 py-3 text-sm font-medium text-blue-800">
            <FontAwesomeIcon icon={faCircleCheck} />
            Se requieren {required} demostraciones exitosas por capacidad.
          </p>
        )}
        {gate.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Capacidades que se evalúan</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {gate.map((code) => (
                <span key={code} className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
                  {code}
                </span>
              ))}
            </div>
          </div>
        )}
        <Link
          to="/progress"
          className="mt-5 flex items-center justify-center gap-2 rounded-full bg-slate-900 px-6 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800"
        >
          Ver mi evidencia acumulada
          <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
        </Link>
      </Card>

      <EmptyState
        icon={faClipboardCheck}
        title="Sin ejercicios calificados todavía"
        text="Este módulo aún no tiene ejercicios de examen cargados. Mientras tanto, la práctica con el tutor es la que suma evidencia."
      />
    </div>
  )
}

/* ----------------------------- Comunes ------------------------------ */

function Card({ title, icon, children }: { title: string; icon?: typeof faBookOpen; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 flex items-center gap-2.5 text-lg font-bold tracking-tight text-slate-900">
        {icon && (
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-sm text-blue-600">
            <FontAwesomeIcon icon={icon} />
          </span>
        )}
        {title}
      </h2>
      {children}
    </section>
  )
}

function EmptyState({ icon, title, text }: { icon: typeof faBookOpen; title: string; text: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <FontAwesomeIcon icon={icon} className="text-2xl text-slate-300" />
      <p className="mt-3 font-semibold text-slate-700">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{text}</p>
    </div>
  )
}
