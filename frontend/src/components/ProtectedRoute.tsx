import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { faSpinner } from "@fortawesome/free-solid-svg-icons"
import { Navigate, Outlet } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"

export default function ProtectedRoute() {
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

  return <Outlet />
}
