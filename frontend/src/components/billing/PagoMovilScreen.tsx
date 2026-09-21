import { faCircleCheck, faMobileScreenButton, faSpinner, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState, type FormEvent } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"
import type { PagoMovilInfo, Plan } from "../../api/types"
import { BackLink, ScreenHeader } from "./BillingModal"
import { Steps, planPrice } from "./PaymentInfo"
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

export default function PagoMovilScreen({
  plan,
  onBack,
  onDone,
  onDeclared,
  doneLabel = "Cerrar",
}: {
  plan: Plan
  onBack: () => void
  onDone: () => void
  /** Si se pasa, al declarar el pago se llama esto en vez de mostrar la
   * confirmación en la propia pantalla (el registro abre su modal de
   * "pago recibido" y da paso a la app). */
  onDeclared?: () => void
  /** Texto del botón final: "Cerrar" en el modal, "Ir a mi aula" en el registro. */
  doneLabel?: string
}) {
  const [paso, setPaso] = useState<Paso>("datos")
  const [info, setInfo] = useState<PagoMovilInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<PagoMovilInfo>(`/billing/pago-movil-info?plan_code=${plan.code}`)
      .then(setInfo)
      .catch(() => setError("No se pudieron cargar los datos de la academia."))
  }, [plan.code])

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
          Vamos a cotejar tu referencia con el estado de cuenta. Tu acceso Premium se activa en cuanto quede
          confirmado; mientras tanto puedes empezar a usar la app.
        </p>
        <button
          onClick={onDone}
          className="mt-5 w-full rounded-2xl bg-brand-600 py-3.5 text-sm font-bold text-white transition active:scale-[0.98] hover:bg-brand-500"
        >
          {doneLabel}
        </button>
      </>
    )
  }

  if (paso === "declarar") {
    return <DeclaracionForm plan={plan} amountBs={info?.amount_bs ?? null} onBack={() => setPaso("datos")} onSuccess={() => (onDeclared ? onDeclared() : setPaso("listo"))} />
  }

  return (
    <>
      <ScreenHeader
        icon={faMobileScreenButton}
        tone="bg-red-500 text-white"
        title="Pago Móvil"
        subtitle="Transferencia en bolívares"
      />

      {info?.configured && (
        <Steps
          items={[
            "Desde la app de tu banco, haz un Pago Móvil con estos datos.",
            "Guarda el número de referencia que te da el banco.",
            "Pulsa \"Ya hice el pago\" y escribe los datos de tu transferencia para que la verifiquemos.",
          ]}
        />
      )}

      <div className="mt-4 space-y-2.5">
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
            {/* Los cuatro datos que se teclean en el banco, juntos. El monto
                en Bs primero: es lo que cambia y lo que más se equivoca. Sin
                tasa configurada no se inventa un monto. */}
            {info.amount_bs != null ? (
              <CopyField
                label={`Monto · ${planPrice(plan)} a tasa BCV${info.rate_date ? ` del ${formatRateDate(info.rate_date)}` : ""} (${formatBs(info.bs_per_usd)} Bs/$)`}
                value={`Bs ${formatBs(info.amount_bs)}`}
                copyValue={info.amount_bs.toFixed(2).replace(".", ",")}
              />
            ) : (
              <p className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
                Monto: el equivalente a <strong>{planPrice(plan)}</strong> en bolívares a la tasa oficial del BCV del día.
              </p>
            )}
            <CopyField label="Banco" value={info.bank} />
            <CopyField label="Cédula / RIF" value={info.document} />
            <CopyField label="Teléfono" value={info.phone} />
            <p className="px-1 pt-1 text-xs text-slate-500">
              Cubre 30 días. No se renueva solo: el mes siguiente vuelves a pagar desde tu perfil.
            </p>
          </>
        )}

        {error && <p className="text-center text-sm text-amber-700">{error}</p>}
      </div>

      <button
        onClick={() => setPaso("declarar")}
        disabled={!info?.configured}
        className="mt-5 w-full rounded-2xl bg-brand-600 py-3.5 text-sm font-bold text-white shadow-lg shadow-brand-600/20 transition active:scale-[0.98] hover:bg-brand-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
      >
        Ya hice el pago
      </button>

      <BackLink onBack={onBack} />
    </>
  )
}

function DeclaracionForm({
  plan,
  amountBs,
  onBack,
  onSuccess,
}: {
  plan: Plan
  amountBs: number | null
  onBack: () => void
  onSuccess: () => void
}) {
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    setSending(true)
    setError(null)
    try {
      await api.post("/billing/payments/pago-movil", {
        plan_code: plan.code,
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
          {/* Monto y fecha ya rellenos con lo esperado: casi siempre es
              eso, y un campo menos que teclear. Se pueden corregir. */}
          <Campo name="monto" label="Monto en Bs" type="number" step="0.01" placeholder="0,00" defaultValue={amountBs ?? undefined} required />
          <Campo name="fecha" label="Fecha del pago" type="date" defaultValue={todayIso()} max={todayIso()} required />
        </div>

        {error && <p className="text-center text-sm text-amber-700">{error}</p>}

        <button
          type="submit"
          disabled={sending}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-brand-600 py-3.5 text-sm font-bold text-white shadow-lg shadow-brand-600/20 transition active:scale-[0.98] hover:bg-brand-500 disabled:opacity-60"
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
        className="mt-1 w-full rounded-xl bg-white px-3.5 py-2.5 text-sm text-slate-800 outline-none ring-1 ring-slate-200 transition placeholder:text-slate-300 focus:ring-2 focus:ring-brand-500"
      />
    </label>
  )
}

const bsFormat = new Intl.NumberFormat("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function formatBs(value: number | null): string {
  return value == null ? "" : bsFormat.format(value)
}

const rateDateFormat = new Intl.DateTimeFormat("es-VE", { weekday: "short", day: "numeric", month: "numeric" })

/** "2026-09-21" → "lun, 21/9". Se parsea a mano: new Date("2026-09-21") lo
 * lee como medianoche UTC, que en Venezuela aún es el día anterior. */
function formatRateDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number)
  return rateDateFormat.format(new Date(y, m - 1, d))
}

/** Hoy en hora LOCAL del alumno ("YYYY-MM-DD"). toISOString() daría la
 * fecha en UTC, que a partir de las 8 de la noche en Venezuela ya es mañana. */
function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

