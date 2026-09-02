import { ApiError } from "./types"

const BACKEND_PORT = "8000"
const FRONTEND_PORT = "5173"

/**
 * Calcula la URL del backend. Idéntica a la del Paso 1 (ver git history de
 * App.tsx) — se traslada aquí porque ahora la necesita todo api/client.ts,
 * no un solo componente de comprobación de salud.
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
    return `${protocol}//${hostname.replace(`-${FRONTEND_PORT}.`, `-${BACKEND_PORT}.`)}`
  }
  return `${protocol}//${hostname}:${BACKEND_PORT}`
}

export const API_URL = resolveApiUrl()

const TOKEN_STORAGE_KEY = "englia_token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

/**
 * Wrapper fino sobre fetch: añade el host resuelto, el header de
 * autenticación si hay token, y traduce respuestas no-2xx a ApiError
 * (con el `detail` crudo, string u objeto — ver api/types.ts) en vez de
 * dejar que cada pantalla reimplemente el mismo try/catch.
 */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  headers.set("Content-Type", "application/json")
  if (token) headers.set("Authorization", `Bearer ${token}`)

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    let detail: string | ApiErrorDetailLike = `Error ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // Respuesta sin JSON (ej. 502 de un proxy) — nos quedamos con el detail genérico.
    }
    throw new ApiError(res.status, detail as never)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// Solo para tipar el catch de arriba sin importar el tipo público —
// ApiErrorDetail ya viene tipado en api/types.ts, esto es interno.
type ApiErrorDetailLike = string | { message?: string; eligible?: boolean; criteria?: unknown[] }

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
}

/** POST /auth/login usa application/x-www-form-urlencoded (OAuth2PasswordRequestForm
 * del backend lo exige), no JSON como el resto de la API — aparte a propósito. */
export async function loginRequest(email: string, password: string): Promise<{ access_token: string }> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail ?? "No se pudo iniciar sesión.")
  }
  return res.json()
}
