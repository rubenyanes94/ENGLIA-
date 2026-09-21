import { faSpinner, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { faBitcoin } from "@fortawesome/free-brands-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import QRCode from "qrcode"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"
import type { CheckoutResponse, Plan } from "../../api/types"
import { BackLink, ScreenHeader } from "./BillingModal"
import { PriceTag, Steps } from "./PaymentInfo"
import CopyField from "./CopyField"

/** Binance Pay.
 *
 * El QR se genera a partir de la URL REAL que devuelve la pasarela para
 * ESTA orden, no de un identificador fijo pintado en el diseño. Importa:
 * un QR estático manda a todos los alumnos al mismo sitio sin decir quién
 * pagó ni por qué plan, así que ningún pago se puede casar con su
 * suscripción y todos acaban en verificación manual. La orden que crea el
 * backend lleva dentro el id de la suscripción, que es lo que permite al
 * webhook activarla sola.
 */
export default function BinanceScreen({ plan, onBack }: { plan: Plan; onBack: () => void }) {
  const [qr, setQr] = useState<string | null>(null)
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .post<CheckoutResponse>("/billing/checkout/binance_pay", { plan_code: plan.code })
      .then(async (res) => {
        if (cancelled) return
        setUrl(res.checkout_url)
        setQr(await QRCode.toDataURL(res.checkout_url, { width: 320, margin: 1 }))
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "No se pudo crear la orden.")
      })
    return () => {
      cancelled = true
    }
  }, [plan.code])

  return (
    <>
      <ScreenHeader icon={faBitcoin} tone="bg-amber-400 text-slate-900" title="Binance Pay" subtitle="Pago con cripto" />

      {/* Binance no cobra solo cada mes: cada pago cubre un periodo y el
          siguiente se paga igual, desde el perfil. Decirlo ANTES de pagar
          evita el "¿por qué perdí el acceso?" treinta días después. */}
      <PriceTag plan={plan} note="Cubre 30 días · no se renueva solo: el mes siguiente vuelves a pagar" />

      <Steps
        items={[
          "Abre la app de Binance y entra en Pay.",
          "Escanea este código (o abre el enlace desde tu móvil).",
          "Confirma el pago. Tu acceso se activa solo en cuanto Binance lo confirma.",
        ]}
      />

      <div className="mt-5 flex justify-center">
        {qr ? (
          <img src={qr} alt="Código QR para pagar con Binance Pay" className="h-44 w-44 rounded-2xl border-4 border-amber-400" />
        ) : (
          <div className="flex h-44 w-44 items-center justify-center rounded-2xl border-4 border-slate-100 text-slate-300">
            <FontAwesomeIcon icon={error ? faTriangleExclamation : faSpinner} spin={!error} className="text-2xl" />
          </div>
        )}
      </div>

      {error ? (
        <p className="mt-4 text-center text-sm text-amber-700">{error}</p>
      ) : (
        url && <div className="mt-4"><CopyField label="Enlace de pago" value={url} /></div>
      )}

      <a
        href={url ?? "#"}
        target="_blank"
        rel="noreferrer"
        aria-disabled={!url}
        className={`mt-5 block rounded-2xl py-3.5 text-center text-sm font-bold text-slate-900 transition active:scale-[0.98] ${
          url ? "bg-amber-400 hover:bg-amber-300" : "pointer-events-none bg-slate-100 text-slate-400"
        }`}
      >
        Abrir en Binance
      </a>

      <BackLink onBack={onBack} />
    </>
  )
}
