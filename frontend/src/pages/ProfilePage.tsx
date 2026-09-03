import { faEnvelope, faGraduationCap, faLanguage, faRightFromBracket } from "@fortawesome/free-solid-svg-icons"
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
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <h1 className="text-3xl font-extrabold text-slate-900 lg:text-4xl">Tu perfil</h1>

      <div className="flex flex-col items-center gap-4 rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:flex-row sm:text-left">
        <span className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-blue-600 text-3xl font-bold text-white">
          {user.full_name.charAt(0).toUpperCase()}
        </span>
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900">{user.full_name}</h2>
          <p className="mt-1 flex items-center justify-center gap-2 text-sm text-slate-500 sm:justify-start">
            <FontAwesomeIcon icon={faEnvelope} className="text-xs" /> {user.email}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <InfoCard
          icon={faGraduationCap}
          label="Nivel actual"
          value={user.current_level_id ? "Certificado" : "Sin certificar — trabajando en A1"}
        />
        <InfoCard icon={faLanguage} label="Idioma nativo" value={user.native_language === "es" ? "Español" : user.native_language} />
      </div>

      <button
        onClick={handleLogout}
        className="flex w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600 transition active:scale-[0.98] hover:bg-slate-50 sm:w-auto sm:px-8"
      >
        <FontAwesomeIcon icon={faRightFromBracket} />
        Cerrar sesión
      </button>
    </div>
  )
}

function InfoCard({ icon, label, value }: { icon: typeof faGraduationCap; label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        <FontAwesomeIcon icon={icon} /> {label}
      </p>
      <p className="mt-2 text-lg font-bold text-slate-900">{value}</p>
    </div>
  )
}
