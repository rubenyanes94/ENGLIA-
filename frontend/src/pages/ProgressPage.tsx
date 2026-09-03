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
    <div className="space-y-8">
      <h1 className="text-3xl font-extrabold text-slate-900 lg:text-4xl">Tu progreso en {LEVEL_CODE}</h1>

      {/* Dos columnas en escritorio: el catálogo de descriptores es largo
          (35 filas) y el gate es un panel corto de decisión — ponerlos en
          columna única desktop dejaría el gate enterrado tras un scroll
          enorme. En móvil vuelven a apilarse. */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {descriptors && (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2 lg:p-8">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Descriptores MCER dominados</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {descriptors.mastered} de {descriptors.total} — dominado a partir de mastery ≥ {descriptors.threshold}
                </p>
              </div>
              <span className="text-2xl font-extrabold text-blue-600">{descriptors.percentage}%</span>
            </div>
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-blue-600" style={{ width: `${descriptors.percentage}%` }} />
            </div>

            <ul className="mt-6 grid grid-cols-1 gap-x-8 gap-y-2 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              {descriptors.descriptors.map((d) => (
                <li key={d.code} className="flex items-start gap-2 text-sm">
                  <FontAwesomeIcon
                    icon={d.is_mastered ? faCircleCheck : faCircleXmark}
                    className={`mt-0.5 shrink-0 ${d.is_mastered ? "text-emerald-500" : "text-slate-300"}`}
                  />
                  <span className={`flex-1 ${d.is_mastered ? "text-slate-700" : "text-slate-400"}`}>
                    {d.statement_es}
                  </span>
                  {d.priority === "critical" && (
                    <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-500">
                      crítico
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {gate && (
          <div className="h-fit rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:sticky lg:top-24">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900">Gate de salida</h2>
              {gate.eligible && (
                <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
                  <FontAwesomeIcon icon={faTrophy} /> Listo
                </span>
              )}
            </div>

            <ul className="mt-4 space-y-3">
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
              <div className="mt-5 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                🎉 Nivel {certifyResult.level_code} certificado.
                {certifyResult.next_level_code && ` Ahora estás trabajando en ${certifyResult.next_level_code}.`}
              </div>
            ) : (
              <button
                onClick={handleCertify}
                disabled={!gate.eligible || certifying}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
              >
                {certifying && <FontAwesomeIcon icon={faSpinner} spin />}
                Certificar mi nivel
              </button>
            )}

            {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
