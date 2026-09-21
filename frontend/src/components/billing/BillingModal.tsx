import { faArrowLeft, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core"
import { useEffect, useState } from "react"
import Modal from "../Modal"
import { api } from "../../api/client"
import type { BillingOptions } from "../../api/types"
import PaymentMethodPicker from "./PaymentMethodPicker"

/** El flujo de facturación desde el perfil: el mismo selector de métodos
 * que el paso 2 del registro, dentro de un modal. */
export default function BillingModal({ onClose }: { onClose: () => void }) {
  const [options, setOptions] = useState<BillingOptions | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    api.get<BillingOptions>("/billing/options").then(setOptions).catch(() => setError(true))
  }, [])

  return (
    <Modal onClose={onClose}>
      <h2 className="text-center text-xl font-extrabold text-slate-900">Suscripción Premium</h2>
      <p className="mt-1 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">Elige cómo pagar</p>

      <div className="mt-5">
        {options ? (
          <PaymentMethodPicker options={options} onDone={onClose} />
        ) : (
          <p className="py-8 text-center text-sm text-slate-400">
            {error ? "No se pudieron cargar los métodos de pago." : <FontAwesomeIcon icon={faSpinner} spin />}
          </p>
        )}
      </div>

      <button
        onClick={onClose}
        className="mt-5 w-full rounded-2xl bg-slate-100 py-3.5 text-sm font-bold uppercase tracking-wide text-slate-500 transition active:scale-[0.98] hover:bg-slate-200"
      >
        Cerrar
      </button>
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
