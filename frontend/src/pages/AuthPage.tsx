import { faArrowLeft, faArrowRight, faCheck, faCircleExclamation, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { api } from "../api/client"
import { ApiError, type BillingOptions } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import Logo from "../components/brand/Logo"
import PaymentMethodPicker from "../components/billing/PaymentMethodPicker"
import { planPeriod, planPrice } from "../components/billing/PaymentInfo"

export default function AuthPage() {
  const [searchParams] = useSearchParams()
  const [mode, setMode] = useState<"login" | "register">(searchParams.get("mode") === "register" ? "register" : "login")

  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // El registro tiene dos pasos: la cuenta y, justo después, cómo pagar.
  // El pago va DESPUÉS de crear la cuenta porque cada cobro queda a nombre
  // del alumno (el backend exige sesión para iniciar cualquier pago).
  const [step, setStep] = useState<"account" | "payment">("account")
  const [options, setOptions] = useState<BillingOptions | null>(null)

  // Se piden las opciones de pago al abrir el registro, no al terminar el
  // paso 1: así el paso 2 aparece al instante, sin un spinner de por medio.
  useEffect(() => {
    if (mode === "register" && !options) {
      api.get<BillingOptions>("/billing/options").then(setOptions).catch(() => {})
    }
  }, [mode, options])

  const { login, register } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === "login") {
        await login(email, password)
        navigate("/dashboard")
      } else {
        // El backend guarda un único `full_name` (ver models/user.py) — el
        // formulario separa Nombre/Apellido solo por UX, se unen al enviar.
        await register(email, password, `${firstName} ${lastName}`.trim())
        // Sin opciones de pago (API caída) no tiene sentido un paso 2 vacío.
        if (options) setStep("payment")
        else navigate("/dashboard")
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Algo salió mal. Inténtalo de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    // Pantalla partida en escritorio (marca a la izquierda, formulario a
    // la derecha), una sola columna en móvil — patrón web estándar para
    // login, en vez de una tarjeta pequeña flotando en medio de 1400px.
    <div className="grid min-h-screen grid-cols-1 bg-slate-50 text-slate-900 lg:grid-cols-2">
      {/* Fondo marino a violeta, el mismo del manual de marca, con el logo
          en su versión para fondo oscuro. */}
      <aside className="hidden flex-col justify-between bg-gradient-to-br from-ink-950 via-ink-900 to-brand-900 p-12 text-white lg:flex">
        <Logo tone="dark" size={44} textClassName="text-2xl" />
        <div>
          <h2 className="text-4xl font-extrabold leading-tight">
            De A1 a C2, con un tutor que entiende cómo aprende un hispanohablante.
          </h2>
          <p className="mt-4 max-w-md text-brand-100">
            Tu progreso se mide en capacidades reales del Marco Común Europeo, demostradas varias veces — no en
            lecciones vistas.
          </p>
        </div>
        <p className="text-sm text-brand-200">Espikin © 2026</p>
      </aside>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-6 flex items-center gap-2 text-sm text-slate-400 hover:text-slate-600">
            <FontAwesomeIcon icon={faArrowLeft} /> Volver al inicio
          </Link>

          <div className="lg:hidden">
            <Logo size={32} className="mb-5" />
          </div>

          {step === "payment" && options ? (
            <PaymentStep options={options} firstName={firstName} onFinish={() => navigate("/dashboard")} />
          ) : (
            <>
              {mode === "register" && <Stepper current={1} />}

              <h1 className="text-3xl font-extrabold">{mode === "login" ? "¡Qué bueno verte!" : "Únete a la academia"}</h1>
              <p className="mt-2 text-slate-500">
                {mode === "login" ? "Ingresa para continuar aprendiendo." : "Inicia tu camino hoy mismo."}
              </p>

              <div className="mt-6 grid grid-cols-2 rounded-full bg-slate-100 p-1 text-sm font-semibold">
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className={`rounded-full py-2.5 transition ${mode === "login" ? "bg-white text-brand-600 shadow-sm" : "text-slate-400"}`}
                >
                  Entrar
                </button>
                <button
                  type="button"
                  onClick={() => setMode("register")}
                  className={`rounded-full py-2.5 transition ${mode === "register" ? "bg-white text-brand-600 shadow-sm" : "text-slate-400"}`}
                >
                  Registrarse
                </button>
              </div>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                {mode === "register" && (
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Nombre" value={firstName} onChange={setFirstName} required />
                    <Field label="Apellido" value={lastName} onChange={setLastName} required />
                  </div>
                )}

                <Field label="Correo electrónico" type="email" value={email} onChange={setEmail} required />
                <Field label="Contraseña" type="password" value={password} onChange={setPassword} required minLength={8} />

                {error && (
                  <div className="flex items-start gap-2 rounded-xl bg-red-50 px-3 py-2.5 text-sm text-red-600">
                    <FontAwesomeIcon icon={faCircleExclamation} className="mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="flex w-full items-center justify-center gap-2 rounded-full bg-brand-600 px-4 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-brand-500 disabled:opacity-60"
                >
                  {submitting ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faArrowRight} />}
                  {mode === "login" ? "Entrar ahora" : "Crear cuenta y elegir pago"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  minLength,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  required?: boolean
  minLength?: number
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</span>
      <input
        type={type}
        required={required}
        minLength={minLength}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-900 outline-none ring-brand-500 focus:ring-2"
      />
    </label>
  )
}

/** "1 Tu cuenta → 2 Tu suscripción": que el alumno sepa desde el primer
 * campo que después viene el pago, y cuánto le falta. */
function Stepper({ current }: { current: 1 | 2 }) {
  const steps = ["Tu cuenta", "Tu suscripción"]
  return (
    <ol className="mb-5 flex items-center gap-2 text-xs font-semibold" aria-label="Pasos del registro">
      {steps.map((label, i) => {
        const n = i + 1
        const done = n < current
        const active = n === current
        return (
          <li key={label} className="flex items-center gap-2" aria-current={active ? "step" : undefined}>
            {i > 0 && <span aria-hidden className={`h-px w-6 ${done || active ? "bg-brand-300" : "bg-slate-200"}`} />}
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full ${
                done ? "bg-brand-600 text-white" : active ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? <FontAwesomeIcon icon={faCheck} className="text-[10px]" /> : n}
            </span>
            <span className={active ? "text-slate-900" : "text-slate-400"}>{label}</span>
          </li>
        )
      })}
    </ol>
  )
}

/** Paso 2: el plan en una línea y los métodos de pago, cada uno con su
 * información dentro. "Pagar después" siempre a mano: la cuenta ya existe
 * y el alumno puede suscribirse cuando quiera desde su perfil. */
function PaymentStep({ options, firstName, onFinish }: { options: BillingOptions; firstName: string; onFinish: () => void }) {
  const plan = options.plan
  return (
    <>
      <Stepper current={2} />
      <h1 className="text-3xl font-extrabold">{firstName ? `¡Listo, ${firstName}!` : "¡Cuenta creada!"}</h1>
      <p className="mt-2 text-slate-500">Ahora elige cómo pagar tu suscripción. Tardas un minuto.</p>

      <div className="mt-5 flex items-center justify-between gap-4 rounded-2xl border border-brand-100 bg-white p-4">
        <div className="min-w-0">
          <p className="font-bold text-slate-900">{plan.name}</p>
          <p className="text-xs text-slate-500">Los 6 niveles, tutor ilimitado 24/7 y certificación · cancela cuando quieras</p>
        </div>
        <p className="shrink-0 text-right">
          <span className="text-2xl font-extrabold text-slate-900">{planPrice(plan)}</span>
          <span className="block text-xs text-slate-500">USD / {planPeriod(plan)}</span>
        </p>
      </div>

      <div className="mt-5">
        <PaymentMethodPicker options={options} onDone={onFinish} doneLabel="Ir a mi aula" />
      </div>

      <button
        type="button"
        onClick={onFinish}
        className="mt-5 w-full rounded-full py-3 text-sm font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
      >
        Prefiero pagar después
      </button>
    </>
  )
}

