import {
  faArrowRight,
  faBolt,
  faBookOpen,
  faChartLine,
  faCircleCheck,
  faClock,
  faComments,
  faGraduationCap,
  faRobot,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { CertificationProgress, DescriptorMasterySummary, ModuleDetail, Task, Tutor } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import AppFooter from "../components/AppFooter"
import Avatar from "../components/Avatar"
import CircularProgress from "../components/CircularProgress"

// Único nivel con currículo sembrado hoy. Si el alumno todavía no
// certificó nada, current_level_code viene null (ver models/user.py) —
// en ese caso, A1 es el punto de partida real de todo alumno nuevo.
const LEVEL_CODE = "A1"

export default function DashboardPage() {
  const { user } = useAuth()
  const [progress, setProgress] = useState<CertificationProgress | null>(null)
  const [descriptors, setDescriptors] = useState<DescriptorMasterySummary | null>(null)
  const [tutor, setTutor] = useState<Tutor | null>(null)
  const [activeModule, setActiveModule] = useState<ModuleDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.get<CertificationProgress>(`/levels/${LEVEL_CODE}/certification-progress`),
      api.get<DescriptorMasterySummary>(`/users/me/progress/descriptors/${LEVEL_CODE}`),
      api.get<Tutor>(`/levels/${LEVEL_CODE}/tutor`).catch(() => null),
    ])
      .then(async ([progressData, descriptorData, tutorData]) => {
        setProgress(progressData)
        setDescriptors(descriptorData)
        setTutor(tutorData)

        // El módulo activo se pide APARTE (y solo uno) porque la práctica
        // del día sale de sus `tasks`, que el listado de módulos no trae
        // — ModuleOut es la "tarjeta", las tareas viven en ModuleDetailOut.
        const next =
          progressData.modules.find((m) => m.status === "in_progress") ??
          progressData.modules.find((m) => m.status === "available")
        if (next) {
          setActiveModule(await api.get<ModuleDetail>(`/modules/${next.id}`).catch(() => null))
        }
      })
      .catch(() => {
        setProgress(null)
        setDescriptors(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const firstName = user?.full_name.split(" ")[0] ?? ""
  const nextModule =
    progress?.modules.find((m) => m.status === "in_progress") ?? progress?.modules.find((m) => m.status === "available")
  const completedCount = progress?.modules.filter((m) => m.status === "completed").length ?? 0
  const moduleIndex = nextModule ? nextModule.order : 1
  const moduleTotal = progress?.modules.length ?? 0

  // La "práctica de hoy" no es contenido generado: es una tarea REAL del
  // módulo activo (Module.tasks del currículo). Se rota por día del año
  // para que cambie a diario de forma estable — el mismo día muestra
  // siempre la misma, en vez de bailar en cada recarga.
  const dailyTask: Task | undefined = activeModule?.tasks.length
    ? activeModule.tasks[dayOfYear() % activeModule.tasks.length]
    : undefined

  return (
    <div>
      <div className="space-y-8">
        {/* Saludo con foto de perfil */}
        <div className="flex items-center gap-4">
          <Avatar name={user?.full_name ?? ""} avatarUrl={user?.avatar_url} size={56} />
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Bienvenido de vuelta</p>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 lg:text-3xl">¡Hola, {firstName}!</h1>
          </div>
        </div>

        {/* Nivel + métricas */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {loading ? (
            <div className="h-48 animate-pulse rounded-3xl bg-slate-200 lg:col-span-2" />
          ) : progress ? (
            <Link
              to="/classroom"
              className="group flex flex-col justify-between rounded-3xl bg-gradient-to-br from-blue-600 to-blue-500 p-6 text-white shadow-lg shadow-blue-600/20 transition hover:shadow-xl lg:col-span-2 lg:p-8"
            >
              <div className="flex items-start justify-between gap-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-100">Tu meta actual</p>
                  <p className="mt-2 text-3xl font-extrabold lg:text-4xl">Nivel {progress.level_code}</p>
                  <p className="mt-1 text-sm text-blue-100">Certificación MCER</p>
                  <p className="mt-4 text-sm text-blue-50">
                    {progress.hours_completed}h de {progress.target_hours_min}–{progress.target_hours_max}h ·{" "}
                    {completedCount}/{moduleTotal} módulos completados
                  </p>
                </div>
                <CircularProgress percentage={progress.percentage} size={88} strokeWidth={7} />
              </div>
              <p className="mt-6 flex items-center gap-2 text-sm font-semibold">
                Ver classroom
                <FontAwesomeIcon icon={faArrowRight} className="text-xs transition group-hover:translate-x-1" />
              </p>
            </Link>
          ) : (
            <p className="text-sm text-slate-500 lg:col-span-2">No se pudo cargar tu progreso.</p>
          )}

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-1">
            <StatCard icon={faClock} value={progress ? `${progress.hours_completed}h` : "—"} label="Horas certificadas" />
            <StatCard
              icon={faChartLine}
              value={descriptors ? `${descriptors.mastered}/${descriptors.total}` : "—"}
              label="Descriptores dominados"
            />
          </div>
        </div>

        {/* Tutor + práctica del día */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Tarjeta de tutor: oscura y destacada, es la acción principal
              de la pantalla. Los datos son reales — el nombre sale de
              GET /levels/{code}/tutor (AgentPersona en base de datos), no
              de una constante. */}
          <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 p-6 text-white shadow-lg lg:p-7">
            <div
              aria-hidden
              className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-blue-500/20 blur-2xl"
            />
            <div className="relative">
              <div className="flex items-center gap-4">
                <span className="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-sky-400 text-2xl font-black shadow-lg">
                  <FontAwesomeIcon icon={faRobot} />
                  <span className="absolute -bottom-1.5 rounded-full bg-emerald-500 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white shadow">
                    IA
                  </span>
                </span>
                <div className="min-w-0">
                  <h2 className="truncate text-xl font-extrabold tracking-tight">
                    {tutor?.name ?? "Tu tutor de IA"}
                  </h2>
                  <p className="mt-0.5 text-xs font-semibold uppercase tracking-wide text-blue-300">
                    Módulo {moduleIndex} de {moduleTotal || "—"}
                  </p>
                </div>
              </div>

              {/* Solo capacidades que el producto tiene de verdad hoy:
                  es chat de texto, no voz ni vídeo. */}
              <div className="mt-5 flex flex-wrap gap-2">
                {["24/7 disponible", "Corrige al momento", "Adaptado a tu nivel"].map((badge) => (
                  <span
                    key={badge}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-300"
                  >
                    {badge}
                  </span>
                ))}
              </div>

              <Link
                to="/chat"
                className="mt-6 flex w-full items-center justify-center gap-2.5 rounded-2xl bg-white px-6 py-4 font-bold text-slate-900 transition active:scale-[0.98] hover:bg-slate-100"
              >
                <FontAwesomeIcon icon={faGraduationCap} />
                Continuar mi clase
              </Link>
            </div>
          </div>

          {/* Práctica del día: una tarea REAL del módulo activo. */}
          <div className="flex flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:p-7">
            <div className="flex items-center justify-between gap-3">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <FontAwesomeIcon icon={faBolt} className="text-amber-500" /> Práctica de hoy
              </p>
              {dailyTask && (
                <span className="rounded-full bg-amber-50 px-3 py-1 text-[11px] font-semibold text-amber-700">
                  {dailyTask.descriptor}
                </span>
              )}
            </div>

            {dailyTask ? (
              <>
                <p className="mt-4 flex-1 text-slate-700">{dailyTask.prompt}</p>
                {dailyTask.success_criteria && (
                  <p className="mt-3 flex items-start gap-2 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
                    <FontAwesomeIcon icon={faCircleCheck} className="mt-0.5 shrink-0 text-emerald-500" />
                    Lo logras si: {dailyTask.success_criteria}
                  </p>
                )}
                <p className="mt-3 text-xs text-slate-400">
                  Completar tareas suma evidencia hacia tus descriptores y, con ella, horas certificadas.
                </p>
                <Link
                  to={`/chat?module=${activeModule?.id}&task=${dailyTask.id}`}
                  className="mt-5 flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-6 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500"
                >
                  <FontAwesomeIcon icon={faComments} />
                  Practicar ahora
                </Link>
              </>
            ) : (
              <div className="flex flex-1 flex-col justify-center py-6">
                <p className="text-sm text-slate-500">
                  {loading
                    ? "Buscando tu práctica de hoy..."
                    : "Inscríbete en un módulo para recibir tu práctica diaria."}
                </p>
                {!loading && nextModule && (
                  <Link
                    to={`/modules/${nextModule.id}`}
                    className="mt-4 flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-6 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500"
                  >
                    Abrir {nextModule.title}
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Siguiente módulo */}
        {nextModule && (
          <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between lg:p-7">
            <div>
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                <FontAwesomeIcon icon={faBookOpen} />
                {nextModule.status === "in_progress" ? "Continúa donde lo dejaste" : "Siguiente módulo"}
              </p>
              <h3 className="mt-2 text-lg font-bold text-slate-900">{nextModule.title}</h3>
              <p className="text-sm text-slate-500">{nextModule.title_es}</p>
              <p className="mt-1 text-xs text-slate-400">
                {nextModule.estimated_hours}h · {nextModule.descriptors.length} descriptores
              </p>
            </div>
            <Link
              to={`/modules/${nextModule.id}`}
              className="flex shrink-0 items-center justify-center gap-2 rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800"
            >
              Abrir módulo
              <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </Link>
          </div>
        )}
      </div>

      <AppFooter />
    </div>
  )
}

/** Día del año (1-366). Sirve para rotar la práctica diaria de forma
 * estable: cambia cada día, pero no en cada recarga. */
function dayOfYear(): number {
  const now = new Date()
  const start = new Date(now.getFullYear(), 0, 0)
  return Math.floor((now.getTime() - start.getTime()) / 86_400_000)
}

function StatCard({ icon, value, label }: { icon: typeof faClock; value: string; label: string }) {
  return (
    <div className="flex flex-col justify-center rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <FontAwesomeIcon icon={icon} className="text-blue-500" />
      <p className="mt-2 text-2xl font-extrabold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  )
}
