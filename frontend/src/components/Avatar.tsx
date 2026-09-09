import { API_URL } from "../api/client"

/**
 * Foto de perfil con degradado de respaldo.
 *
 * `avatarUrl` viene del backend como ruta relativa ("/media/avatars/..."),
 * así que se antepone API_URL — que es "/api" (mismo origen, proxy de
 * Vite). Sin eso, el navegador pediría /media/... al servidor del
 * frontend, donde no existe.
 *
 * Si no hay foto, la inicial del nombre sobre degradado: nunca un icono
 * genérico de "usuario sin foto", que es lo que hace que un producto
 * parezca vacío antes de tener usuarios.
 */
export default function Avatar({
  name,
  avatarUrl,
  size = 40,
  className = "",
}: {
  name: string
  avatarUrl?: string | null
  size?: number
  className?: string
}) {
  const initial = name.trim().charAt(0).toUpperCase() || "?"

  if (avatarUrl) {
    return (
      <img
        src={`${API_URL}${avatarUrl}`}
        alt={name}
        style={{ width: size, height: size }}
        className={`shrink-0 rounded-full object-cover ${className}`}
      />
    )
  }

  return (
    <span
      style={{ width: size, height: size, fontSize: Math.max(12, size * 0.4) }}
      className={`flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 font-bold text-white ${className}`}
    >
      {initial}
    </span>
  )
}
