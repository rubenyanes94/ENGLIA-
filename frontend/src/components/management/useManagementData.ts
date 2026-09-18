import { useCallback, useEffect, useState } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"

/** Carga un endpoint del panel y lo recarga cuando cambia la ruta (p. ej.
 * al cambiar de periodo). Mientras recarga, CONSERVA los datos anteriores
 * (`loading` sirve para atenuarlos): sin parpadeos ni saltos de altura
 * cada vez que se toca el selector.
 *
 * `refreshMs` (opcional) la vuelve a pedir sola cada N ms — el panel de
 * Sistema se deja abierto en una pantalla y tiene que reflejar el estado
 * de AHORA. `reload()` fuerza una recarga manual. */
export function useManagementData<T>(path: string, options: { refreshMs?: number } = {}) {
  const { refreshMs } = options
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .get<T>(path)
      .then((d) => {
        if (cancelled) return
        setData(d)
        setUpdatedAt(new Date())
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "No se pudieron cargar los datos.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [path, tick])

  useEffect(() => {
    if (!refreshMs) return
    const id = setInterval(reload, refreshMs)
    return () => clearInterval(id)
  }, [refreshMs, reload])

  return { data, loading, error, reload, updatedAt }
}
