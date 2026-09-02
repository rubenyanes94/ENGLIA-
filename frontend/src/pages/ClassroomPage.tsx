import { faCheck, faCircleCheck, faLock, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { CertificationProgress, ModuleProgress } from "../api/types"
import { ApiError } from "../api/types"

const LEVEL_CODE = "A1" // único nivel con currículo sembrado hoy — ver seed_a1_modules.py

const STATUS_STYLES: Record<ModuleProgress["status"], { label: string; classes: string; icon: typeof faLock }> = {
  locked: { label: "Bloqueado", classes: "border-slate-200 bg-slate-100 text-slate-400", icon: faLock },
  available: { label: "Disponible", classes: "border-slate-200 bg-white text-slate-700", icon: faCircleCheck },
  in_progress: { label: "En progreso", classes: "border-amber-300 bg-amber-50 text-amber-700", icon: faSpinner },
  completed: { label: "Completado", classes: "border-emerald-300 bg-emerald-50 text-emerald-700", icon: faCheck },
}

/** El "classroom": el mapa de módulos de un nivel, con bloqueo
 * secuencial visible (ver GET /levels/{code}/certification-progress). Es
 * donde el alumno abre cada módulo — el dominio de descriptores y el gate
 * de salida viven aparte, en ProgressPage. */
export default function ClassroomPage() {
  const [progress, setProgress] = useState<CertificationProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<CertificationProgress>(`/levels/${LEVEL_CODE}/certification-progress`)
      .then(setProgress)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar el classroom."))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Cargando classroom...
      </div>
    )
  }

  if (!progress) {
    return <div className="text-red-500">{error ?? "No se pudo cargar el classroom."}</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">Classroom {progress.level_code}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {progress.hours_completed}h de {progress.target_hours_min}–{progress.target_hours_max}h objetivo
        </p>
        <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full bg-blue-600 transition-all"
            style={{ width: `${Math.min(progress.percentage, 100)}%` }}
          />
        </div>
      </div>

      <div className="space-y-3">
        {progress.modules.map((module) => {
          const style = STATUS_STYLES[module.status]
          const clickable = module.status !== "locked"
          const card = (
            <div className={`rounded-2xl border p-4 shadow-sm transition ${style.classes} ${clickable ? "hover:border-blue-300" : ""}`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400">{module.code}</span>
                <span className="flex items-center gap-1 text-xs font-semibold">
                  <FontAwesomeIcon icon={style.icon} spin={module.status === "in_progress"} />
                  {style.label}
                </span>
              </div>
              <h3 className="mt-1 font-semibold text-slate-900">{module.title}</h3>
              <p className="text-sm text-slate-500">{module.title_es}</p>
              <p className="mt-2 text-xs text-slate-400">
                {module.estimated_hours}h · {module.descriptors.length} descriptores
              </p>
            </div>
          )
          return clickable ? (
            <Link key={module.id} to={`/modules/${module.id}`}>
              {card}
            </Link>
          ) : (
            <div key={module.id}>{card}</div>
          )
        })}
      </div>
    </div>
  )
}
