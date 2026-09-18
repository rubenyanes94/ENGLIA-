import { faChartSimple, faTable } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState, type ReactNode } from "react"
import DataTable, { type TableData } from "./DataTable"

/** Contenedor de todo gráfico del panel: título, explicación de qué mide
 * y el botón de vista de tabla.
 *
 * La tabla no es un extra: es la forma de leer cada valor sin depender del
 * color ni de pasar el ratón (lectores de pantalla, daltonismo, copiar
 * cifras a un informe). Por eso la exige `table` y no es opcional. */
export default function ChartCard({
  title,
  description,
  table,
  children,
  className = "",
  aside,
}: {
  title: string
  description?: ReactNode
  table: TableData
  children: ReactNode
  className?: string
  aside?: ReactNode
}) {
  const [showTable, setShowTable] = useState(false)

  return (
    <figure className={`flex min-w-0 flex-col rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 ${className}`}>
      <figcaption className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-base font-bold text-slate-900">{title}</h3>
          {description && <p className="mt-1 text-sm leading-relaxed text-slate-500">{description}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {aside}
          <button
            type="button"
            onClick={() => setShowTable((v) => !v)}
            aria-pressed={showTable}
            title={showTable ? "Ver gráfico" : "Ver tabla"}
            className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <FontAwesomeIcon icon={showTable ? faChartSimple : faTable} />
            <span className="sr-only">{showTable ? "Ver gráfico" : "Ver tabla"}</span>
          </button>
        </div>
      </figcaption>
      <div className="mt-5 min-w-0 flex-1">{showTable ? <DataTable data={table} /> : children}</div>
    </figure>
  )
}
