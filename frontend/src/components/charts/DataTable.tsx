export interface TableData {
  columns: string[]
  rows: (string | number)[][]
  /** Índices de columnas numéricas: se alinean a la derecha con cifras tabulares. */
  numeric?: number[]
}

/** Vista de tabla de un gráfico. Cifras tabulares solo aquí, donde tienen
 * que alinearse en columna; en las tarjetas grandes van proporcionales. */
export default function DataTable({ data }: { data: TableData }) {
  const numeric = new Set(data.numeric ?? [])
  return (
    <div className="max-h-96 overflow-auto rounded-2xl border border-slate-100">
      <table className="w-full text-left text-sm">
        <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {data.columns.map((c, i) => (
              <th key={c} scope="col" className={`whitespace-nowrap px-3 py-2 font-semibold ${numeric.has(i) ? "text-right" : ""}`}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, i) => (
                <td
                  key={i}
                  className={`px-3 py-2 text-slate-700 ${numeric.has(i) ? "whitespace-nowrap text-right tabular-nums" : ""}`}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
          {data.rows.length === 0 && (
            <tr>
              <td colSpan={data.columns.length} className="px-3 py-6 text-center text-slate-400">
                Sin datos en este periodo.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
