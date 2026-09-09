import {
  faBell,
  faCamera,
  faChevronRight,
  faCreditCard,
  faEnvelope,
  faGraduationCap,
  faLanguage,
  faRightFromBracket,
  faSpinner,
  faTrash,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useRef, useState, type ChangeEvent } from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { User } from "../api/types"
import { ApiError } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import AppFooter from "../components/AppFooter"
import Avatar from "../components/Avatar"
import BillingModal from "../components/billing/BillingModal"

export default function ProfilePage() {
  const { user, logout, refreshUser } = useAuth()
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [billingOpen, setBillingOpen] = useState(false)
  const [savingPrefs, setSavingPrefs] = useState(false)

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

        {/* Configuración: las tres acciones en una sola tarjeta, en vez del
            botón de cerrar sesión suelto que había antes. Agruparlas las
            hace encontrables — un ajuste que vive solo en mitad de la
            página no se busca, se tropieza uno con él. */}
        <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <p className="px-6 pt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">Configuración</p>

          <div className="mt-2 divide-y divide-slate-100">
            <div className="flex items-center gap-4 px-6 py-4">
              <FontAwesomeIcon icon={faBell} className="w-5 text-slate-400" />
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-slate-800">Notificaciones</p>
                {/* Se dice la verdad sobre el estado real de la función:
                    la preferencia se guarda, pero todavía no hay nada que
                    envíe avisos. Un interruptor que promete lo que no hay
                    se nota a la primera semana. */}
                <p className="text-xs text-slate-400">Guardamos tu preferencia para cuando activemos los avisos</p>
              </div>
              <Toggle
                checked={user.notifications_enabled}
                disabled={savingPrefs}
                onChange={async (value) => {
                  setSavingPrefs(true)
                  try {
                    await api.patch<User>("/users/me/preferences", { notifications_enabled: value })
                    await refreshUser()
                  } catch {
                    setError("No se pudo guardar la preferencia.")
                  } finally {
                    setSavingPrefs(false)
                  }
                }}
              />
            </div>

            <button
              onClick={() => setBillingOpen(true)}
              className="flex w-full items-center gap-4 px-6 py-4 text-left transition hover:bg-slate-50"
            >
              <FontAwesomeIcon icon={faCreditCard} className="w-5 text-slate-400" />
              <span className="flex-1 font-semibold text-slate-800">Método de Facturación</span>
              <FontAwesomeIcon icon={faChevronRight} className="text-xs text-slate-300" />
            </button>

            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-4 px-6 py-4 text-left font-semibold text-red-500 transition hover:bg-red-50"
            >
              <FontAwesomeIcon icon={faRightFromBracket} className="w-5" />
              Cerrar sesión
            </button>
          </div>
        </div>
      </div>

      {billingOpen && <BillingModal onClose={() => setBillingOpen(false)} />}

      <AppFooter />
    </div>
  )
}

/** Interruptor de preferencia. `button` con role="switch" y no un
 * `input type="checkbox"` maquillado: así el lector de pantalla anuncia
 * "activado/desactivado" en vez de "casilla", que es lo que realmente es. */
function Toggle({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean
  disabled?: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label="Notificaciones"
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-7 w-12 shrink-0 rounded-full transition disabled:opacity-50 ${checked ? "bg-blue-600" : "bg-slate-200"}`}
    >
      <span
        className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? "left-6" : "left-1"}`}
      />
    </button>
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
