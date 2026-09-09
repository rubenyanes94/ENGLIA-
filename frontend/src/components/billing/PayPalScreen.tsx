import { faSpinner } from "@fortawesome/free-solid-svg-icons"
import { faPaypal } from "@fortawesome/free-brands-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"
import type { CheckoutResponse } from "../../api/types"
import { BackLink, ScreenHeader } from "./BillingModal"

export default function PayPalScreen({ onBack }: { onBack: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.post<CheckoutResponse>("/billing/checkout/paypal", { plan_code: "premium_monthly" })
      window.location.href = res.checkout_url
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar el pago.")
      setLoading(false)
    }
  }

  return (
    <>
      <ScreenHeader icon={faPaypal} tone="bg-indigo-500 text-white" title="PayPal Academy" subtitle="Suscripción mensual" />

      <p className="mt-4 text-center text-sm text-slate-500">
        Serás redirigido a PayPal para autorizar la suscripción mensual.
      </p>

      {error && <p className="mt-3 text-center text-sm text-amber-700">{error}</p>}

      <button
        onClick={start}
        disabled={loading}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-500 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 transition active:scale-[0.98] hover:bg-indigo-400 disabled:opacity-60"
      >
        {loading && <FontAwesomeIcon icon={faSpinner} spin />}
        Continuar a PayPal
      </button>

      <BackLink onBack={onBack} />
    </>
  )
}
