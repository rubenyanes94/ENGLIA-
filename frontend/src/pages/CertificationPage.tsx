import {
  faCheck,
  faCircleCheck,
  faCircleXmark,
  faLock,
  faSpinner,
  faTrophy,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { CertificationProgress, CertificationResult, DescriptorMasterySummary, LevelExitGate, ModuleProgress } from "../api/types"
import { ApiError } from "../api/types"

const LEVEL_CODE = "A1" // único nivel con currículo sembrado hoy — ver seed_a1_modules.py

const STATUS_STYLES: Record<ModuleProgress["status"], { label: string; classes: string; icon: typeof faLock }> = {
  locked: { label: "Bloqueado", classes: "border-slate-800 bg-slate-900/50 text-slate-500", icon: faLock },
  available: { label: "Disponible", classes: "border-slate-700 bg-slate-900 text-slate-200", icon: faCircleCheck },
  in_progress: { label: "En progreso", classes: "border-amber-600/40 bg-amber-500/5 text-amber-300", icon: faSpinner },
  completed: { label: "Completado", classes: "border-emerald-600/40 bg-emerald-500/5 text-emerald-300", icon: faCheck },
}

export default function CertificationPage() {
  const [progress, setProgress] = useState<CertificationProgress | null>(null)
  const [descriptors, setDescriptors] = useState<DescriptorMasterySummary | null>(null)
  const [gate, setGate] = useState<LevelExitGate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [certifying, setCertifying] = useState(false)
  const [certifyResult, setCertifyResult] = useState<CertificationResult | null>(null)

  async function loadAll() {
    setError(null)
    try {
      const [progressData, descriptorData, gateData] = await Promise.all([
        api.get<CertificationProgress>(`/levels/${LEVEL_CODE}/certification-progress`),
        api.get<DescriptorMasterySummary>(`/users/me/progress/descriptors/${LEVEL_CODE}`),
        api.get<LevelExitGate>(`/users/me/progress/level-exit/${LEVEL_CODE}`),
      ])
      setProgress(progressData)
      setDescriptors(descriptorData)
      setGate(gateData)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la certificación.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAll()
  }, [])

  async function handleCertify() {
    setCertifying(true)
    setError(null)
    try {
      const result = await api.post<CertificationResult>(`/users/me/certify/${LEVEL_CODE}`)
      setCertifyResult(result)
      await loadAll() // refresca el gate/descriptores tras certificar
    } catch (err) {
      // El 409 del backend ya trae el detalle por criterio — lo mostramos
      // recargando el gate en vez de solo un mensaje genérico.
      if (err instanceof ApiError) setError(err.message)
      await loadAll()
    } finally {
      setCertifying(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Cargando certificación...
      </div>
    )
  }

  if (!progress) {
    return <div className="text-red-400">{error ?? "No se pudo cargar la certificación."}</div>
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold">Certificación {progress.level_code}</h1>
        <p className="mt-1 text-slate-400">
          {progress.hours_completed}h de {progress.target_hours_min}–{progress.target_hours_max}h objetivo
        </p>
        <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{ width: `${Math.min(progress.percentage, 100)}%` }}
          />
        </div>
        <p className="mt-1 text-sm text-slate-500">{progress.percentage}% del objetivo de horas</p>
      </section>

      {descriptors && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="mb-1 text-lg font-semibold">Descriptores MCER dominados</h2>
          <p className="text-sm text-slate-400">
            {descriptors.mastered} de {descriptors.total} ({descriptors.percentage}%) — dominado a partir de mastery ≥{" "}
            {descriptors.threshold}
          </p>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-sky-500" style={{ width: `${descriptors.percentage}%` }} />
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Módulos</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {progress.modules.map((module) => {
            const style = STATUS_STYLES[module.status]
            const clickable = module.status !== "locked"
            const card = (
              <div className={`rounded-xl border p-4 transition ${style.classes} ${clickable ? "hover:border-slate-600" : ""}`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-slate-500">{module.code}</span>
                  <span className="flex items-center gap-1 text-xs">
                    <FontAwesomeIcon icon={style.icon} spin={module.status === "in_progress"} />
                    {style.label}
                  </span>
                </div>
                <h3 className="mt-1 font-semibold">{module.title}</h3>
                <p className="text-sm text-slate-400">{module.title_es}</p>
                <p className="mt-2 text-xs text-slate-500">{module.estimated_hours}h · {module.descriptors.length} descriptores</p>
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
      </section>

      {gate && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Gate de salida de nivel</h2>
            {gate.eligible ? (
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-sm text-emerald-400">
                <FontAwesomeIcon icon={faTrophy} /> Listo para certificar
              </span>
            ) : (
              <span className="text-sm text-slate-500">Todavía no</span>
            )}
          </div>

          <ul className="mt-4 space-y-2">
            {gate.criteria.map((criterion) => (
              <li key={criterion.key} className="flex items-start gap-2 text-sm">
                <FontAwesomeIcon
                  icon={criterion.met ? faCircleCheck : faCircleXmark}
                  className={`mt-0.5 shrink-0 ${criterion.met ? "text-emerald-400" : "text-slate-600"}`}
                />
                <span className={criterion.met ? "text-slate-300" : "text-slate-500"}>{criterion.label}</span>
              </li>
            ))}
          </ul>

          {certifyResult ? (
            <div className="mt-4 rounded-lg bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
              🎉 Nivel {certifyResult.level_code} certificado.
              {certifyResult.next_level_code && ` Ahora estás trabajando en ${certifyResult.next_level_code}.`}
            </div>
          ) : (
            <button
              onClick={handleCertify}
              disabled={!gate.eligible || certifying}
              className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {certifying && <FontAwesomeIcon icon={faSpinner} spin />}
              Certificar mi nivel
            </button>
          )}

          {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        </section>
      )}
    </div>
  )
}
