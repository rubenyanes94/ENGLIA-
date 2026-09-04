import { faArrowLeft, faArrowRight, faCircleExclamation, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState, type FormEvent } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { ApiError } from "../api/types"
import { useAuth } from "../auth/AuthContext"

export default function AuthPage() {
  const [searchParams] = useSearchParams()
  const [mode, setMode] = useState<"login" | "register">(searchParams.get("mode") === "register" ? "register" : "login")

  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const { login, register } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === "login") {
        await login(email, password)
      } else {
        // El backend guarda un único `full_name` (ver models/user.py) — el
        // formulario separa Nombre/Apellido solo por UX, se unen al enviar.
        await register(email, password, `${firstName} ${lastName}`.trim())
      }
      navigate("/dashboard")
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
      <aside className="hidden flex-col justify-between bg-gradient-to-br from-blue-600 to-blue-500 p-12 text-white lg:flex">
        <span className="flex items-center gap-2 font-bold">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20 text-sm">E</span>
          Espikin
        </span>
        <div>
          <h2 className="text-4xl font-extrabold leading-tight">
            De A1 a C2, con un tutor que entiende cómo aprende un hispanohablante.
          </h2>
          <p className="mt-4 max-w-md text-blue-100">
            Tu progreso se mide en capacidades reales del Marco Común Europeo, demostradas varias veces — no en
            lecciones vistas.
          </p>
        </div>
        <p className="text-sm text-blue-200">Espikin © 2026</p>
      </aside>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-6 flex items-center gap-2 text-sm text-slate-400 hover:text-slate-600">
            <FontAwesomeIcon icon={faArrowLeft} /> Volver al inicio
          </Link>

          <div className="lg:hidden">
            <span className="mb-4 flex items-center gap-2 text-sm font-extrabold text-slate-900">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-blue-500 text-[11px] font-black text-white">
                E
              </span>
              Espikin
            </span>
          </div>

          <h1 className="text-3xl font-extrabold">{mode === "login" ? "¡Qué bueno verte!" : "Únete a la academia"}</h1>
          <p className="mt-2 text-slate-500">
            {mode === "login" ? "Ingresa para continuar aprendiendo." : "Inicia tu camino hoy mismo."}
          </p>

          <div className="mt-6 grid grid-cols-2 rounded-full bg-slate-100 p-1 text-sm font-semibold">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`rounded-full py-2.5 transition ${mode === "login" ? "bg-white text-blue-600 shadow-sm" : "text-slate-400"}`}
            >
              Entrar
            </button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={`rounded-full py-2.5 transition ${mode === "register" ? "bg-white text-blue-600 shadow-sm" : "text-slate-400"}`}
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
              className="flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-4 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500 disabled:opacity-60"
            >
              {submitting ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faArrowRight} />}
              {mode === "login" ? "Entrar ahora" : "Crear cuenta"}
            </button>
          </form>
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
        className="w-full rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-900 outline-none ring-blue-500 focus:ring-2"
      />
    </label>
  )
}
