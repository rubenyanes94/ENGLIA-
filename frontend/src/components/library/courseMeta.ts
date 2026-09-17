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

export const CATEGORIES: Record<string, { label: string; icon: IconDefinition; tile: string; accent: string }> = {
  trabajo: { label: "Trabajo", icon: faBriefcase, tile: "bg-blue-600 text-white", accent: "text-blue-600" },
  viajes: { label: "Viajes", icon: faPlane, tile: "bg-sky-500 text-white", accent: "text-sky-600" },
  vida_diaria: { label: "Vida diaria", icon: faHouse, tile: "bg-emerald-500 text-white", accent: "text-emerald-600" },
  social: { label: "Social", icon: faComments, tile: "bg-violet-500 text-white", accent: "text-violet-600" },
}

export function categoryMeta(category: string) {
  return CATEGORIES[category] ?? { label: category, icon: faBookBookmark, tile: "bg-slate-700 text-white", accent: "text-slate-600" }
}
