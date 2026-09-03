import { faArrowRight, faBookOpen, faChartLine, faClock, faComments } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { CertificationProgress, DescriptorMasterySummary } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import CircularProgress from "../components/CircularProgress"

// Único nivel con currículo sembrado hoy. Si el alumno todavía no
// certificó nada, current_level_code viene null (ver models/user.py) —
// en ese caso, A1 es el punto de partida real de todo alumno nuevo, no
// una suposición: es el único nivel con módulos para inscribirse.
const FALLBACK_LEVEL_CODE = "A1"

export default function DashboardPage() {
  const { user } = useAuth()
  const [progress, setProgress] = useState<CertificationProgress | null>(null)
  const [descriptors, setDescriptors] = useState<DescriptorMasterySummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // user.current_level_id (cuando existe) apunta a un UUID, no a un
    // code — no podemos pedir /levels/{code}/... con eso directamente.
    // Como hoy SOLO A1 tiene currículo, usamos ese code siempre; el día
    // que haya más niveles con contenido, esto necesita resolver el code
    // real desde /users/me/progress (que sí trae current_level_code).
    setLoading(true)
    Promise.all([
      api.get<CertificationProgress>(`/levels/${FALLBACK_LEVEL_CODE}/certification-progress`),
      api.get<DescriptorMasterySummary>(`/users/me/progress/descriptors/${FALLBACK_LEVEL_CODE}`),
    ])
      .then(([progressData, descriptorData]) => {
        setProgress(progressData)
        setDescriptors(descriptorData)
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

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Bienvenido de vuelta</p>
        <h1 className="mt-1 text-3xl font-extrabold text-slate-900 lg:text-4xl">¡Hola, {firstName}!</h1>
      </div>

      {/* Rejilla principal: en escritorio, la tarjeta de nivel ocupa 2/3 y
          las métricas se apilan al lado; en móvil, todo en columna. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {loading ? (
          <div className="h-48 animate-pulse rounded-3xl bg-slate-200 lg:col-span-2" />
        ) : progress ? (
          <Link
            to="/classroom"
            className="group flex flex-col justify-between rounded-3xl bg-gradient-to-br from-blue-600 to-blue-500 p-6 text-white shadow-md transition hover:shadow-lg lg:col-span-2 lg:p-8"
          >
            <div className="flex items-start justify-between gap-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-100">Tu meta actual</p>
                <p className="mt-2 text-3xl font-extrabold lg:text-4xl">Nivel {progress.level_code}</p>
                <p className="mt-1 text-sm text-blue-100">Certificación MCER</p>
                <p className="mt-4 text-sm text-blue-50">
                  {progress.hours_completed}h de {progress.target_hours_min}–{progress.target_hours_max}h ·{" "}
                  {completedCount}/{progress.modules.length} módulos completados
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

      {/* Segunda fila: tutor y siguiente módulo, lado a lado en escritorio. */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            <FontAwesomeIcon icon={faComments} /> Tu tutor de IA
          </p>
          <p className="mt-3 flex-1 text-sm text-slate-500">
            Conversa en inglés con corrección adaptada a tu nivel y a los errores típicos de un hispanohablante.
          </p>
          <Link
            to="/chat"
            className="mt-5 flex items-center justify-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800"
          >
            Continuar con tu tutor
          </Link>
        </div>

        {nextModule ? (
          <div className="flex flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              <FontAwesomeIcon icon={faBookOpen} />
              {nextModule.status === "in_progress" ? "Continúa donde lo dejaste" : "Siguiente módulo"}
            </p>
            <div className="mt-3 flex-1">
              <h3 className="text-lg font-semibold text-slate-900">{nextModule.title}</h3>
              <p className="text-sm text-slate-500">{nextModule.title_es}</p>
              <p className="mt-2 text-xs text-slate-400">
                {nextModule.estimated_hours}h · {nextModule.descriptors.length} descriptores
              </p>
            </div>
            <Link
              to={`/modules/${nextModule.id}`}
              className="mt-5 flex items-center justify-center gap-2 rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500"
            >
              Abrir módulo
            </Link>
          </div>
        ) : (
          !loading && (
            <div className="flex flex-col items-start justify-center rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm text-slate-500">
                Has completado todos los módulos disponibles. Revisa tu progreso para certificar el nivel.
              </p>
              <Link to="/progress" className="mt-4 text-sm font-semibold text-blue-600 hover:text-blue-500">
                Ver mi progreso →
              </Link>
            </div>
          )
        )}
      </div>
    </div>
  )
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
