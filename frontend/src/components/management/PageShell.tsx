import { faCircleExclamation, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { ReactNode } from "react"

/** Cabecera de cada pestaña del panel (título, qué responde, filtros) y
 * los estados de carga/error. Los filtros van en UNA fila encima de todo
 * lo que filtran, nunca dentro de una tarjeta. */
export default function PageShell({
  title,
  question,
  filters,
  loading,
  error,
  hasData,
  children,
}: {
  title: string
  question: string
  filters?: ReactNode
  loading: boolean
  error: string | null
  hasData: boolean
  children: ReactNode
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{question}</p>
        </div>
        {filters && <div className="flex flex-wrap items-center gap-3">{filters}</div>}
      </div>

      {error && (
        <p className="flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <FontAwesomeIcon icon={faCircleExclamation} />
          {error}
        </p>
      )}

      {!hasData && loading && (
        <div className="flex items-center justify-center py-24 text-slate-400">
          <FontAwesomeIcon icon={faSpinner} spin className="mr-2" />
          Cargando…
        </div>
      )}

      {hasData && (
        <div className={`space-y-6 transition-opacity ${loading ? "opacity-50" : ""}`} aria-busy={loading}>
          {children}
        </div>
      )}
    </div>
  )
}
