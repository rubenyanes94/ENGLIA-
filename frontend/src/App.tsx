import { faCircleCheck, faCircleXmark, faSpinner } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useEffect, useState } from 'react'

type HealthResponse = {
  status: string
  postgres: string
  redis: string
}

const BACKEND_PORT = '8000'
const FRONTEND_PORT = '5173'

/**
 * Calcula la URL del backend. Tres estrategias, en orden de confianza:
 *
 * 1. VITE_API_URL explícita (vía de escape manual).
 * 2. VITE_CODESPACE_NAME + VITE_PORT_FORWARDING_DOMAIN: variables que la
 *    propia VM de Codespaces ya conoce (CODESPACE_NAME,
 *    GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN) y que le pasamos al
 *    contenedor del frontend en docker-compose.yml. Con esto construimos
 *    la URL pública real del backend SIN mirar la URL del navegador, así
 *    que da igual si accedes por la URL https://...app.github.dev o si
 *    VS Code Desktop te está redirigiendo por un túnel a "localhost":
 *    siempre apuntamos al Codespace correcto.
 * 3. Fallback por si no hay nada de Codespaces (Docker Compose en tu
 *    propia máquina, sin más): mismo host del navegador, cambia el puerto.
 */
function resolveApiUrl(): string {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL

  const codespaceName = import.meta.env.VITE_CODESPACE_NAME
  const forwardingDomain = import.meta.env.VITE_PORT_FORWARDING_DOMAIN

  if (codespaceName && forwardingDomain) {
    return `https://${codespaceName}-${BACKEND_PORT}.${forwardingDomain}`
  }

  const { protocol, hostname } = window.location

  if (hostname.includes(`-${FRONTEND_PORT}.`)) {
    // Patrón de Codespaces / github.dev accedido directo por URL pública.
    return `${protocol}//${hostname.replace(`-${FRONTEND_PORT}.`, `-${BACKEND_PORT}.`)}`
  }

  // Docker Compose local, sin Codespaces de por medio.
  return `${protocol}//${hostname}:${BACKEND_PORT}`
}

const API_URL = resolveApiUrl()

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then(setHealth)
      .catch(() => setError('No se pudo conectar con el backend'))
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
        <h1 className="mb-1 text-2xl font-bold">English Academy 🇬🇧</h1>
        <p className="mb-6 text-slate-400">Comprobación de infraestructura (Paso 1)</p>

        {error && (
          <div className="flex items-center gap-2 text-red-400">
            <FontAwesomeIcon icon={faCircleXmark} />
            <span>{error}</span>
          </div>
        )}

        {!health && !error && (
          <div className="flex items-center gap-2 text-slate-400">
            <FontAwesomeIcon icon={faSpinner} spin />
            <span>Conectando con la API...</span>
          </div>
        )}

        {health && (
          <ul className="space-y-2">
            <li className="flex items-center gap-2">
              <FontAwesomeIcon icon={faCircleCheck} className="text-emerald-400" />
              API FastAPI: {health.status}
            </li>
            <li className="flex items-center gap-2">
              <FontAwesomeIcon icon={faCircleCheck} className="text-emerald-400" />
              PostgreSQL: {health.postgres}
            </li>
            <li className="flex items-center gap-2">
              <FontAwesomeIcon icon={faCircleCheck} className="text-emerald-400" />
              Redis: {health.redis}
            </li>
          </ul>
        )}
      </div>
    </div>
  )
}

export default App
