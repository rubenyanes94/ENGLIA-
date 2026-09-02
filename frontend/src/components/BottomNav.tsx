import { faBookOpen, faChartLine, faComments, faHouse, faUser } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { NavLink } from "react-router-dom"

const ITEMS = [
  { to: "/dashboard", icon: faHouse, label: "Inicio" },
  { to: "/classroom", icon: faBookOpen, label: "Classroom" },
  { to: "/progress", icon: faChartLine, label: "Progreso" },
  { to: "/chat", icon: faComments, label: "Tutor" },
  { to: "/profile", icon: faUser, label: "Perfil" },
]

/** Nav inferior fija, estilo app móvil (ver referencia de diseño) — visible
 * en todas las pantallas protegidas vía Layout. `end` en Inicio a
 * propósito: sin él, NavLink marcaría "/dashboard" como activo también
 * al estar en subrutas que empiecen igual (no las hay hoy, pero evita el bug). */
export default function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-lg items-center justify-around px-2 py-2">
        {ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 rounded-xl px-3 py-1.5 text-[11px] font-medium transition ${
                isActive ? "text-blue-600" : "text-slate-400 hover:text-slate-600"
              }`
            }
          >
            <FontAwesomeIcon icon={item.icon} className="text-lg" />
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
