import { API_URL, getToken } from "../api/client"

/** Manda al backend los errores de JavaScript que ocurren en el navegador
 * de un usuario (panel de gerencia → Sistema → Fallos recientes).
 *
 * Es lo único que el servidor no ve por sí mismo: si una pantalla se
 * queda en blanco por un error de render, en los logs del backend no
 * aparece nada — la API respondió bien.
 *
 * Con cuidado para no convertirse en el problema:
 * - Cada mensaje distinto se manda una sola vez por carga de página, y
 *   como mucho MAX_PER_PAGE: un error dentro de un bucle de render no
 *   puede disparar mil peticiones.
 * - fetch directo con keepalive, NO el cliente `api`: si reportar fallara
 *   y ese fallo se reportara a su vez, sería un bucle infinito.
 * - Si falla el envío, se ignora en silencio. */

const MAX_PER_PAGE = 10
const sent = new Set<string>()

function isInApp(source: string | undefined, stack: string | undefined): boolean {
  // Las extensiones del navegador también lanzan errores en la página
  // (chrome-extension://...): se guardan, pero marcados como ajenos.
  const origin = window.location.origin
  return Boolean((source && source.startsWith(origin)) || (stack && stack.includes(origin)))
}

function report(kind: "error" | "unhandledrejection", message: string, source?: string, stack?: string) {
  const key = `${kind}:${message}`
  if (sent.has(key) || sent.size >= MAX_PER_PAGE) return
  sent.add(key)

  const token = getToken()
  void fetch(`${API_URL}/monitoring/client-errors`, {
    method: "POST",
    keepalive: true,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({
      kind,
      message: message.slice(0, 1000),
      source: source?.slice(0, 300),
      path: window.location.pathname.slice(0, 300),
      stack: stack?.slice(0, 4000),
      in_app: isInApp(source, stack),
    }),
  }).catch(() => {})
}

export function installClientErrorReporting() {
  window.addEventListener("error", (event) => {
    // Un <img> o <script> que no carga también dispara "error", pero sin
    // mensaje: no es un error de código, se ignora.
    if (!event.message) return
    report("error", event.message, event.filename, event.error instanceof Error ? event.error.stack : undefined)
  })
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason
    const message = reason instanceof Error ? `${reason.name}: ${reason.message}` : String(reason)
    report("unhandledrejection", message, undefined, reason instanceof Error ? reason.stack : undefined)
  })
}
