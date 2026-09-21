import type { ReactNode } from "react"
import Logo from "../brand/Logo"

/** Marco de las pantallas de entrada: registro, login, suscripción y la
 * vuelta desde la pasarela de pago. Pantalla partida en escritorio (marca
 * a la izquierda, contenido a la derecha), una columna en móvil — patrón
 * web estándar, en vez de una tarjeta pequeña flotando en 1400 px.
 *
 * Compartido para que el paso de pago se vea como CONTINUACIÓN del
 * registro y no como otra parte de la app. */
export default function AuthShell({ top, children }: { top?: ReactNode; children: ReactNode }) {
  return (
    <div className="grid min-h-screen grid-cols-1 bg-slate-50 text-slate-900 lg:grid-cols-2">
      {/* Fondo marino a violeta, el mismo del manual de marca, con el logo
          en su versión para fondo oscuro. */}
      <aside className="hidden flex-col justify-between bg-gradient-to-br from-ink-950 via-ink-900 to-brand-900 p-12 text-white lg:flex">
        <Logo tone="dark" size={44} textClassName="text-2xl" />
        <div>
          <h2 className="text-4xl font-extrabold leading-tight">
            De A1 a C2, con un tutor que entiende cómo aprende un hispanohablante.
          </h2>
          <p className="mt-4 max-w-md text-brand-100">
            Tu progreso se mide en capacidades reales del Marco Común Europeo, demostradas varias veces — no en
            lecciones vistas.
          </p>
        </div>
        <p className="text-sm text-brand-200">Espikin © 2026</p>
      </aside>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          {top}
          <div className="lg:hidden">
            <Logo size={32} className="mb-5" />
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
