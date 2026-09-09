import { faArrowLeft, faCreditCard, faMobileScreenButton } from "@fortawesome/free-solid-svg-icons"
import { faBitcoin, faPaypal } from "@fortawesome/free-brands-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core"
import { useState } from "react"
import Modal from "../Modal"
import type { BillingProvider } from "../../api/types"
import CardScreen from "./CardScreen"
import PayPalScreen from "./PayPalScreen"
import BinanceScreen from "./BinanceScreen"
import PagoMovilScreen from "./PagoMovilScreen"

/** El flujo de facturación completo: elegir método y, según cuál, su
 * pantalla.
 *
 * Los cuatro NO se comportan igual por debajo aunque en el selector
 * parezcan hermanos, y la diferencia es del negocio, no del código:
 * tarjeta y PayPal redirigen a la pasarela, Binance genera una orden con
 * su propio QR, y Pago Móvil no tiene pasarela ninguna — el alumno
 * transfiere desde su banco y luego DECLARA los datos para que alguien
 * los verifique a mano. Por eso cada uno tiene su pantalla en vez de un
 * formulario genérico con un `switch` dentro.
 */
const METODOS: { id: BillingProvider; label: string; icon: IconDefinition; tone: string }[] = [
  { id: "credit_card", label: "Mastercard", icon: faCreditCard, tone: "bg-slate-900 text-white" },
  { id: "paypal", label: "PayPal", icon: faPaypal, tone: "bg-indigo-500 text-white" },
  { id: "binance_pay", label: "Binance Pay", icon: faBitcoin, tone: "bg-amber-400 text-slate-900" },
  { id: "pago_movil", label: "Pago Móvil (BS)", icon: faMobileScreenButton, tone: "bg-red-500 text-white" },
]

export default function BillingModal({ onClose }: { onClose: () => void }) {
  const [selected, setSelected] = useState<BillingProvider | null>(null)
  const back = () => setSelected(null)

  return (
    <Modal onClose={onClose}>
      {selected === null && (
        <>
          <h2 className="text-center text-xl font-extrabold text-slate-900">Facturación</h2>
          <p className="mt-1 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Selecciona un método para ver detalles
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            {METODOS.map((metodo) => (
              <button
                key={metodo.id}
                onClick={() => setSelected(metodo.id)}
                className="flex flex-col items-center gap-3 rounded-2xl border border-slate-200 bg-white p-5 transition active:scale-95 hover:border-slate-300 hover:shadow-md"
              >
                <span className={`flex h-11 w-11 items-center justify-center rounded-xl text-lg ${metodo.tone}`}>
                  <FontAwesomeIcon icon={metodo.icon} />
                </span>
                <span className="text-center text-[10px] font-bold uppercase leading-tight tracking-wide text-slate-500">
                  {metodo.label}
                </span>
              </button>
            ))}
          </div>

          <button
            onClick={onClose}
            className="mt-5 w-full rounded-2xl bg-slate-100 py-3.5 text-sm font-bold uppercase tracking-wide text-slate-500 transition active:scale-[0.98] hover:bg-slate-200"
          >
            Cerrar
          </button>
        </>
      )}

      {selected === "credit_card" && <CardScreen onBack={back} />}
      {selected === "paypal" && <PayPalScreen onBack={back} />}
      {selected === "binance_pay" && <BinanceScreen onBack={back} />}
      {selected === "pago_movil" && <PagoMovilScreen onBack={back} onDone={onClose} />}
    </Modal>
  )
}

/** Cabecera común a las cuatro pantallas: icono en su pastilla de color,
 * título y subtítulo en versalitas. */
export function ScreenHeader({
  icon,
  tone,
  title,
  subtitle,
}: {
  icon: IconDefinition
  tone: string
  title: string
  subtitle: string
}) {
  return (
    <div className="text-center">
      <span className={`mx-auto flex h-12 w-12 items-center justify-center rounded-2xl text-lg ${tone}`}>
        <FontAwesomeIcon icon={icon} />
      </span>
      <h2 className="mt-3 text-xl font-extrabold text-slate-900">{title}</h2>
      <p className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{subtitle}</p>
    </div>
  )
}

export function BackLink({ onBack }: { onBack: () => void }) {
  return (
    <button
      onClick={onBack}
      className="mt-3 flex w-full items-center justify-center gap-2 py-1 text-[11px] font-bold uppercase tracking-wide text-slate-400 transition hover:text-slate-600"
    >
      <FontAwesomeIcon icon={faArrowLeft} className="text-[9px]" /> Atrás
    </button>
  )
}
