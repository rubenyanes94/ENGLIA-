import { faBookBookmark, faBookOpen, faChartLine, faComments, faHouse, faUser } from "@fortawesome/free-solid-svg-icons"

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
  { to: "/dashboard", icon: faHouse, label: "Inicio", end: true },
  { to: "/classroom", icon: faBookOpen, label: "Classroom", end: true },
  // end: false para que "Biblioteca" siga marcada dentro de un curso
  // (/library/ingles-petroleros); con end: true se apagaría al entrar.
  { to: "/library", icon: faBookBookmark, label: "Biblioteca", end: false },
  { to: "/progress", icon: faChartLine, label: "Progreso", end: true },
  { to: "/chat", icon: faComments, label: "Tutor", end: true },
  { to: "/profile", icon: faUser, label: "Perfil", end: true },
]
