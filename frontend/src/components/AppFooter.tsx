import { faBookBookmark, faBookOpen, faChartLine, faComments, faEnvelope, faUser } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { Link } from "react-router-dom"
import { PAGE_GUTTER } from "./pageGutter"
import Logo from "./brand/Logo"

const LEARN_LINKS = [
  { to: "/classroom", label: "Classroom", icon: faBookOpen },
  { to: "/library", label: "Biblioteca", icon: faBookBookmark },
  { to: "/chat", label: "Hablar con Teacher David", icon: faComments },
  { to: "/progress", label: "Mi progreso y certificación", icon: faChartLine },
  { to: "/profile", label: "Mi perfil", icon: faUser },
]

/** Pie común de la app, a todo el ancho de la ventana.
 *
 * Vive en el Layout y no en cada página: antes cada pantalla lo pintaba
 * dentro de su contenido, así que quedaba encajonado con ese contenido y
 * había que acordarse de añadirlo en cada página nueva. */
export default function AppFooter() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className={`grid grid-cols-1 gap-10 py-12 md:grid-cols-12 ${PAGE_GUTTER}`}>
        <div className="md:col-span-5">
          <Logo size={40} textClassName="text-xl" />
          <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-500">
            Inglés con Teacher David, tu tutor de IA, diseñado para hispanohablantes y estructurado según el Marco
            Común Europeo de Referencia, de A1 a C2.
          </p>
          <a
            href="mailto:hola@espikin.com"
            className="mt-5 inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
          >
            <FontAwesomeIcon icon={faEnvelope} className="text-xs" /> hola@espikin.com
          </a>
        </div>

        <nav className="md:col-span-3" aria-label="Tu aprendizaje">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Tu aprendizaje</h3>
          <ul className="mt-4 space-y-3 text-sm">
            {LEARN_LINKS.map((link) => (
              <li key={link.to}>
                <Link to={link.to} className="flex items-center gap-2.5 text-slate-600 transition hover:text-brand-600">
                  <FontAwesomeIcon icon={link.icon} className="w-3.5 text-xs text-slate-300" />
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="md:col-span-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Cómo funciona</h3>
          <ul className="mt-4 space-y-3 text-sm leading-relaxed text-slate-500">
            <li>Tu nivel se certifica por evidencia acumulada, no por lecciones vistas.</li>
            <li>Teacher David corrige según tu nivel: deja pasar lo que todavía no toca.</li>
            <li>Cada módulo se aprueba con un examen, y aprobarlo desbloquea el siguiente.</li>
          </ul>
        </div>
      </div>

      <div className="border-t border-slate-100">
        <div
          className={`flex flex-col items-center justify-between gap-2 py-5 text-xs text-slate-400 sm:flex-row ${PAGE_GUTTER}`}
        >
          <span>© 2026 Espikin. Todos los derechos reservados.</span>
          <span>Plan Premium $10/mes · cancela cuando quieras</span>
        </div>
      </div>
    </footer>
  )
}
