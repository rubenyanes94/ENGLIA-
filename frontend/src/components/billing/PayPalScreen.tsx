import { faSpinner } from "@fortawesome/free-solid-svg-icons"
import { faPaypal } from "@fortawesome/free-brands-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"
import type { CheckoutResponse, Plan } from "../../api/types"
import { BackLink, ScreenHeader } from "./BillingModal"
import { PriceTag, Steps } from "./PaymentInfo"

export default function PayPalScreen({ plan, onBack }: { plan: Plan; onBack: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.post<CheckoutResponse>("/billing/checkout/paypal", { plan_code: plan.code })
      window.location.href = res.checkout_url
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar el pago.")
      setLoading(false)
    }
  }

  return (
    <>
      <ScreenHeader icon={faPaypal} tone="bg-brand-500 text-white" title="PayPal" subtitle="Suscripción mensual" />

      <PriceTag plan={plan} note="PayPal lo cobra cada mes · cancela cuando quieras desde PayPal" />

      <Steps
        items={[
          "Pulsa el botón y te llevamos a PayPal.",
          "Inicia sesión en tu cuenta y aprueba la suscripción.",
          "Al aprobarla, vuelves aquí con tu acceso Premium ya activo.",
        ]}
      />

      {error && <p className="mt-3 text-center text-sm text-amber-700">{error}</p>}

      <button
        onClick={start}
        disabled={loading}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-brand-500 py-3.5 text-sm font-bold text-white shadow-lg shadow-brand-500/20 transition active:scale-[0.98] hover:bg-brand-400 disabled:opacity-60"
      >
        {loading && <FontAwesomeIcon icon={faSpinner} spin />}
        Continuar a PayPal
      </button>

      <BackLink onBack={onBack} />
    </>
  )
}
