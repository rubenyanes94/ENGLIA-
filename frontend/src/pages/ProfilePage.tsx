import { faEnvelope, faGraduationCap, faRightFromBracket } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"

export default function ProfilePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  function handleLogout() {
    logout()
    navigate("/")
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-600 text-2xl font-bold text-white">
          {user.full_name.charAt(0).toUpperCase()}
        </span>
        <h1 className="mt-3 text-xl font-extrabold text-slate-900">{user.full_name}</h1>
        <p className="flex items-center gap-1.5 text-sm text-slate-500">
          <FontAwesomeIcon icon={faEnvelope} className="text-xs" /> {user.email}
        </p>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          <FontAwesomeIcon icon={faGraduationCap} /> Nivel actual
        </p>
        <p className="mt-2 text-lg font-bold text-slate-900">
          {user.current_level_id ? "Certificado" : "Sin certificar todavía — trabajando en A1"}
        </p>
      </div>

      <button
        onClick={handleLogout}
        className="flex w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600 transition active:scale-[0.98] hover:bg-slate-50"
      >
        <FontAwesomeIcon icon={faRightFromBracket} />
        Cerrar sesión
      </button>
    </div>
  )
}
