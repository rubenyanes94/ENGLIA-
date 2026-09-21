import { faCircleCheck, faCircleXmark, faClock, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { MySubscription } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import AuthShell from "../components/auth/AuthShell"
import BillingModal from "../components/billing/BillingModal"
import { METHODS } from "../components/billing/methods"

// La pasarela devuelve al alumno en cuanto aprueba el pago, pero quien
// ACTIVA la suscripción es su webhook, que puede llegar unos segundos
// después. Se pregunta cada 3 s durante un minuto antes de rendirse.
const POLL_MS = 3000
const POLL_MAX_MS = 60_000

/** A dónde vuelve el alumno desde Stripe o PayPal (ver success_url y
 * return_url en app/billing/). Sin estas rutas, quien acababa de pagar
 * aterrizaba en la portada sin saber si el pago había funcionado. */
export default function BillingReturnPage({ outcome }: { outcome: "success" | "cancel" }) {
  // En el marco del registro y no dentro del aula: quien vuelve de pagar su
  // primera suscripción todavía no tiene acceso a la app.
  return (
    <AuthShell>
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm sm:p-8">
        {outcome === "success" ? <Success /> : <Canceled />}
      </div>
    </AuthShell>
  )
}

/** "Ir a mi aula" refrescando el usuario ANTES de navegar: con el de
 * memoria (todavía sin acceso) el candado lo devolvería a /suscripcion. */
function EnterAppButton({ label = "Ir a mi aula" }: { label?: string }) {
  const { refreshUser } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  return (
    <button
      type="button"
      disabled={busy}
      onClick={async () => {
        setBusy(true)
        await refreshUser()
        navigate("/dashboard", { replace: true })
      }}
      className="mt-6 inline-flex items-center gap-2 rounded-full bg-brand-600 px-6 py-3 font-semibold text-white transition hover:bg-brand-500 disabled:opacity-60"
    >
      {busy && <FontAwesomeIcon icon={faSpinner} spin />}
      {label}
    </button>
  )
}

function Success() {
  const [sub, setSub] = useState<MySubscription | null>(null)
  const [gaveUp, setGaveUp] = useState(false)

  useEffect(() => {
    let stopped = false
    const started = Date.now()
    async function poll() {
      try {
        const data = await api.get<MySubscription>("/billing/subscription")
        if (stopped) return
        setSub(data)
        if (data.has_access) return
      } catch {
        // Un fallo puntual no cierra la espera: se vuelve a intentar.
      }
      if (Date.now() - started >= POLL_MAX_MS) setGaveUp(true)
      else setTimeout(poll, POLL_MS)
    }
    void poll()
    return () => {
      stopped = true
    }
  }, [])

  if (sub?.has_access && sub.subscription) {
    const s = sub.subscription
    const method = METHODS.find((m) => m.id === s.provider)?.label ?? s.provider
    const until = s.current_period_end ? new Date(s.current_period_end).toLocaleDateString("es-VE", { day: "numeric", month: "long", year: "numeric" }) : null
    return (
      <>
        <FontAwesomeIcon icon={faCircleCheck} className="text-5xl text-emerald-500" />
        <h1 className="mt-4 text-2xl font-extrabold text-slate-900">¡Pago aceptado!</h1>
        <p className="mt-2 text-slate-500">
          {s.plan.name} con {method}.
          {until && (s.auto_renew ? ` Se renueva sola el ${until}.` : ` Tienes acceso hasta el ${until}.`)}
        </p>
        <EnterAppButton />
      </>
    )
  }

  if (gaveUp) {
    return (
      <>
        <FontAwesomeIcon icon={faClock} className="text-5xl text-amber-500" />
        <h1 className="mt-4 text-2xl font-extrabold text-slate-900">Estamos confirmando tu pago</h1>
        <p className="mt-2 text-slate-500">
          La pasarela todavía no nos ha confirmado el cobro. Suele tardar solo unos minutos: tu acceso se activará solo, y
          mientras tanto puedes seguir usando la app.
        </p>
        <EnterAppButton />
      </>
    )
  }

  return (
    <>
      <FontAwesomeIcon icon={faSpinner} spin className="text-4xl text-brand-500" />
      <h1 className="mt-4 text-2xl font-extrabold text-slate-900">Confirmando tu pago…</h1>
      <p className="mt-2 text-slate-500">Un momento: estamos activando tu suscripción.</p>
    </>
  )
}

function Canceled() {
  const { user } = useAuth()
  const [billingOpen, setBillingOpen] = useState(false)
  // Sin acceso (era su primera suscripción): volver al paso de pago. Con
  // acceso (renovaba desde el perfil): elegir otro método o volver al aula.
  const hasAccess = user?.access?.has_access === true
  return (
    <>
      <FontAwesomeIcon icon={faCircleXmark} className="text-5xl text-slate-300" />
      <h1 className="mt-4 text-2xl font-extrabold text-slate-900">No se completó el pago</h1>
      <p className="mt-2 text-slate-500">No te hemos cobrado nada. Puedes intentarlo otra vez o elegir otro método.</p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
        {hasAccess ? (
          <>
            <button
              type="button"
              onClick={() => setBillingOpen(true)}
              className="rounded-full bg-brand-600 px-6 py-3 font-semibold text-white transition hover:bg-brand-500"
            >
              Elegir método de pago
            </button>
            <Link to="/dashboard" className="rounded-full px-6 py-3 font-semibold text-slate-600 transition hover:bg-slate-100">
              Ir a mi aula
            </Link>
          </>
        ) : (
          <Link to="/suscripcion" className="rounded-full bg-brand-600 px-6 py-3 font-semibold text-white transition hover:bg-brand-500">
            Volver a elegir cómo pagar
          </Link>
        )}
      </div>
      {billingOpen && <BillingModal onClose={() => setBillingOpen(false)} />}
    </>
  )
}
