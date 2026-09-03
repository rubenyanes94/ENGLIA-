import { faRightFromBracket } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { Link, Outlet, useNavigate } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"
import BottomNav from "./BottomNav"

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate("/")
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-lg items-center justify-between px-5 py-3">
          <Link to="/dashboard" className="flex items-center gap-2 font-bold text-slate-900">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm text-white">
              EA
            </span>
            English Academy
          </Link>

          <div className="flex items-center gap-3">
            {user && (
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                {user.full_name.charAt(0).toUpperCase()}
              </span>
            )}
            <button
              onClick={handleLogout}
              className="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              title="Cerrar sesión"
            >
              <FontAwesomeIcon icon={faRightFromBracket} />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-lg px-5 py-6">
        <Outlet />
      </main>

      <BottomNav />
    </div>
  )
}
