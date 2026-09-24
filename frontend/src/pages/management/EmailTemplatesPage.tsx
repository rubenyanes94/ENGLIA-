import {
  faCircleCheck,
  faCircleInfo,
  faEnvelope,
  faPaperPlane,
  faPenToSquare,
  faFileLines,
  faPlus,
  faSpinner,
  faTrash,
  faTriangleExclamation,
  faUsers,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../../api/client"
import type { Audience, EmailTemplate, Starter, TemplateDraft, TemplatePreview } from "../../api/management"
import { ApiError } from "../../api/types"
import { dateAndTime, int } from "../../components/charts/format"
import PageShell from "../../components/management/PageShell"
import { useManagementData } from "../../components/management/useManagementData"

const VACIA: TemplateDraft = {
  name: "",
  subject: "",
  preheader: "",
  eyebrow: "Novedad",
  title: "",
  body: "",
  button_label: "",
  button_url: "",
}

type Editando = TemplateDraft & { id?: string }

/** Panel de gerencia → Correos → Escribir. Se escribe el mensaje, se ve
 * al lado tal como le va a llegar al alumno, se prueba en la bandeja
 * propia y solo entonces se envía a un grupo.
 *
 * Ese orden es el diseño entero: un correo a doscientos clientes no se
 * puede recoger, así que la prueba está antes que el envío y el botón de
 * enviar obliga a leer a cuánta gente va. */
export default function EmailTemplatesPage() {
  const templates = useManagementData<EmailTemplate[]>("/management/email-templates")
  const [editando, setEditando] = useState<Editando | null>(null)
  // Al escribir uno nuevo se elige primero de entre los ya escritos: una
  // página en blanco es lo que hace que nadie escriba nunca.
  const [eligiendo, setEligiendo] = useState(false)
  // El grupo que sugiere el mensaje elegido, para dejarlo marcado abajo.
  // Se equivoca uno justo ahí: mandarle "renueva antes de que venza" a
  // quien ya renovó.
  const [sugerido, setSugerido] = useState<string | null>(null)

  function nuevo(draft: TemplateDraft, audiencia: string | null) {
    setSugerido(audiencia)
    setEditando({ ...draft })
    setEligiendo(false)
  }

  return (
    <PageShell
      title="Escribir a los clientes"
      question="Mensajes que escribes tú y le llegan a un grupo de clientes con el estilo de Espikin."
      loading={templates.loading}
      error={templates.error}
      hasData={templates.data != null}
      filters={
        <>
          <Link to="/gerencia/correos" className="text-sm font-medium text-slate-500 hover:text-slate-900">
            Ver enviados
          </Link>
          {!editando && !eligiendo && (
            <button
              type="button"
              onClick={() => setEligiendo(true)}
              className="flex items-center gap-2 rounded-full bg-ink-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ink-800"
            >
              <FontAwesomeIcon icon={faPlus} />
              Mensaje nuevo
            </button>
          )}
        </>
      }
    >
      {editando ? (
        <Editor
          inicial={editando}
          sugerido={sugerido}
          onClose={() => setEditando(null)}
          onSaved={(t) => {
            templates.reload()
            setEditando({ ...t })
          }}
          onDeleted={() => {
            templates.reload()
            setEditando(null)
          }}
        />
      ) : eligiendo ? (
        <Elegir onElegir={nuevo} onCancelar={() => setEligiendo(false)} />
      ) : (
        <Lista
          templates={templates.data ?? []}
          onNueva={() => setEligiendo(true)}
          onAbrir={(t) => {
            setSugerido(null)
            setEditando({ ...t })
          }}
        />
      )}
    </PageShell>
  )
}

// ---------------------------------------------------------------------------

function Lista({ templates, onNueva, onAbrir }: { templates: EmailTemplate[]; onNueva: () => void; onAbrir: (t: EmailTemplate) => void }) {
  if (templates.length === 0) {
    return (
      <section className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
        <FontAwesomeIcon icon={faEnvelope} className="text-3xl text-slate-200" />
        <h2 className="mt-4 text-lg font-bold text-slate-900">Todavía no hay ningún mensaje escrito</h2>
        <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
          Aquí escribes promociones, avisos de clases nuevas o lo que quieras contarle a tus clientes. Se guarda y lo puedes reutilizar.
        </p>
        <button
          type="button"
          onClick={onNueva}
          className="mt-5 rounded-full bg-ink-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-ink-800"
        >
          Escribir el primero
        </button>
      </section>
    )
  }

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {templates.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => onAbrir(t)}
          className="flex flex-col rounded-3xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-brand-300 hover:shadow"
        >
          <p className="font-bold text-slate-900">{t.name}</p>
          <p className="mt-1 line-clamp-2 text-sm text-slate-500">{t.subject}</p>
          <p className="mt-4 flex items-center gap-2 text-xs text-slate-400">
            <FontAwesomeIcon icon={faPenToSquare} />
            {t.times_sent > 0 ? `Enviado ${int(t.times_sent)} ${t.times_sent === 1 ? "vez" : "veces"}` : "Sin enviar"}
            {t.last_sent_at && ` · ${dateAndTime(t.last_sent_at)}`}
          </p>
        </button>
      ))}
    </section>
  )
}

