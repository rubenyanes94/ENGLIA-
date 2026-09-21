import { faCircleCheck, faSpinner, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { faBitcoin } from "@fortawesome/free-brands-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import QRCode from "qrcode"
import { useEffect, useState, type FormEvent, type InputHTMLAttributes } from "react"
import { api } from "../../api/client"
import { ApiError } from "../../api/types"
import type { BinancePersonalInfo, Plan } from "../../api/types"
import { BackLink, ScreenHeader } from "./BillingModal"
import CopyField from "./CopyField"
import { Steps } from "./PaymentInfo"

/** Binance Pay a la cuenta PERSONAL de la academia, en dos pasos como Pago
 * Móvil: pagar desde la app de Binance y declarar la orden.
 *
 * Sin cuenta de comerciante no hay aviso automático de Binance, así que
 * el pago lo verifica una persona en el historial. Por eso el segundo
 * paso pide el ID de la orden: es lo que permite encontrar ESE pago entre
 * todos los recibidos, y el backend no deja declarar la misma orden dos veces.
 *
 * El QR se genera aquí a partir del enlace configurado (el mismo que
 * codifica el QR de "Recibir" de la app de Binance): sale nítido a
 * cualquier tamaño y no hay que subir ninguna imagen. */
type Paso = "datos" | "declarar" | "listo"

export default function BinancePersonalScreen({
  plan,
  onBack,
  onDone,
  doneLabel = "Cerrar",
}: {
  plan: Plan
  onBack: () => void
  onDone: () => void
  doneLabel?: string
}) {
  const [paso, setPaso] = useState<Paso>("datos")
  const [info, setInfo] = useState<BinancePersonalInfo | null>(null)
  const [qr, setQr] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<BinancePersonalInfo>(`/billing/binance-info?plan_code=${plan.code}`)
      .then(async (data) => {
        setInfo(data)
        if (data.configured) setQr(await QRCode.toDataURL(data.qr_url, { width: 360, margin: 1 }))
      })
      .catch(() => setError("No se pudieron cargar los datos de Binance."))
  }, [plan.code])

  if (paso === "listo") {
    return (
      <>
        <ScreenHeader icon={faCircleCheck} tone="bg-emerald-500 text-white" title="Pago declarado" subtitle="Pendiente de verificación" />
        <p className="mt-4 text-center text-sm text-slate-500">
          Vamos a buscar tu orden en nuestro historial de Binance. Tu acceso Premium se activa en cuanto quede confirmada;
          mientras tanto puedes empezar a usar la app.
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

  if (paso === "declarar" && info) {
    return <DeclaracionForm plan={plan} info={info} onBack={() => setPaso("datos")} onSuccess={() => setPaso("listo")} />
  }

  const amount = info ? `${info.amount} ${info.asset}` : ""

  return (
    <>
      <ScreenHeader icon={faBitcoin} tone="bg-amber-400 text-slate-900" title="Binance Pay" subtitle="Pago con USDT" />

      {info?.configured && (
        <Steps
          items={[
            "Abre la app de Binance, entra en Pay y pulsa Enviar (o escanea este código).",
            <>
              Envía exactamente <strong>{amount}</strong>. Binance Pay entre usuarios no cobra comisión.
            </>,
            "Pulsa \"Ya hice el pago\" y escribe el ID de la orden que te da Binance para que la verifiquemos.",
          ]}
        />
      )}

      <div className="mt-4 space-y-2.5">
        {!info && !error && (
          <p className="py-6 text-center text-slate-300">
            <FontAwesomeIcon icon={faSpinner} spin className="text-xl" />
          </p>
        )}

        {info && !info.configured && (
          <p className="flex items-start gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <FontAwesomeIcon icon={faTriangleExclamation} className="mt-0.5" />
            Este método aún no está disponible. Usa otro por ahora.
          </p>
        )}

        {info?.configured && (
          <>
            <div className="flex flex-col items-center gap-2 py-1">
              {qr ? (
                <img src={qr} alt={`Código QR para pagar a ${info.nickname || "la academia"} con Binance Pay`} className="h-44 w-44 rounded-2xl border-4 border-amber-400" />
              ) : (
                <div className="flex h-44 w-44 items-center justify-center rounded-2xl border-4 border-slate-100 text-slate-300">
                  <FontAwesomeIcon icon={faSpinner} spin className="text-2xl" />
                </div>
              )}
              {/* En el móvil no se puede escanear la propia pantalla: el enlace
                  abre la app de Binance directamente en el pago. */}
              <a href={info.qr_url} target="_blank" rel="noreferrer" className="text-sm font-semibold text-amber-700 hover:underline">
                ¿Estás en el móvil? Abrir en la app de Binance
              </a>
            </div>
            <CopyField label="Monto a enviar" value={amount} copyValue={info.amount} />
            {info.nickname && <CopyField label="Usuario de Binance" value={info.nickname} />}
            {info.email && <CopyField label="Correo de Binance" value={info.email} />}
            {info.pay_id && <CopyField label="Pay ID" value={info.pay_id} />}
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
        className="mt-5 w-full rounded-2xl bg-amber-400 py-3.5 text-sm font-bold text-slate-900 transition active:scale-[0.98] hover:bg-amber-300 disabled:bg-slate-100 disabled:text-slate-400"
      >
        Ya hice el pago
      </button>

      <BackLink onBack={onBack} />
    </>
  )
}

function DeclaracionForm({ plan, info, onBack, onSuccess }: { plan: Plan; info: BinancePersonalInfo; onBack: () => void; onSuccess: () => void }) {
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    setSending(true)
    setError(null)
    try {
      await api.post("/billing/payments/binance", {
        plan_code: plan.code,
        order_id: String(data.get("orden")).trim(),
        payer_account: String(data.get("cuenta")).trim(),
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
      <ScreenHeader icon={faBitcoin} tone="bg-amber-400 text-slate-900" title="Confirma tu pago" subtitle={`${info.amount} ${info.asset} por Binance Pay`} />

      <form onSubmit={submit} className="mt-5 space-y-2.5">
        <Campo
          name="orden"
          label="ID de la orden"
          placeholder="Ej. 341234567890123456"
          hint="En Binance: Pay → Historial → toca el pago → ID de la orden."
          required
          minLength={4}
          maxLength={64}
        />
        <Campo name="cuenta" label="Tu usuario, correo o Pay ID de Binance" placeholder="Con la cuenta que pagaste" required minLength={2} maxLength={120} />
        <Campo name="fecha" label="Fecha del pago" type="date" defaultValue={todayIso()} max={todayIso()} required />

        {error && <p className="text-center text-sm text-amber-700">{error}</p>}

        <button
          type="submit"
          disabled={sending}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-amber-400 py-3.5 text-sm font-bold text-slate-900 transition active:scale-[0.98] hover:bg-amber-300 disabled:opacity-60"
        >
          {sending && <FontAwesomeIcon icon={faSpinner} spin />}
          Enviar para verificación
        </button>
      </form>

      <BackLink onBack={onBack} />
    </>
  )
}

function Campo({ name, label, hint, ...props }: { name: string; label: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</span>
      <input
        name={name}
        {...props}
        className="mt-1 w-full rounded-xl bg-white px-3.5 py-2.5 text-sm text-slate-800 outline-none ring-1 ring-slate-200 transition placeholder:text-slate-300 focus:ring-2 focus:ring-brand-500"
      />
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  )
}

/** Hoy en hora LOCAL del alumno ("YYYY-MM-DD"). toISOString() daría la
 * fecha en UTC, que a partir de las 8 de la noche en Venezuela ya es mañana. */
function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}
