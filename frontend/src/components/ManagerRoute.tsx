import { faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { Navigate, Outlet } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"

/** Puerta del panel de gerencia: solo "manager" y "admin". Un alumno que
 * teclee /gerencia vuelve a su inicio. Es solo navegación: aunque alguien
 * forzara la pantalla, el backend responde 403 a cada dato. */
export default function ManagerRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" />
        Comprobando sesión...
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== "manager" && user.role !== "admin") return <Navigate to="/dashboard" replace />

  return <Outlet />
}
