import { faBitcoin, faPaypal } from "@fortawesome/free-brands-svg-icons"
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core"
import { faCreditCard, faMobileScreenButton } from "@fortawesome/free-solid-svg-icons"
import type { BillingProvider } from "../../api/types"

/** Los cuatro métodos de pago, en el orden en que se ofrecen, con lo que
 * el alumno necesita para elegir SIN abrir cada uno: cómo se paga y si se
 * renueva solo. Única fuente para el registro y para el modal del perfil. */
export const METHODS: {
  id: BillingProvider
  label: string
  summary: string
  icon: IconDefinition
  tone: string
}[] = [
  { id: "pago_movil", label: "Pago Móvil", summary: "Transferencia en bolívares desde tu banco", icon: faMobileScreenButton, tone: "bg-red-500 text-white" },
  { id: "credit_card", label: "Tarjeta", summary: "Crédito o débito · se renueva cada mes", icon: faCreditCard, tone: "bg-ink-900 text-white" },
  { id: "paypal", label: "PayPal", summary: "Con tu cuenta PayPal · se renueva cada mes", icon: faPaypal, tone: "bg-brand-500 text-white" },
  { id: "binance_pay", label: "Binance Pay", summary: "Con cripto desde la app de Binance", icon: faBitcoin, tone: "bg-amber-400 text-slate-900" },
]