// ---------------------------------------------------------------------------

/** Los mensajes ya escritos, para no empezar en blanco.
 *
 * Es la pantalla que decide si esto se usa o no. Escribir un correo de
 * promoción desde cero un martes por la tarde no lo hace nadie; elegir
 * "Recuperar a quien se fue" y cambiarle dos frases, sí. Lo que se elige
 * es un borrador: a partir de ahí es un mensaje del usuario y estos
 * textos no vuelven a tocarse. */
function Elegir({ onElegir, onCancelar }: { onElegir: (draft: TemplateDraft, audiencia: string | null) => void; onCancelar: () => void }) {
  const starters = useManagementData<Starter[]>("/management/email-starters")
  // Solo para enseñar "Pensado para: Se les venció" en cada tarjeta. Se
  // piden los grupos en vez de repetir aquí sus nombres, que se quedarían
  // viejos el día que cambien en el backend.
  const audiences = useManagementData<Audience[]>("/management/email-audiences")
  const nombreGrupo = (key: string) => audiences.data?.find((a) => a.key === key)?.label

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900">¿Qué quieres decirles?</h2>
          <p className="text-sm text-slate-500">Elige uno y cámbiale lo que quieras. Todos están escritos y listos para enviar.</p>
        </div>
        <button type="button" onClick={onCancelar} className="text-sm font-medium text-slate-500 hover:text-slate-900">
          Cancelar
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(starters.data ?? []).map((st) => {
          const { key, label, description, audience, ...draft } = st
          const grupo = nombreGrupo(audience)
          return (
            <button
              key={key}
              type="button"
              onClick={() => onElegir(draft, audience)}
              className="flex h-full flex-col rounded-3xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-brand-300 hover:shadow"
            >
              <p className="font-bold text-slate-900">{label}</p>
              <p className="mt-1 flex-1 text-sm text-slate-500">{description}</p>
              <p className="mt-4 rounded-2xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
                <span className="text-slate-400">Asunto: </span>
                {st.subject}
              </p>
              {grupo && (
                <p className="mt-2 text-xs font-semibold text-brand-700">
                  Pensado para: {grupo}
                </p>
              )}
            </button>
          )
        })}

        <button
          type="button"
          onClick={() => onElegir(VACIA, null)}
          className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 rounded-3xl border border-dashed border-slate-300 p-5 text-slate-400 transition hover:border-brand-300 hover:text-brand-700"
        >
          <FontAwesomeIcon icon={faFileLines} className="text-2xl" />
          <span className="text-sm font-semibold">Empezar en blanco</span>
        </button>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------

