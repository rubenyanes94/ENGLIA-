import {
  faArrowsRotate,
  faChartColumn,
  faGaugeHigh,
  faHeartPulse,
  faMoneyCheckDollar,
  faRightFromBracket,
  faRoute,
  faSackDollar,
  faUsers,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { Suspense, useEffect, useState } from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import { api } from "../../api/client"
import type { PaymentReviewSummary } from "../../api/management"
import { useAuth } from "../../auth/AuthContext"
import Logo from "../brand/Logo"
import { PAGE_GUTTER } from "../pageGutter"
import { PAYMENTS_CHANGED } from "./events"

export const MANAGEMENT_NAV = [
  { to: "/gerencia", label: "Resumen", icon: faGaugeHigh, end: true },
  { to: "/gerencia/consumo", label: "Consumo", icon: faChartColumn, end: true },
  { to: "/gerencia/journey", label: "Journey", icon: faRoute, end: true },
  { to: "/gerencia/retencion", label: "Retención", icon: faArrowsRotate, end: true },
  { to: "/gerencia/ingresos", label: "Ingresos", icon: faSackDollar, end: true },
  { to: "/gerencia/pagos", label: "Pagos", icon: faMoneyCheckDollar, end: true },
  { to: "/gerencia/clientes", label: "Clientes", icon: faUsers, end: false },
  { to: "/gerencia/sistema", label: "Sistema", icon: faHeartPulse, end: true },
]

/** Marco del panel de gerencia. Aparte del Layout del alumno a propósito:
 * gerencia no ve el aula, el tutor ni el progreso de nadie como alumno —
 * solo estas seis pestañas. Mismo relleno lateral (PAGE_GUTTER) y ancho
 * completo que el resto de la app.
 *
 * Las pestañas arrastran el ?periodo= actual: cambiar de "Resumen" a
 * "Ingresos" no debería devolverte a 30 días si estabas mirando 90. */
export default function ManagementLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { search } = useLocation()
  const period = new URLSearchParams(search).get("periodo")
  const carry = period ? `?periodo=${period}` : ""
  const pending = usePendingPayments()

  function handleLogout() {
    logout()
    navigate("/")
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className={`flex w-full items-center justify-between gap-4 py-3 ${PAGE_GUTTER}`}>
          <Link to={`/gerencia${carry}`} className="flex shrink-0 items-center gap-3" aria-label="Espikin gerencia: ir al resumen">
            <Logo size={34} textClassName="hidden text-xl sm:inline" />
            <span className="rounded-full bg-ink-900 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-white">
              Gerencia
            </span>
          </Link>

          <div className="flex shrink-0 items-center gap-3">
            {user?.role === "admin" && (
              <Link to="/dashboard" className="hidden text-sm font-medium text-slate-500 hover:text-slate-900 sm:inline">
                Ir a la app
              </Link>
            )}
            <span className="hidden text-sm text-slate-500 md:inline">{user?.full_name}</span>
            <button
              onClick={handleLogout}
              className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              title="Cerrar sesión"
            >
              <FontAwesomeIcon icon={faRightFromBracket} />
              <span className="sr-only">Cerrar sesión</span>
            </button>
          </div>
        </div>

        {/* Pestañas en su propia fila: seis secciones no caben junto al logo
            en un móvil, y aquí se desplazan en horizontal sin romper la página. */}
        <nav aria-label="Secciones de gerencia" className={`-mb-px flex w-full gap-1 overflow-x-auto ${PAGE_GUTTER}`}>
          {MANAGEMENT_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={`${item.to}${carry}`}
              end={item.end}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-semibold transition ${
                  isActive ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-900"
                }`
              }
            >
              <FontAwesomeIcon icon={item.icon} className="text-xs" />
              {item.label}
              {item.to === "/gerencia/pagos" && pending > 0 && (
                <span className="rounded-full bg-amber-400 px-1.5 text-[11px] font-bold text-slate-900" aria-label={`${pending} por verificar`}>
                  {pending}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className={`w-full flex-1 py-8 lg:py-10 ${PAGE_GUTTER}`}>
        {/* Suspense propio: cada pestaña se descarga al abrirla y, sin él,
            mientras llega se quedaría en blanco toda la cabecera. */}
        <Suspense fallback={<div className="py-24" />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}

/** Pagos por verificar, para el contador de la pestaña: se ve desde
 * cualquier sección del panel que hay cola, sin tener que entrar a mirar.
 * Se refresca cada minuto y al momento cuando se revisa un pago. */
function usePendingPayments(): number {
  const [pending, setPending] = useState(0)
  useEffect(() => {
    let alive = true
    const load = () =>
      api
        .get<PaymentReviewSummary>("/management/payments/summary")
        .then((s) => alive && setPending(s.pending))
        .catch(() => {})
    void load()
    const id = setInterval(load, 60_000)
    window.addEventListener(PAYMENTS_CHANGED, load)
    return () => {
      alive = false
      clearInterval(id)
      window.removeEventListener(PAYMENTS_CHANGED, load)
    }
  }, [])
  return pending
}

