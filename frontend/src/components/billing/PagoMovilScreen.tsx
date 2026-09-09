import { faCircleCheck, faMobileScreenButton, faSpinner, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState, type FormEvent } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"
import type { PagoMovilInfo } from "../../api/types"
import { BackLink, ScreenHeader } from "./BillingModal"
import CopyField from "./CopyField"

/** Pago Móvil, en dos pasos.
 *
 * Es el único método sin pasarela: el alumno transfiere desde la app de
 * su banco y nadie se entera. Por eso el diseño original —una pantalla
 * con los datos de la academia y un botón "Finalizar"— dejaba el circuito
 * abierto: sin la referencia de la transferencia, ese pago no se puede
 * casar con nadie y el alumno se queda sin acceso habiendo pagado.
 *
 * Así que "Finalizar" no cierra: lleva al paso donde el alumno declara lo
 * que transfirió. Eso es exactamente lo que espera el backend
 * (POST /billing/payments/pago-movil) y lo que un admin necesita para
 * cotejarlo contra el estado de cuenta.
 */
type Paso = "datos" | "declarar" | "listo"

export default function PagoMovilScreen({ onBack, onDone }: { onBack: () => void; onDone: () => void }) {
  const [paso, setPaso] = useState<Paso>("datos")
  const [info, setInfo] = useState<PagoMovilInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<PagoMovilInfo>("/billing/pago-movil-info")
      .then(setInfo)
      .catch(() => setError("No se pudieron cargar los datos de la academia."))
  }, [])

  if (paso === "listo") {
    return (
      <>
        <ScreenHeader
          icon={faCircleCheck}
          tone="bg-emerald-500 text-white"
          title="Pago declarado"
          subtitle="Pendiente de verificación"
        />
        <p className="mt-4 text-center text-sm text-slate-500">
          Vamos a cotejar tu referencia con el estado de cuenta. Te avisamos en cuanto quede confirmado.
        </p>
        <button
          onClick={onDone}
          className="mt-5 w-full rounded-2xl bg-slate-100 py-3.5 text-sm font-bold uppercase tracking-wide text-slate-500 transition active:scale-[0.98] hover:bg-slate-200"
        >
          Cerrar
        </button>
      </>
    )
  }

  if (paso === "declarar") {
    return <DeclaracionForm onBack={() => setPaso("datos")} onSuccess={() => setPaso("listo")} />
  }

  return (
    <>
      <ScreenHeader
        icon={faMobileScreenButton}
        tone="bg-red-500 text-white"
        title="Pago Móvil Academy"
        subtitle="Datos para transferencia"
      />

      <div className="mt-5 space-y-2.5">
        {!info && !error && (
          <p className="py-6 text-center text-slate-300">
            <FontAwesomeIcon icon={faSpinner} spin className="text-xl" />
          </p>
        )}

        {/* Sin datos configurados NO se enseña nada parecido a una cuenta.
            Un alumno que transfiere a una cédula de ejemplo pierde su
            dinero de verdad — es el peor fallo posible de esta pantalla. */}
        {info && !info.configured && (
          <p className="flex items-start gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <FontAwesomeIcon icon={faTriangleExclamation} className="mt-0.5" />
            Este método aún no está disponible. Usa otro por ahora.
          </p>
        )}

        {info?.configured && (
          <>
            <CopyField label="Banco" value={info.bank} />
            <CopyField label="Cédula / RIF" value={info.document} />
            <CopyField label="Teléfono" value={info.phone} />
          </>
        )}

        {error && <p className="text-center text-sm text-amber-700">{error}</p>}
      </div>

      <button
        onClick={() => setPaso("declarar")}
        disabled={!info?.configured}
        className="mt-5 w-full rounded-2xl bg-blue-600 py-3.5 text-sm font-bold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
      >
        Finalizar
      </button>

      <BackLink onBack={onBack} />
    </>
  )
}

function DeclaracionForm({ onBack, onSuccess }: { onBack: () => void; onSuccess: () => void }) {
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    setSending(true)
    setError(null)
    try {
      await api.post("/billing/payments/pago-movil", {
        plan_code: "premium_monthly",
        payer_cedula: data.get("cedula"),
        payer_phone: data.get("telefono"),
        payer_bank: data.get("banco"),
        reference_number: data.get("referencia"),
        amount_bs: Number(data.get("monto")),
        // El input date da "YYYY-MM-DD" y el backend espera un datetime.
        paid_at: new Date(String(data.get("fecha"))).toISOString(),
      })
      onSuccess()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el pago.")
      setSending(false)
    }
  }

  return (
    <>
      <ScreenHeader
        icon={faMobileScreenButton}
        tone="bg-red-500 text-white"
        title="Confirma tu pago"
        subtitle="Datos de tu transferencia"
      />

      <form onSubmit={submit} className="mt-5 space-y-2.5">
        <Campo name="referencia" label="Número de referencia" placeholder="000123456" required />
        <div className="grid grid-cols-2 gap-2.5">
          <Campo name="cedula" label="Tu cédula" placeholder="V-12345678" required />
          <Campo name="telefono" label="Tu teléfono" placeholder="0412-1234567" required />
        </div>
        <Campo name="banco" label="Tu banco" placeholder="Banesco" required />
        <div className="grid grid-cols-2 gap-2.5">
          <Campo name="monto" label="Monto en Bs" type="number" step="0.01" placeholder="0,00" required />
          <Campo name="fecha" label="Fecha del pago" type="date" required />
        </div>

        {error && <p className="text-center text-sm text-amber-700">{error}</p>}

        <button
          type="submit"
          disabled={sending}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 py-3.5 text-sm font-bold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500 disabled:opacity-60"
        >
          {sending && <FontAwesomeIcon icon={faSpinner} spin />}
          Enviar para verificación
        </button>
      </form>

      <BackLink onBack={onBack} />
    </>
  )
}

function Campo({ name, label, ...props }: { name: string; label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</span>
      <input
        name={name}
        {...props}
        className="mt-1 w-full rounded-xl bg-slate-50 px-3.5 py-2.5 text-sm text-slate-800 outline-none ring-blue-500 transition placeholder:text-slate-300 focus:ring-2"
      />
    </label>
  )
}
