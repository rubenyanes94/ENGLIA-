import { faCreditCard, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"
import type { CheckoutResponse } from "../../api/types"
import { BackLink, ScreenHeader } from "./BillingModal"

/** Pago con tarjeta.
 *
 * El diseño original pedía aquí un formulario con número de tarjeta,
 * MM/YY y CVC. NO se implementó así, y la razón no es de estilo:
 *
 * 1. El backend no tiene dónde recibir un número de tarjeta. Su flujo
 *    (billing.start_checkout → stripe_gateway.create_checkout_session)
 *    devuelve una URL a la que se REDIRIGE al alumno; los datos se tecleen
 *    en el dominio de la pasarela, nunca en el nuestro.
 * 2. Un formulario que pide PAN y CVC mete a Espikin en el alcance de
 *    PCI-DSS entero. Ese es el motivo por el que todas las pasarelas
 *    modernas te dan una página alojada o un iframe.
 * 3. Un formulario que recoge datos de tarjeta y no puede cobrar con
 *    ellos es, para el alumno que los teclea, indistinguible de uno que
 *    sí puede.
 *
 * Así que la pantalla conserva el peso visual del diseño, pero lleva al
 * alumno a la pasarela en vez de pedirle los dígitos aquí.
 */
export default function CardScreen({ onBack }: { onBack: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.post<CheckoutResponse>("/billing/checkout/credit_card", {
        plan_code: "premium_monthly",
      })
      window.location.href = res.checkout_url
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar el pago.")
      setLoading(false)
    }
  }

  return (
    <>
      <ScreenHeader icon={faCreditCard} tone="bg-slate-900 text-white" title="Vincular Tarjeta" subtitle="Suscripción Premium" />

      <p className="mt-4 text-center text-sm text-slate-500">
        Te llevamos a la pasarela segura para introducir tu tarjeta. Espikin nunca ve ni guarda tus dígitos.
      </p>

      {error && <p className="mt-3 text-center text-sm text-amber-700">{error}</p>}

      <button
        onClick={start}
        disabled={loading}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 py-3.5 text-sm font-bold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500 disabled:opacity-60"
      >
        {loading && <FontAwesomeIcon icon={faSpinner} spin />}
        Guardar Método
      </button>

      <BackLink onBack={onBack} />
    </>
  )
}
