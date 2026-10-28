import { faArrowLeft, faCheck, faCircleExclamation, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState, type FormEvent } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { ApiError } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import AuthShell from "../components/auth/AuthShell"
import Field from "../components/auth/Field"

/** A donde lleva el botón del correo "Cambia tu contraseña"
 * (/restablecer?token=…). Al guardar, el alumno queda con la sesión
 * iniciada y entra directo, sin volver a pasar por el login. */
export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token") ?? ""
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const { resetPassword } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (password !== confirm) {
      setError("Las dos contraseñas no coinciden.")
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      await resetPassword(token, password)
      navigate("/dashboard", { replace: true })
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
      <h1 className="text-3xl font-extrabold">Elige una contraseña nueva</h1>

      {!token ? (
        <p className="mt-2 text-slate-500">
          Este enlace está incompleto. Ábrelo directamente desde el correo, o{" "}
          <Link to="/recuperar" className="font-semibold text-brand-600 hover:text-brand-500">
            pide uno nuevo
          </Link>
          .
        </p>
      ) : (
        <>
          <p className="mt-2 text-slate-500">Mínimo 8 caracteres. Al guardarla entras directo a tu aula.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Field
              label="Contraseña nueva"
              type="password"
              value={password}
              onChange={setPassword}
              required
              minLength={8}
              autoComplete="new-password"
            />
            <Field
              label="Repítela"
              type="password"
              value={confirm}
              onChange={setConfirm}
              required
              minLength={8}
              autoComplete="new-password"
            />

            {error && (
              <div className="flex items-start gap-2 rounded-xl bg-red-50 px-3 py-2.5 text-sm text-red-600">
                <FontAwesomeIcon icon={faCircleExclamation} className="mt-0.5 shrink-0" />
                <span>
                  {error}{" "}
                  {error.includes("caducó") && (
                    <Link to="/recuperar" className="font-semibold underline">
                      Pedir otro enlace
                    </Link>
                  )}
                </span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-brand-600 px-4 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-brand-500 disabled:opacity-60"
            >
              {submitting ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faCheck} />}
              Guardar y entrar
            </button>
          </form>
        </>
      )}
    </AuthShell>
  )
}
