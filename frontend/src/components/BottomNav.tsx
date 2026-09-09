import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { NavLink } from "react-router-dom"
import { NAV_ITEMS } from "./navItems"

/** Nav inferior fija — SOLO en móvil (`md:hidden`). En escritorio la
 * navegación vive en el header horizontal de Layout: una barra fija
 * abajo en una pantalla ancha es un patrón de app, no de web, y aquí la
 * experiencia objetivo es web.
 *
 * `end` en cada NavLink a propósito: sin él, NavLink marcaría una ruta
 * como activa también en subrutas que empiecen igual. */
export default function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white/95 backdrop-blur md:hidden">
      <div className="mx-auto flex max-w-lg items-center justify-around px-2 py-2">
        {NAV_ITEMS.map((item) => (
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
