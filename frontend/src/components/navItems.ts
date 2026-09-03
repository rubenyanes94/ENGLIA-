import { faBookOpen, faChartLine, faComments, faHouse, faUser } from "@fortawesome/free-solid-svg-icons"

/** Única fuente de verdad de las secciones de la app, compartida por la
 * navegación horizontal de escritorio (Layout) y la barra inferior de
 * móvil (BottomNav).
 *
 * En su propio módulo, no dentro de Layout, a propósito: si viviera allí,
 * BottomNav tendría que importarlo DE Layout mientras Layout importa
 * BottomNav — un ciclo que hoy funcionaría (NAV_ITEMS solo se lee en
 * tiempo de render, no de carga del módulo) pero que se rompería en
 * silencio en cuanto alguien lo usara a nivel de módulo. */
export const NAV_ITEMS = [
  { to: "/dashboard", icon: faHouse, label: "Inicio" },
  { to: "/classroom", icon: faBookOpen, label: "Classroom" },
  { to: "/progress", icon: faChartLine, label: "Progreso" },
  { to: "/chat", icon: faComments, label: "Tutor" },
  { to: "/profile", icon: faUser, label: "Perfil" },
]
