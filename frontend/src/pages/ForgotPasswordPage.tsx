import { faArrowLeft, faArrowRight, faCircleExclamation, faEnvelopeCircleCheck, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState, type FormEvent } from "react"
import { Link, useLocation } from "react-router-dom"
import { api } from "../api/client"
import { ApiError } from "../api/types"
import AuthShell from "../components/auth/AuthShell"
import Field from "../components/auth/Field"

/** "¿Olvidaste tu contraseña?": pide el correo con el botón para cambiarla.
 * El backend responde lo mismo exista o no la cuenta, así que aquí tampoco
 * se distingue: siempre se muestra el "revisa tu correo". */
export default function ForgotPasswordPage() {
  // El login pasa el correo que ya había escrito, para no pedirlo dos veces.
  const location = useLocation()
  const [email, setEmail] = useState<string>((location.state as { email?: string } | null)?.email ?? "")
  const [sentMessage, setSentMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const { message } = await api.post<{ message: string }>("/auth/password/forgot", { email })
      setSentMessage(message)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Algo salió mal. Inténtalo de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      top={
        <Link to="/login" className="mb-6 flex items-center gap-2 text-sm text-slate-400 hover:text-slate-600">
          <FontAwesomeIcon icon={faArrowLeft} /> Volver a entrar
        </Link>
      }
    >
      {sentMessage ? (
        <>
          <FontAwesomeIcon icon={faEnvelopeCircleCheck} className="text-4xl text-brand-600" />
          <h1 className="mt-4 text-3xl font-extrabold">Revisa tu correo</h1>
          <p className="mt-2 text-slate-500">{sentMessage}</p>
          <p className="mt-4 text-sm text-slate-400">
            ¿No llegó en un par de minutos?{" "}
            <button
              type="button"
              onClick={() => setSentMessage(null)}
              className="font-semibold text-brand-600 hover:text-brand-500"
            >
              Pedirlo otra vez
            </button>
          </p>
        </>
      ) : (
        <>
          <h1 className="text-3xl font-extrabold">¿Olvidaste tu contraseña?</h1>
          <p className="mt-2 text-slate-500">
            Escribe el correo con el que te registraste y te enviamos un botón para elegir una nueva.
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Field label="Correo electrónico" type="email" value={email} onChange={setEmail} required autoComplete="email" />

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
              Enviarme el enlace
            </button>
          </form>
        </>
      )}
    </AuthShell>
  )
}
