import { faComments, faGraduationCap, faRightFromBracket } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { Link, Outlet, useNavigate } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate("/login")
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold">
            <span>English Academy</span>
            <span className="text-xs">🇬🇧</span>
          </Link>

          <div className="flex items-center gap-4 text-sm">
            {user?.current_level_id && (
              <span className="hidden items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-emerald-400 sm:flex">
                <FontAwesomeIcon icon={faGraduationCap} />
                Nivel actual
              </span>
            )}
            <Link
              to="/chat"
              className="flex items-center gap-1.5 rounded-full px-3 py-1 text-slate-300 hover:bg-slate-800 hover:text-white"
            >
              <FontAwesomeIcon icon={faComments} />
              <span className="hidden sm:inline">Tutor</span>
            </Link>
            <span className="hidden text-slate-400 sm:inline">{user?.full_name}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 rounded-full px-3 py-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              title="Cerrar sesión"
            >
              <FontAwesomeIcon icon={faRightFromBracket} />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
