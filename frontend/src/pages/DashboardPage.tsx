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

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Bienvenido de vuelta</p>
        <h1 className="text-2xl font-extrabold text-slate-900">¡Hola, {firstName}!</h1>
      </div>

      {loading ? (
        <div className="h-40 animate-pulse rounded-3xl bg-slate-200" />
      ) : progress ? (
        <Link
          to="/classroom"
          className="block rounded-3xl bg-gradient-to-br from-blue-600 to-blue-500 p-5 text-white shadow-md"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-100">Tu meta actual</p>
              <p className="mt-1 text-2xl font-extrabold">Nivel {progress.level_code}</p>
              <p className="text-xs text-blue-100">Certificación MCER</p>
            </div>
            <CircularProgress percentage={progress.percentage} />
          </div>
          <p className="mt-4 flex items-center gap-1 text-sm font-semibold">
            Ver classroom <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
          </p>
        </Link>
      ) : (
        <p className="text-sm text-slate-500">No se pudo cargar tu progreso.</p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <StatCard icon={faClock} value={progress ? `${progress.hours_completed}h` : "—"} label="Horas certificadas" />
        <StatCard
          icon={faChartLine}
          value={descriptors ? `${descriptors.mastered}/${descriptors.total}` : "—"}
          label="Descriptores dominados"
        />
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          <FontAwesomeIcon icon={faComments} /> Tu tutor de IA
        </p>
        <p className="text-sm text-slate-500">
          Conversa en inglés con corrección adaptada a tu nivel y a los errores típicos de un hispanohablante.
        </p>
        <Link
          to="/chat"
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800"
        >
          Continuar con tu tutor
        </Link>
      </div>

      {nextModule && (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            <FontAwesomeIcon icon={faBookOpen} />
            {nextModule.status === "in_progress" ? "Continúa donde lo dejaste" : "Siguiente módulo"}
          </p>
          <h3 className="font-semibold text-slate-900">{nextModule.title}</h3>
          <p className="text-sm text-slate-500">{nextModule.title_es}</p>
          <Link
            to={`/modules/${nextModule.id}`}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500"
          >
            Abrir módulo
          </Link>
        </div>
      )}
    </div>
  )
}

function StatCard({ icon, value, label }: { icon: typeof faClock; value: string; label: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <FontAwesomeIcon icon={icon} className="text-blue-500" />
      <p className="mt-2 text-xl font-extrabold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  )
}
