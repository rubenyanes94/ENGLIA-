import { faCamera, faEnvelope, faGraduationCap, faLanguage, faRightFromBracket, faSpinner, faTrash } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useRef, useState, type ChangeEvent } from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { User } from "../api/types"
import { ApiError } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import AppFooter from "../components/AppFooter"
import Avatar from "../components/Avatar"

export default function ProfilePage() {
  const { user, logout, refreshUser } = useAuth()
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!user) return null

  function handleLogout() {
    logout()
    navigate("/")
  }

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)
    try {
      await api.upload<User>("/users/me/avatar", file)
      // refreshUser en vez de guardar la respuesta en un estado local: el
      // avatar se pinta también en la barra superior y en el dashboard,
      // que leen del contexto de auth — actualizar solo aquí dejaría el
      // resto de la app mostrando la foto vieja hasta recargar.
      await refreshUser()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo subir la imagen.")
    } finally {
      setUploading(false)
      // Se limpia el input para que volver a elegir EL MISMO archivo
      // dispare el evento otra vez (si no, el navegador lo ignora).
      if (fileInput.current) fileInput.current.value = ""
    }
  }

  async function handleRemovePhoto() {
    setUploading(true)
    setError(null)
    try {
      await api.delete<User>("/users/me/avatar")
      await refreshUser()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo quitar la imagen.")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 lg:text-4xl">Tu perfil</h1>

        <div className="flex flex-col items-center gap-5 rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:flex-row sm:text-left">
          <div className="relative shrink-0">
            <Avatar name={user.full_name} avatarUrl={user.avatar_url} size={96} />
            <button
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              className="absolute -bottom-1 -right-1 flex h-9 w-9 items-center justify-center rounded-full border-2 border-white bg-blue-600 text-sm text-white shadow-md transition active:scale-95 hover:bg-blue-500 disabled:opacity-60"
              title="Cambiar foto"
            >
              <FontAwesomeIcon icon={uploading ? faSpinner : faCamera} spin={uploading} />
            </button>
            <input
              ref={fileInput}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          <div className="min-w-0 flex-1">
            <h2 className="text-2xl font-extrabold text-slate-900">{user.full_name}</h2>
            <p className="mt-1 flex items-center justify-center gap-2 text-sm text-slate-500 sm:justify-start">
              <FontAwesomeIcon icon={faEnvelope} className="text-xs" /> {user.email}
            </p>
            <div className="mt-3 flex flex-wrap items-center justify-center gap-3 sm:justify-start">
              <button
                onClick={() => fileInput.current?.click()}
                disabled={uploading}
                className="text-sm font-semibold text-blue-600 hover:text-blue-500 disabled:opacity-60"
              >
                {user.avatar_url ? "Cambiar foto" : "Subir foto"}
              </button>
              {user.avatar_url && (
                <button
                  onClick={handleRemovePhoto}
                  disabled={uploading}
                  className="flex items-center gap-1.5 text-sm font-semibold text-slate-400 hover:text-red-500 disabled:opacity-60"
                >
                  <FontAwesomeIcon icon={faTrash} className="text-xs" /> Quitar
                </button>
              )}
            </div>
            <p className="mt-2 text-xs text-slate-400">JPG, PNG o WebP · máximo 2 MB</p>
            {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <InfoCard
            icon={faGraduationCap}
            label="Nivel actual"
            value={user.current_level_id ? "Certificado" : "Sin certificar — trabajando en A1"}
          />
          <InfoCard
            icon={faLanguage}
            label="Idioma nativo"
            value={user.native_language === "es" ? "Español" : user.native_language}
          />
        </div>

        <button
          onClick={handleLogout}
          className="flex w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600 transition active:scale-[0.98] hover:bg-slate-50 sm:w-auto sm:px-8"
        >
          <FontAwesomeIcon icon={faRightFromBracket} />
          Cerrar sesión
        </button>
      </div>

      <AppFooter />
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
