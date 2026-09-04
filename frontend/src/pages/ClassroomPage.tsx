import {
  faArrowRight,
  faBolt,
  faCircleCheck,
  faClock,
  faFlagCheckered,
  faLock,
  faPlay,
  faRotateRight,
  faSpinner,
  faTrophy,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { CertificationProgress, ModuleProgress, Progress } from "../api/types"
import { ApiError } from "../api/types"
import AppFooter from "../components/AppFooter"

const LEVEL_CODE = "A1" // único nivel con currículo sembrado hoy

/** Estilo y copy por estado. En un solo sitio para que la tarjeta, el
 * botón y el borde no puedan contradecirse entre ellos. */
const STATUS_META: Record<
  ModuleProgress["status"],
  { label: string; badge: string; cta: string; icon: typeof faPlay; ring: string }
> = {
  completed: {
    label: "Completado",
    badge: "bg-emerald-100 text-emerald-700",
    cta: "Repasar",
    icon: faRotateRight,
    ring: "border-emerald-200 bg-emerald-50/40",
  },
  in_progress: {
    label: "En progreso",
    badge: "bg-amber-100 text-amber-700",
    cta: "Continuar",
    icon: faBolt,
    ring: "border-amber-300 bg-amber-50/60 ring-2 ring-amber-200",
  },
  available: {
    label: "Disponible",
    badge: "bg-blue-100 text-blue-700",
    cta: "Empezar",
    icon: faPlay,
    ring: "border-blue-200 bg-white ring-2 ring-blue-100",
  },
  locked: {
    label: "Bloqueado",
    badge: "bg-slate-100 text-slate-400",
    cta: "Bloqueado",
    icon: faLock,
    ring: "border-slate-200 bg-slate-50",
  },
}

export default function ClassroomPage() {
  const [progress, setProgress] = useState<CertificationProgress | null>(null)
  const [masteryByModule, setMasteryByModule] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.get<CertificationProgress>(`/levels/${LEVEL_CODE}/certification-progress`),
      // El mastery por módulo NO viene en certification-progress (que solo
      // trae el estado), sino en el progreso del alumno — se cruzan por
      // module_id para poder pintar una barra real en cada tarjeta.
      api.get<Progress>("/users/me/progress").catch(() => null),
    ])
      .then(([progressData, userProgress]) => {
        setProgress(progressData)
        if (userProgress) {
          setMasteryByModule(
            Object.fromEntries(userProgress.modules.map((m) => [m.module_id, m.mastery_score])),
          )
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar el classroom."))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Cargando tu classroom...
      </div>
    )
  }

  if (!progress) {
    return <div className="text-red-500">{error ?? "No se pudo cargar el classroom."}</div>
  }

  const modules = progress.modules
  const completedCount = modules.filter((m) => m.status === "completed").length
  const current = modules.find((m) => m.status === "in_progress") ?? modules.find((m) => m.status === "available")
  const remainingHours = modules
    .filter((m) => m.status !== "completed")
    .reduce((sum, m) => sum + m.estimated_hours, 0)

  return (
    <div>
      <div className="space-y-8">
        {/* ---- Cabecera: progreso del nivel ---- */}
        <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900 to-blue-900 p-6 text-white shadow-xl sm:p-8">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-blue-500/25 blur-3xl"
          />
          <div className="relative">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Tu ruta de certificación</p>
                <h1 className="mt-1.5 text-3xl font-extrabold tracking-tight sm:text-4xl">Classroom {progress.level_code}</h1>
                <p className="mt-2 text-slate-300">
                  {completedCount} de {modules.length} módulos · {progress.hours_completed}h de{" "}
                  {progress.target_hours_min}–{progress.target_hours_max}h
                </p>
              </div>
              <div className="text-right">
                <p className="text-4xl font-extrabold sm:text-5xl">{progress.percentage}%</p>
                <p className="text-xs text-slate-400">certificado</p>
              </div>
            </div>

            <div className="mt-6 h-2.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-400 to-emerald-400 transition-all duration-700"
                style={{ width: `${Math.max(progress.percentage, 1.5)}%` }}
              />
            </div>

            <div className="mt-6 grid grid-cols-3 gap-3 border-t border-white/10 pt-5 text-center">
              <MiniStat icon={faCircleCheck} value={`${completedCount}/${modules.length}`} label="Módulos" />
              <MiniStat icon={faClock} value={`${remainingHours}h`} label="Te faltan" />
              <MiniStat icon={faTrophy} value={progress.level_code} label="Certificación" />
            </div>
          </div>
        </header>

        {/* ---- Siguiente paso, destacado ---- */}
        {current && (
          <Link
            to={`/modules/${current.id}`}
            className="group flex flex-col gap-4 rounded-3xl border-2 border-blue-600 bg-white p-5 shadow-lg shadow-blue-600/10 transition hover:shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-6"
          >
            <div className="flex items-center gap-4">
              <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-blue-500 text-xl font-black text-white shadow-md">
                {current.order}
              </span>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-blue-600">
                  {current.status === "in_progress" ? "Continúa donde lo dejaste" : "Tu siguiente paso"}
                </p>
                <h2 className="mt-0.5 text-xl font-extrabold tracking-tight text-slate-900">{current.title}</h2>
                <p className="text-sm text-slate-500">{current.title_es}</p>
              </div>
            </div>
            <span className="flex shrink-0 items-center justify-center gap-2 rounded-full bg-blue-600 px-6 py-3.5 font-bold text-white transition group-hover:bg-blue-500">
              {STATUS_META[current.status].cta}
              <FontAwesomeIcon icon={faArrowRight} className="text-xs transition group-hover:translate-x-1" />
            </span>
          </Link>
        )}

        {/* ---- La ruta completa ---- */}
        <section>
          <h2 className="mb-4 text-lg font-bold tracking-tight text-slate-900">Los {modules.length} módulos de {progress.level_code}</h2>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {modules.map((module, index) => {
              const meta = STATUS_META[module.status]
              const mastery = Math.round((masteryByModule[module.id] ?? 0) * 100)
              const clickable = module.status !== "locked"
              const blockedBy = index > 0 ? modules[index - 1] : undefined

              const card = (
                <article
                  className={`flex h-full flex-col rounded-3xl border p-5 shadow-sm transition ${meta.ring} ${
                    clickable ? "hover:-translate-y-1 hover:shadow-lg" : "opacity-80"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-base font-black ${
                        module.status === "completed"
                          ? "bg-emerald-500 text-white"
                          : module.status === "locked"
                            ? "bg-slate-200 text-slate-400"
                            : "bg-gradient-to-br from-blue-600 to-blue-500 text-white"
                      }`}
                    >
                      {module.status === "completed" ? <FontAwesomeIcon icon={faCircleCheck} /> : module.order}
                    </span>
                    <span
                      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${meta.badge}`}
                    >
                      <FontAwesomeIcon icon={meta.icon} spin={module.status === "in_progress"} />
                      {meta.label}
                    </span>
                  </div>

                  <h3 className="mt-4 text-lg font-extrabold tracking-tight text-slate-900">{module.title}</h3>
                  <p className="text-sm text-slate-500">{module.title_es}</p>

                  {/* Objetivos: lo que el alumno GANA, no metadatos sueltos */}
                  {module.communicative_objectives.length > 0 && module.status !== "locked" && (
                    <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
                      <FontAwesomeIcon icon={faFlagCheckered} className="mt-0.5 shrink-0 text-slate-300" />
                      {module.communicative_objectives[0]}
                    </p>
                  )}

                  {/* Barra de dominio real (mastery del enrollment) */}
                  {module.status !== "locked" && module.status !== "available" && (
                    <div className="mt-4">
                      <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                        <span>Dominio</span>
                        <span>{mastery}%</span>
                      </div>
                      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            module.status === "completed" ? "bg-emerald-500" : "bg-amber-500"
                          }`}
                          style={{ width: `${Math.max(mastery, 2)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="mt-auto pt-4">
                    <div className="flex items-center gap-3 text-[11px] font-medium text-slate-400">
                      <span className="flex items-center gap-1">
                        <FontAwesomeIcon icon={faClock} /> {module.estimated_hours}h
                      </span>
                      <span>·</span>
                      <span>{module.descriptors.length} capacidades</span>
                    </div>

                    {module.status === "locked" ? (
                      <p className="mt-3 flex items-start gap-2 rounded-2xl bg-slate-100 px-3 py-2.5 text-xs text-slate-500">
                        <FontAwesomeIcon icon={faLock} className="mt-0.5 shrink-0" />
                        {blockedBy ? `Completa “${blockedBy.title}” para desbloquear` : "Aún no disponible"}
                      </p>
                    ) : (
                      <span
                        className={`mt-3 flex items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-bold transition ${
                          module.status === "completed"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-900 text-white"
                        }`}
                      >
                        <FontAwesomeIcon icon={meta.icon} className="text-xs" />
                        {meta.cta}
                      </span>
                    )}
                  </div>
                </article>
              )

              return clickable ? (
                <Link key={module.id} to={`/modules/${module.id}`} className="h-full">
                  {card}
                </Link>
              ) : (
                <div key={module.id} className="h-full">
                  {card}
                </div>
              )
            })}
          </div>
        </section>

        {/* ---- Meta final ---- */}
        <div className="flex items-center gap-4 rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-6">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-600">
            <FontAwesomeIcon icon={faTrophy} />
          </span>
          <div>
            <p className="font-bold text-slate-900">Certificación {progress.level_code}</p>
            <p className="mt-0.5 text-sm text-slate-500">
              Al completar los {modules.length} módulos y demostrar tus capacidades clave, certificas el nivel y pasas al
              siguiente.{" "}
              <Link to="/progress" className="font-semibold text-blue-600 hover:text-blue-500">
                Ver mis requisitos →
              </Link>
            </p>
          </div>
        </div>
      </div>

      <AppFooter />
    </div>
  )
}

function MiniStat({ icon, value, label }: { icon: typeof faClock; value: string; label: string }) {
  return (
    <div>
      <FontAwesomeIcon icon={icon} className="text-blue-300" />
      <p className="mt-1 text-lg font-extrabold">{value}</p>
      <p className="text-[11px] text-slate-400">{label}</p>
    </div>
  )
}
