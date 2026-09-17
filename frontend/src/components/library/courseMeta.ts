import {
  faBookBookmark,
  faBriefcase,
  faComments,
  faHeadset,
  faHouse,
  faLaptop,
  faOilWell,
  faPassport,
  faPlane,
  faStethoscope,
  faSuitcaseRolling,
  faUserTie,
  faUtensils,
} from "@fortawesome/free-solid-svg-icons"
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core"

/** Icono de cada curso por el nombre que guarda el backend (FlashCourse.icon).
 *
 * Un mapa explícito y no una importación dinámica por nombre: para eso
 * habría que meter en el bundle los ~1.400 iconos del paquete para usar
 * nueve. Un nombre que no esté aquí cae al icono genérico en vez de romper
 * la tarjeta. */
const ICONS: Record<string, IconDefinition> = {
  "oil-well": faOilWell,
  "suitcase-rolling": faSuitcaseRolling,
  "user-tie": faUserTie,
  utensils: faUtensils,
  passport: faPassport,
  headset: faHeadset,
  laptop: faLaptop,
  stethoscope: faStethoscope,
  comments: faComments,
}

export function courseIcon(name: string): IconDefinition {
  return ICONS[name] ?? faBookBookmark
}

// Un color por categoría, distinto entre sí: dentro de la paleta de la marca
// (violeta y marino) para Trabajo y Viajes, y dos tonos que armonizan con el
// violeta para las otras. Con el cambio de marca, Viajes y Social habían
// quedado del mismo color y las tarjetas dejaban de distinguirse de un vistazo.
export const CATEGORIES: Record<string, { label: string; icon: IconDefinition; tile: string; accent: string }> = {
  trabajo: { label: "Trabajo", icon: faBriefcase, tile: "bg-brand-600 text-white", accent: "text-brand-600" },
  viajes: { label: "Viajes", icon: faPlane, tile: "bg-ink-800 text-white", accent: "text-ink-800" },
  vida_diaria: { label: "Vida diaria", icon: faHouse, tile: "bg-emerald-500 text-white", accent: "text-emerald-600" },
  social: { label: "Social", icon: faComments, tile: "bg-fuchsia-500 text-white", accent: "text-fuchsia-600" },
}

export function categoryMeta(category: string) {
  return CATEGORIES[category] ?? { label: category, icon: faBookBookmark, tile: "bg-slate-700 text-white", accent: "text-slate-600" }
}
