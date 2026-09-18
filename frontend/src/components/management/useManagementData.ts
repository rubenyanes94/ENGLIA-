import { useEffect, useState } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"

/** Carga un endpoint del panel y lo recarga cuando cambia la ruta (p. ej.
 * al cambiar de periodo). Mientras recarga, CONSERVA los datos anteriores
 * (`loading` sirve para atenuarlos): sin parpadeos ni saltos de altura
 * cada vez que se toca el selector. */
export function useManagementData<T>(path: string) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .get<T>(path)
      .then((d) => {
        if (!cancelled) setData(d)
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
  }, [path])

  return { data, loading, error }
}
