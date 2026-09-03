import { faCircleCheck, faCircleXmark, faSpinner, faTrophy } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { api } from "../api/client"
import type { CertificationResult, DescriptorMasterySummary, LevelExitGate } from "../api/types"
import { ApiError } from "../api/types"

const LEVEL_CODE = "A1" // único nivel con currículo sembrado hoy

export default function ProgressPage() {
  const [descriptors, setDescriptors] = useState<DescriptorMasterySummary | null>(null)
  const [gate, setGate] = useState<LevelExitGate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [certifying, setCertifying] = useState(false)
  const [certifyResult, setCertifyResult] = useState<CertificationResult | null>(null)

  async function loadAll() {
    setError(null)
    try {
      const [descriptorData, gateData] = await Promise.all([
        api.get<DescriptorMasterySummary>(`/users/me/progress/descriptors/${LEVEL_CODE}`),
        api.get<LevelExitGate>(`/users/me/progress/level-exit/${LEVEL_CODE}`),
      ])
      setDescriptors(descriptorData)
      setGate(gateData)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar tu progreso.")
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
      await loadAll()
    } catch (err) {
      if (err instanceof ApiError) setError(err.message)
      await loadAll()
    } finally {
      setCertifying(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Cargando tu progreso...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold text-slate-900">Tu progreso en {LEVEL_CODE}</h1>

      {descriptors && (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Descriptores MCER dominados</h2>
          <p className="mt-1 text-sm text-slate-500">
            {descriptors.mastered} de {descriptors.total} ({descriptors.percentage}%) — dominado a partir de mastery ≥{" "}
            {descriptors.threshold}
          </p>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-blue-600" style={{ width: `${descriptors.percentage}%` }} />
          </div>

          <ul className="mt-4 space-y-1.5">
            {descriptors.descriptors.map((d) => (
              <li key={d.code} className="flex items-center gap-2 text-sm">
                <FontAwesomeIcon
                  icon={d.is_mastered ? faCircleCheck : faCircleXmark}
                  className={d.is_mastered ? "text-emerald-500" : "text-slate-300"}
                />
                <span className={`flex-1 ${d.is_mastered ? "text-slate-700" : "text-slate-400"}`}>{d.statement_es}</span>
                {d.priority === "critical" && (
                  <span className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-500">crítico</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {gate && (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Gate de salida de nivel</h2>
            {gate.eligible && (
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
                <FontAwesomeIcon icon={faTrophy} /> Listo
              </span>
            )}
          </div>

          <ul className="mt-3 space-y-2">
            {gate.criteria.map((criterion) => (
              <li key={criterion.key} className="flex items-start gap-2 text-sm">
                <FontAwesomeIcon
                  icon={criterion.met ? faCircleCheck : faCircleXmark}
                  className={`mt-0.5 shrink-0 ${criterion.met ? "text-emerald-500" : "text-slate-300"}`}
                />
                <span className={criterion.met ? "text-slate-700" : "text-slate-400"}>{criterion.label}</span>
              </li>
            ))}
          </ul>

          {certifyResult ? (
            <div className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              🎉 Nivel {certifyResult.level_code} certificado.
              {certifyResult.next_level_code && ` Ahora estás trabajando en ${certifyResult.next_level_code}.`}
            </div>
          ) : (
            <button
              onClick={handleCertify}
              disabled={!gate.eligible || certifying}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            >
              {certifying && <FontAwesomeIcon icon={faSpinner} spin />}
              Certificar mi nivel
            </button>
          )}
        </div>
      )}

      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  )
}
