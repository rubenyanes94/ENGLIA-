import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { faSpinner } from "@fortawesome/free-solid-svg-icons"
import { Navigate, Outlet } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"

/** Puerta de la app de alumno. `requireAccess` (por defecto) exige además
 * el acceso de pago: sin él, al paso de suscripción. Las pantallas que un
 * alumno sin pagar SÍ necesita (la propia suscripción, la vuelta desde la
 * pasarela) usan requireAccess={false}. */
export default function ProtectedRoute({ requireAccess = true }: { requireAccess?: boolean }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-950 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" />
        Comprobando sesión...
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  // La cuenta de gerencia solo ve el panel de gerencia: cualquier ruta del
  // aula (incluido el /dashboard al que manda el login) la lleva allí.
  if (user.role === "manager") return <Navigate to="/gerencia" replace />
  // El candado de pago. Mismo criterio que el backend (/auth/me → access):
  // si llega a false, a pagar; la API respondería 402 de todos modos.
  if (requireAccess && user.access?.has_access === false) return <Navigate to="/suscripcion" replace />

  return <Outlet />
}
