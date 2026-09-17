import { useId } from "react"

/** Logotipo de Espikin: burbuja de diálogo lavanda con dos franjas marino.
 *
 * Vectorizado a partir del PNG oficial del logo. Es SVG y no PNG para que
 * se vea nítido a cualquier tamaño (favicon de 16px, cabecera de 40px);
 * las versiones PNG en alta resolución están en `public/` para los usos
 * que no aceptan SVG (icono de pantalla de inicio en el móvil, redes).
 *
 * El isotipo es el mismo en fondos claros y oscuros, como el original:
 * la burbuja lavanda contrasta con los dos. `tone` solo cambia el color
 * del nombre.
 */
type Tone = "light" | "dark"

export function LogoMark({ size = 36, className = "" }: { size?: number; className?: string }) {
  // id único por instancia: con varios logos en la misma página (cabecera
  // y footer), ids repetidos harían que todos usaran el primer degradado.
  const gradientId = useId()

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label="Espikin"
      className={`shrink-0 ${className}`}
    >
      <defs>
        <linearGradient id={gradientId} x1="0.2" y1="0" x2="0.5" y2="1">
          <stop offset="0%" stopColor="#CDBBFF" />
          <stop offset="100%" stopColor="#7743EE" />
        </linearGradient>
      </defs>
      {/* Burbuja: cuadrado redondeado con el pico abajo a la izquierda. */}
      <path
        d="M26 6H74A16 16 0 0 1 90 22V68A16 16 0 0 1 74 84H34L10 97V22A16 16 0 0 1 26 6Z"
        fill={`url(#${gradientId})`}
      />
      {/* Dos franjas inclinadas en paralelo. */}
      <path d="M31 37L82 21V34L31 50Z" fill="#191340" />
      <path d="M31 56L82 40V53L31 69Z" fill="#191340" />
    </svg>
  )
}

/** Isotipo + nombre, la versión horizontal del logo. */
export default function Logo({
  size = 36,
  tone = "light",
  className = "",
  textClassName = "text-lg",
}: {
  size?: number
  tone?: Tone
  className?: string
  textClassName?: string
}) {
  return (
    <span className={`flex items-center gap-2.5 ${className}`}>
      <LogoMark size={size} />
      <span
        className={`font-extrabold tracking-tight ${textClassName} ${
          tone === "light" ? "text-ink-900" : "bg-gradient-to-b from-brand-100 to-brand-400 bg-clip-text text-transparent"
        }`}
      >
        Espikin
      </span>
    </span>
  )
}
