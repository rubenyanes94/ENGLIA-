import { faArrowRight, faCircleCheck, faFlask, faRightFromBracket, faSpinner, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Navigate, useNavigate } from "react-router-dom"
import { api } from "../api/client"
import type { BillingOptions, BillingProvider } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import Modal from "../components/Modal"
import AuthShell from "../components/auth/AuthShell"
import Stepper from "../components/auth/Stepper"
import PaymentMethodPicker from "../components/billing/PaymentMethodPicker"
import { planPeriod, planPrice } from "../components/billing/PaymentInfo"

/** Paso 2 del registro, y a donde vuelve cualquier alumno sin acceso.
 *
 * El flujo es registro → pago → "pago recibido" → la app. La cuenta se
 * crea en el paso 1 (cada pago tiene que ir a nombre de alguien), pero sin
 * pagar no se entra: ProtectedRoute trae aquí a quien lo intente por
 * cualquier otro camino (volver al inicio, escribir la URL, recargar), y
 * el backend responde 402 a la API de la app. Por eso aquí no hay "volver
 * al inicio" ni "pagar después": la salida es cerrar sesión. */
export default function SubscribePage() {
  const { user, isLoading, logout, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [options, setOptions] = useState<BillingOptions | null>(null)
  const [error, setError] = useState(false)
  // "test" = el botón de prueba: el pago queda ACEPTADO (no pendiente).
  const [declared, setDeclared] = useState<BillingProvider | "test" | null>(null)
  const [reporting, setReporting] = useState(false)
  const [testError, setTestError] = useState<string | null>(null)
  const [entering, setEntering] = useState(false)

  useEffect(() => {
    api.get<BillingOptions>("/billing/options").then(setOptions).catch(() => setError(true))
  }, [])

  if (isLoading) return null
  if (!user) return <Navigate to="/login?mode=register" replace />
  if (user.role === "manager") return <Navigate to="/gerencia" replace />
  // Ya tiene acceso (pagó, está exento o es del equipo): nada que hacer aquí.
  // Salvo si acaba de declarar un pago: entonces se queda a ver su modal.
  if (user.access?.has_access && !declared) return <Navigate to="/dashboard" replace />

  async function enterApp() {
    setEntering(true)
    // Refrescar ANTES de navegar: con el usuario viejo en memoria (sin
    // acceso), ProtectedRoute lo devolvería aquí.
    await refreshUser()
    navigate("/dashboard", { replace: true })
  }

  async function reportTestPayment() {
    setReporting(true)
    setTestError(null)
    try {
      await api.post("/billing/test-payment")
      setDeclared("test")
    } catch {
      setTestError("No se pudo registrar el pago de prueba.")
    } finally {
      setReporting(false)
    }
  }

  function handleLogout() {
    logout()
    navigate("/", { replace: true })
  }

  const firstName = user.full_name.split(" ")[0]
  const rejection = user.access?.last_rejection_reason

  return (
    <AuthShell
      top={
        <button
          type="button"
          onClick={handleLogout}
          className="mb-6 flex items-center gap-2 text-sm text-slate-400 hover:text-slate-600"
        >
          <FontAwesomeIcon icon={faRightFromBracket} /> Cerrar sesión
        </button>
      }
    >
      <Stepper current={2} />
      <h1 className="text-3xl font-extrabold">{rejection ? `Hola de nuevo, ${firstName}` : `¡Cuenta creada, ${firstName}!`}</h1>
      <p className="mt-2 text-slate-500">Elige cómo pagar tu suscripción para empezar. Tardas un minuto.</p>

      {rejection && (
        <p className="mt-4 flex items-start gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <FontAwesomeIcon icon={faTriangleExclamation} className="mt-0.5 shrink-0" />
          <span>
            <strong>No pudimos confirmar tu último pago:</strong> {rejection}. Revisa los datos e inténtalo de nuevo, o
            escríbenos a hola@espikin.com.
          </span>
        </p>
      )}

      {options ? (
        <>
          <div className="mt-5 flex items-center justify-between gap-4 rounded-2xl border border-brand-100 bg-white p-4">
            <div className="min-w-0">
              <p className="font-bold text-slate-900">{options.plan.name}</p>
              <p className="text-xs text-slate-500">Los 6 niveles, tutor ilimitado 24/7 y certificación · cancela cuando quieras</p>
            </div>
            <p className="shrink-0 text-right">
              <span className="text-2xl font-extrabold text-slate-900">{planPrice(options.plan)}</span>
              <span className="block text-xs text-slate-500">USD / {planPeriod(options.plan)}</span>
            </p>
          </div>
          {options.test_mode && (
            // Solo en desarrollo (el backend lo decide y además rechaza la
            // llamada en producción). Recuadro discontinuo y etiquetado para
            // que nadie lo confunda con un método de pago de verdad.
            <div className="mt-5 rounded-2xl border-2 border-dashed border-violet-300 bg-violet-50/60 p-4">
              <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-violet-700">
                <FontAwesomeIcon icon={faFlask} /> Modo de prueba
              </p>
              <p className="mt-1 text-sm text-slate-600">Activa la suscripción sin pagar para probar el flujo completo.</p>
              <button
                type="button"
                onClick={reportTestPayment}
                disabled={reporting}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-violet-600 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-60"
              >
                {reporting && <FontAwesomeIcon icon={faSpinner} spin />}
                Reportar pago
              </button>
              {testError && <p className="mt-2 text-center text-sm text-rose-700">{testError}</p>}
            </div>
          )}
          <div className="mt-5">
            {/* Tarjeta y PayPal salen de la página y vuelven por /billing/success;
                Pago Móvil y Binance se declaran aquí y abren el modal. */}
            <PaymentMethodPicker options={options} onDone={enterApp} onDeclared={setDeclared} doneLabel="Entrar a mi aula" />
          </div>
        </>
      ) : (
        <p className="py-10 text-center text-sm text-slate-400">
          {error ? "No se pudieron cargar los métodos de pago. Recarga la página." : <FontAwesomeIcon icon={faSpinner} spin />}
        </p>
      )}

      {declared && (
        // Sin cerrar con Escape ni clic fuera: la única salida es entrar.
        <Modal onClose={() => {}} dismissible={false}>
          <div className="text-center">
            <FontAwesomeIcon icon={faCircleCheck} className="text-5xl text-emerald-500" />
            <h2 className="mt-4 text-2xl font-extrabold text-slate-900">{declared === "test" ? "¡Pago aceptado!" : "¡Pago recibido!"}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-500">
              {declared === "test" ? (
                "Tu suscripción Premium está activa por 30 días. ¡Bienvenido a Espikin!"
              ) : (
                <>
                  {declared === "binance_pay" ? "Vamos a confirmar tu orden en Binance." : "Vamos a confirmar tu transferencia con el banco."}{" "}
                  Ya puedes empezar a usar Espikin: si hubiera algún problema con el pago, te lo diremos aquí mismo.
                </>
              )}
            </p>
            <button
              type="button"
              onClick={enterApp}
              disabled={entering}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-brand-600 py-3.5 font-semibold text-white transition hover:bg-brand-500 disabled:opacity-60"
            >
              {entering ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faArrowRight} />}
              Entrar a mi aula
            </button>
          </div>
        </Modal>
      )}
    </AuthShell>
  )
}
