import { faChevronRight } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"
import type { BillingOptions, BillingProvider } from "../../api/types"
import BinancePersonalScreen from "./BinancePersonalScreen"
import BinanceScreen from "./BinanceScreen"
import CardScreen from "./CardScreen"
import { METHODS } from "./methods"
import PagoMovilScreen from "./PagoMovilScreen"
import PayPalScreen from "./PayPalScreen"

/** Elegir método y, al elegirlo, su pantalla con cuánto y cómo pagar.
 *
 * Lo usan el registro (paso 2) y el modal de facturación del perfil, para
 * que el alumno vea exactamente lo mismo en los dos sitios.
 *
 * Los cuatro NO se comportan igual por debajo aunque aquí parezcan
 * hermanos, y la diferencia es del negocio, no del código: tarjeta y
 * PayPal redirigen a la pasarela, Binance genera una orden con su propio
 * QR, y Pago Móvil no tiene pasarela — el alumno transfiere desde su banco
 * y luego DECLARA los datos para que alguien los verifique a mano. Por eso
 * cada uno tiene su pantalla en vez de un formulario genérico. */
export default function PaymentMethodPicker({
  options,
  onDone,
  doneLabel,
}: {
  options: BillingOptions
  /** Cuando el alumno termina un pago que no sale de la página (Pago Móvil declarado). */
  onDone: () => void
  doneLabel?: string
}) {
  const [selected, setSelected] = useState<BillingProvider | null>(null)
  const available = new Map(options.methods.map((m) => [m.id, m.available]))
  const back = () => setSelected(null)
  const plan = options.plan

  if (selected === "credit_card") return <CardScreen plan={plan} onBack={back} />
  if (selected === "paypal") return <PayPalScreen plan={plan} onBack={back} />
  if (selected === "binance_pay") {
    // Sin claves de comerciante, Binance es un envío a la cuenta personal
    // de la academia que se verifica a mano (ver BinancePersonalScreen).
    const mode = options.methods.find((m) => m.id === "binance_pay")?.mode
    return mode === "merchant" ? (
      <BinanceScreen plan={plan} onBack={back} />
    ) : (
      <BinancePersonalScreen plan={plan} onBack={back} onDone={onDone} doneLabel={doneLabel} />
    )
  }
  if (selected === "pago_movil") return <PagoMovilScreen plan={plan} onBack={back} onDone={onDone} doneLabel={doneLabel} />

  const anyAvailable = options.methods.some((m) => m.available)

  return (
    <div>
      <ul className="space-y-2.5" aria-label="Métodos de pago">
        {METHODS.map((m) => {
          const ok = available.get(m.id) ?? false
          return (
            <li key={m.id}>
              <button
                type="button"
                disabled={!ok}
                onClick={() => setSelected(m.id)}
                className="flex w-full items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 text-left transition enabled:hover:border-brand-300 enabled:hover:shadow-md enabled:active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-slate-50"
              >
                <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-lg ${ok ? m.tone : "bg-slate-200 text-slate-400"}`}>
                  <FontAwesomeIcon icon={m.icon} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className={`block font-semibold ${ok ? "text-slate-900" : "text-slate-400"}`}>{m.label}</span>
                  <span className="block text-xs text-slate-500">{ok ? m.summary : "Próximamente"}</span>
                </span>
                {ok && <FontAwesomeIcon icon={faChevronRight} className="text-xs text-slate-300" />}
              </button>
            </li>
          )
        })}
      </ul>
      {!anyAvailable && (
        <p className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Todavía no hay ningún método de pago activo. Puedes empezar a usar la app y suscribirte más adelante desde tu perfil.
        </p>
      )}
    </div>
  )
}
