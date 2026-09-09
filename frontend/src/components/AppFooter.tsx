import { faCircleQuestion, faEnvelope, faShieldHalved } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { Link } from "react-router-dom"

/** Pie de la app (dentro de la sesión). `mb-20 md:mb-0` porque en móvil
 * la barra inferior fija taparía el final del footer. */
export default function AppFooter() {
  return (
    <footer className="mt-16 mb-20 border-t border-slate-200 pt-10 md:mb-0">
      <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
        <div>
          <span className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 text-sm font-black text-white">
              E
            </span>
            <span className="font-extrabold tracking-tight text-slate-900">Espikin</span>
          </span>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-slate-500">
            Inglés con tutores de IA, diseñado para hispanohablantes y estructurado según el Marco Común Europeo de
            Referencia (A1–C2).
          </p>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Tu aprendizaje</h3>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <Link to="/classroom" className="text-slate-600 hover:text-blue-600">
                Classroom
              </Link>
            </li>
            <li>
              <Link to="/progress" className="text-slate-600 hover:text-blue-600">
                Mi progreso y certificación
              </Link>
            </li>
            <li>
              <Link to="/chat" className="text-slate-600 hover:text-blue-600">
                Hablar con mi tutor
              </Link>
            </li>
            <li>
              <Link to="/profile" className="text-slate-600 hover:text-blue-600">
                Mi perfil
              </Link>
            </li>
          </ul>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Cómo funciona</h3>
          <ul className="mt-3 space-y-2.5 text-sm text-slate-500">
            <li className="flex items-start gap-2">
              <FontAwesomeIcon icon={faShieldHalved} className="mt-0.5 shrink-0 text-slate-300" />
              Tu nivel se certifica por evidencia acumulada, no por lecciones vistas.
            </li>
            <li className="flex items-start gap-2">
              <FontAwesomeIcon icon={faCircleQuestion} className="mt-0.5 shrink-0 text-slate-300" />
              El tutor corrige según tu nivel: ignora lo que aún no toca.
            </li>
            <li className="flex items-start gap-2">
              <FontAwesomeIcon icon={faEnvelope} className="mt-0.5 shrink-0 text-slate-300" />
              ¿Dudas? hola@espikin.com
            </li>
          </ul>
        </div>
      </div>

      <div className="mt-10 border-t border-slate-100 pt-6 text-center text-xs text-slate-400">
        Espikin © 2026 · Plan Premium $10/mes, cancela cuando quieras
      </div>
    </footer>
  )
}
