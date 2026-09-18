import { faChartPie, faRightFromBracket } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useRef } from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import { api } from "../api/client"
import { useAuth } from "../auth/AuthContext"
import AppFooter from "./AppFooter"
import Avatar from "./Avatar"
import BottomNav from "./BottomNav"
import { NAV_ITEMS } from "./navItems"
import { PAGE_GUTTER } from "./pageGutter"
import Logo from "./brand/Logo"

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  // El chat ocupa exactamente el alto de la pantalla (la caja de mensajes
  // tiene su propio scroll); un footer debajo obligaría a desplazar la
  // página entera para ver lo que se escribe.
  const showFooter = !pathname.startsWith("/chat")

  // Qué pantallas abre cada alumno: es la materia prima del "journey" y de
  // "pantallas más visitadas" en el panel de gerencia. Solo alumnos (los
  // clics de un admin probando la app falsearían las cifras) y con la ruta
  // normalizada, para que /modules/<id> cuente como UNA pantalla y no como
  // cien. Si falla, se ignora: medir nunca puede romper la app.
  //
  // `lastTracked` evita el doble registro: en desarrollo, StrictMode ejecuta
  // cada efecto dos veces y cada visita salía duplicada en el panel. Solo
  // se salta la MISMA ruta consecutiva, así que ir a Inicio, luego a
  // Classroom y volver a Inicio sigue contando las tres visitas.
  const lastTracked = useRef<string | null>(null)
  useEffect(() => {
    if (user?.role !== "student" || lastTracked.current === pathname) return
    lastTracked.current = pathname
    void api.post("/events", { event_type: "page_viewed", payload: { path: screenKey(pathname) } }).catch(() => {})
  }, [pathname, user?.role])

  function handleLogout() {
    logout()
    navigate("/")
  }

  return (
    // pb-20 solo en móvil: es el hueco que necesita la barra inferior
    // fija, que en escritorio no existe (la navegación vive en el header).
    <div className="flex min-h-screen flex-col bg-slate-50 pb-20 text-slate-900 md:pb-0">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className={`flex w-full items-center justify-between gap-6 py-3 ${PAGE_GUTTER}`}>
          <Link to="/dashboard" className="shrink-0" aria-label="Espikin: ir al inicio">
            <Logo size={36} textClassName="hidden text-xl sm:inline" />
          </Link>

          {/* Navegación horizontal: solo escritorio. En móvil la sirve
              BottomNav, que es el patrón que espera un pulgar. */}
          <nav className="hidden flex-1 items-center gap-1 md:flex">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition ${
                    isActive ? "bg-brand-50 text-brand-600" : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                <FontAwesomeIcon icon={item.icon} className="text-xs" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-3">
            {user?.role === "admin" && (
              <Link
                to="/gerencia"
                className="hidden items-center gap-2 rounded-full px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 md:flex"
              >
                <FontAwesomeIcon icon={faChartPie} className="text-xs" />
                Gerencia
              </Link>
            )}
            {user && (
              <span className="hidden text-sm text-slate-500 lg:inline">{user.full_name}</span>
            )}
            {user && (
              <Link to="/profile" title="Tu perfil">
                <Avatar name={user.full_name} avatarUrl={user.avatar_url} size={36} />
              </Link>
            )}
            <button
              onClick={handleLogout}
              className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              title="Cerrar sesión"
            >
              <FontAwesomeIcon icon={faRightFromBracket} />
            </button>
          </div>
        </div>
      </header>

      <main className={`w-full flex-1 py-8 lg:py-10 ${PAGE_GUTTER}`}>
        <Outlet />
      </main>

      {showFooter && <AppFooter />}

      <BottomNav />
    </div>
  )
}

/** "/modules/9d3b…" → "/modules/:id"; "/library/ingles-petroleros" → "/library/:slug". */
function screenKey(pathname: string): string {
  if (pathname.startsWith("/modules/")) return "/modules/:id"
  if (pathname.startsWith("/library/")) return "/library/:slug"
  return pathname
}