function Editor({
  inicial,
  sugerido,
  onClose,
  onSaved,
  onDeleted,
}: {
  inicial: Editando
  sugerido: string | null
  onClose: () => void
  onSaved: (t: EmailTemplate) => void
  onDeleted: () => void
}) {
  const [draft, setDraft] = useState<Editando>(inicial)
  const [preview, setPreview] = useState<TemplatePreview | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const completo = draft.name.trim().length > 1 && draft.subject.trim().length > 1 && draft.title.trim().length > 1 && draft.body.trim().length > 1
  const guardado = Boolean(draft.id)

  useEffect(() => setDraft(inicial), [inicial.id])

  // La vista previa se pide al backend y no se pinta en el navegador: así
  // lo que se ve es EXACTAMENTE el HTML que va a salir, armado por el
  // mismo código que lo envía. Con retardo, para no pedir una por tecla.
  useEffect(() => {
    if (!completo) return
    const t = setTimeout(() => {
      api
        .post<TemplatePreview>("/management/email-templates/preview", cuerpo(draft))
        .then(setPreview)
        .catch(() => setPreview(null))
    }, 400)
    return () => clearTimeout(t)
  }, [draft.subject, draft.preheader, draft.eyebrow, draft.title, draft.body, draft.button_label, draft.button_url, completo])

  function set<K extends keyof Editando>(key: K, value: Editando[K]) {
    setDraft((d) => ({ ...d, [key]: value }))
    setAviso(null)
  }

  async function guardar(): Promise<EmailTemplate | null> {
    setGuardando(true)
    setError(null)
    try {
      const saved = draft.id
        ? await api.patch<EmailTemplate>(`/management/email-templates/${draft.id}`, cuerpo(draft))
        : await api.post<EmailTemplate>("/management/email-templates", cuerpo(draft))
      onSaved(saved)
      setAviso("Mensaje guardado.")
      return saved
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.")
      return null
    } finally {
      setGuardando(false)
    }
  }

  async function prueba() {
    const saved = draft.id ? { id: draft.id } : await guardar()
    if (!saved) return
    setEnviando(true)
    setError(null)
    try {
      const r = await api.post<{ sent_to: string }>(`/management/email-templates/${saved.id}/test`, {})
      setAviso(`Prueba enviada a ${r.sent_to}. Míralo en tu bandeja antes de mandárselo a nadie.`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar la prueba.")
    } finally {
      setEnviando(false)
    }
  }

  async function borrar() {
    if (!draft.id) return onClose()
    setGuardando(true)
    try {
      await api.delete(`/management/email-templates/${draft.id}`)
      onDeleted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar.")
      setGuardando(false)
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,520px)]">
      {/* Formulario */}
      <section className="space-y-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <Campo label="Nombre interno" hint="Para reconocerlo en la lista. No sale en el correo.">
          <input {...input} value={draft.name} onChange={(e) => set("name", e.target.value)} placeholder="Promo de Navidad" maxLength={120} />
        </Campo>

        <Campo label="Asunto" hint="Lo primero que se lee en la bandeja. Puedes usar {nombre}.">
          <input {...input} value={draft.subject} onChange={(e) => set("subject", e.target.value)} placeholder="Una semana gratis, {nombre}" maxLength={200} />
        </Campo>

        <Campo label="Adelanto" hint="La línea gris que se lee junto al asunto, antes de abrirlo.">
          <input {...input} value={draft.preheader} onChange={(e) => set("preheader", e.target.value)} placeholder="Solo hasta el domingo" maxLength={200} />
        </Campo>

        <div className="grid gap-5 sm:grid-cols-[150px_minmax(0,1fr)]">
          <Campo label="Etiqueta" hint="Arriba, en violeta.">
            <input {...input} value={draft.eyebrow} onChange={(e) => set("eyebrow", e.target.value)} placeholder="Promoción" maxLength={40} />
          </Campo>
          <Campo label="Título" hint="La frase grande. {nombre} y *en violeta*.">
            <input {...input} value={draft.title} onChange={(e) => set("title", e.target.value)} placeholder="Te regalamos *una semana*, {nombre}" maxLength={200} />
          </Campo>
        </div>

        <Campo label="Mensaje" hint="Una línea en blanco separa párrafos. Rodea con *asteriscos* lo que quieras en violeta.">
          <textarea
            {...input}
            rows={7}
            value={draft.body}
            onChange={(e) => set("body", e.target.value)}
            placeholder={"Queremos que vuelvas a practicar.\n\nSi renuevas antes del domingo, te sumamos siete días sin costo."}
            maxLength={4000}
          />
        </Campo>

        <div className="grid gap-5 sm:grid-cols-2">
          <Campo label="Texto del botón" hint="Vacío = sin botón.">
            <input {...input} value={draft.button_label ?? ""} onChange={(e) => set("button_label", e.target.value)} placeholder="Quiero mi semana" maxLength={60} />
          </Campo>
          <Campo label="A dónde lleva" hint="Vacío = al inicio de la app.">
            <input {...input} value={draft.button_url ?? ""} onChange={(e) => set("button_url", e.target.value)} placeholder="https://…" maxLength={500} />
          </Campo>
        </div>

        {error && (
          <p className="flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <FontAwesomeIcon icon={faTriangleExclamation} />
            {error}
          </p>
        )}
        {aviso && (
          <p className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <FontAwesomeIcon icon={faCircleCheck} />
            {aviso}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
          <button
            type="button"
            onClick={guardar}
            disabled={!completo || guardando}
            className="rounded-full bg-ink-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-ink-800 disabled:opacity-40"
          >
            {guardando ? "Guardando…" : "Guardar"}
          </button>
          <button
            type="button"
            onClick={prueba}
            disabled={!completo || enviando}
            className="flex items-center gap-2 rounded-full border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40"
          >
            <FontAwesomeIcon icon={enviando ? faSpinner : faEnvelope} spin={enviando} />
            Enviarme una prueba
          </button>
          <button type="button" onClick={onClose} className="text-sm font-medium text-slate-500 hover:text-slate-900">
            Cerrar
          </button>
          {draft.id && (
            <button
              type="button"
              onClick={borrar}
              className="ml-auto flex items-center gap-2 text-sm font-medium text-slate-400 transition hover:text-rose-600"
            >
              <FontAwesomeIcon icon={faTrash} />
              Borrar
            </button>
          )}
        </div>
      </section>

      {/* Vista previa y envío */}
      <div className="space-y-5">
        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-5 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Así le llega</p>
            <p className="mt-0.5 truncate text-sm font-semibold text-slate-800">{preview?.subject || draft.subject || "—"}</p>
          </div>
          {preview ? (
            <iframe title="Vista previa del correo" srcDoc={preview.html} className="h-[560px] w-full border-0 bg-white" />
          ) : (
            <p className="px-5 py-20 text-center text-sm text-slate-400">
              {completo ? "Preparando la vista previa…" : "Rellena nombre, asunto, título y mensaje para verlo."}
            </p>
          )}
        </section>

        <Enviar templateId={draft.id} guardado={guardado} sugerido={sugerido} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------

function Enviar({ templateId, guardado, sugerido }: { templateId?: string; guardado: boolean; sugerido: string | null }) {
  const audiences = useManagementData<Audience[]>("/management/email-audiences")
  const [grupo, setGrupo] = useState<string | null>(sugerido)
  const [confirmando, setConfirmando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const elegido = audiences.data?.find((a) => a.key === grupo)

  async function enviar() {
    if (!templateId || !elegido) return
    setEnviando(true)
    setError(null)
    try {
      await api.post("/management/email-campaigns", { template_id: templateId, audience: elegido.key })
      setResultado(`Enviando a ${elegido.customers} ${elegido.customers === 1 ? "cliente" : "clientes"}. Puedes seguir el avance en "Enviados".`)
      setConfirmando(false)
      setGrupo(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo lanzar el envío.")
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="flex items-center gap-2 font-bold text-slate-900">
        <FontAwesomeIcon icon={faUsers} className="text-slate-400" />
        Enviar a un grupo
      </h2>

      {!guardado ? (
        <p className="mt-3 text-sm text-slate-500">Guarda el mensaje para poder enviarlo.</p>
      ) : (
        <>
          <div className="mt-3 space-y-2" role="radiogroup" aria-label="Grupo de clientes">
            {(audiences.data ?? []).map((a) => (
              <button
                key={a.key}
                type="button"
                role="radio"
                aria-checked={grupo === a.key}
                onClick={() => {
                  setGrupo(a.key)
                  setConfirmando(false)
                  setResultado(null)
                }}
                className={`flex w-full items-start justify-between gap-3 rounded-2xl border p-3 text-left transition ${
                  grupo === a.key ? "border-brand-400 bg-brand-50" : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-slate-800">{a.label}</span>
                  <span className="block text-xs text-slate-500">{a.description}</span>
                </span>
                <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-xs font-bold tabular-nums text-slate-700">{int(a.customers)}</span>
              </button>
            ))}
          </div>

          <p className="mt-3 flex items-start gap-2 text-xs text-slate-400">
            <FontAwesomeIcon icon={faCircleInfo} className="mt-0.5" />
            Ese número es cuánta gente hay en el grupo. Recibirán menos: quien se dio de baja de los recordatorios queda fuera.
          </p>

          {error && <p className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
          {resultado && <p className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{resultado}</p>}

          {elegido &&
            (confirmando ? (
              /* Confirmación en el sitio: el segundo clic dice el número en
                 voz alta, porque un envío no se puede deshacer. */
              <div className="mt-4 rounded-2xl bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-900">
                  Se enviará a {int(elegido.customers)} {elegido.customers === 1 ? "cliente" : "clientes"} de «{elegido.label}». No se puede deshacer.
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={enviar}
                    disabled={enviando}
                    className="flex items-center gap-2 rounded-full bg-ink-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ink-800 disabled:opacity-40"
                  >
                    <FontAwesomeIcon icon={enviando ? faSpinner : faPaperPlane} spin={enviando} />
                    Sí, enviar ahora
                  </button>
                  <button type="button" onClick={() => setConfirmando(false)} className="rounded-full px-4 py-2 text-sm font-medium text-slate-600 hover:bg-white">
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmando(true)}
                disabled={elegido.customers === 0}
                className="mt-4 w-full rounded-full bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-40"
              >
                {elegido.customers === 0 ? "No hay nadie en ese grupo" : `Enviar a ${int(elegido.customers)} ${elegido.customers === 1 ? "cliente" : "clientes"}`}
              </button>
            ))}
        </>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------

const input = {
  className:
    "w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none transition focus:border-brand-300 focus:ring-2 focus:ring-brand-100",
}

function Campo({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-slate-800">{label}</span>
      {hint && <span className="mt-0.5 block text-xs text-slate-400">{hint}</span>}
      <span className="mt-1.5 block">{children}</span>
    </label>
  )
}

function cuerpo(draft: Editando): TemplateDraft {
  return {
    name: draft.name.trim(),
    subject: draft.subject.trim(),
    preheader: (draft.preheader ?? "").trim(),
    eyebrow: (draft.eyebrow || "Espikin").trim(),
    title: draft.title.trim(),
    body: draft.body.trim(),
    button_label: (draft.button_label ?? "").trim() || null,
    button_url: (draft.button_url ?? "").trim() || null,
  }
}
