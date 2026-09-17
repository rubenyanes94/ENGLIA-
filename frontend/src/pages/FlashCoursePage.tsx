import {
  faArrowLeft,
  faCircleCheck,
  faClock,
  faComments,
  faLanguage,
  faMasksTheater,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { api } from "../api/client"
import type { FlashCourseDetail } from "../api/types"
import { ApiError } from "../api/types"
import { categoryMeta, courseIcon } from "../components/library/courseMeta"

/** Un curso flash: la chuleta de frases y los escenarios para practicar.
 *
 * El orden de la página es el orden de estudio: primero las frases (qué
 * decir), luego los escenarios (decirlo con el tutor). Un alumno que entra
 * directo a la práctica sin haber visto las frases se bloquea al primer
 * turno.
 */
export default function FlashCoursePage() {
  const { slug } = useParams<{ slug: string }>()
  const [course, setCourse] = useState<FlashCourseDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!slug) return
    api
      .get<FlashCourseDetail>(`/library/courses/${slug}`)
      .then(setCourse)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar el curso."))
    window.scrollTo({ top: 0 })
  }, [slug])

  if (error) return <p className="text-red-500">{error}</p>
  if (!course) {
    return (
      <p className="flex items-center justify-center gap-2 py-24 text-slate-400">
        <FontAwesomeIcon icon={faSpinner} spin /> Abriendo el curso...
      </p>
    )
  }

  const meta = categoryMeta(course.category)
  const percent = course.scenario_count ? (course.completed_scenarios / course.scenario_count) * 100 : 0

  return (
    <div>
      <div className="space-y-6">
        <header className="relative overflow-hidden rounded-3xl bg-ink-900 p-6 text-white shadow-lg sm:p-8">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-brand-500/20 blur-3xl"
          />
          <div className="relative">
            <Link
              to="/library"
              className="inline-flex items-center gap-2 text-sm font-semibold text-slate-300 transition hover:text-white"
            >
              <FontAwesomeIcon icon={faArrowLeft} className="text-xs" /> Biblioteca
            </Link>

            <div className="mt-5 flex flex-col gap-5 sm:flex-row sm:items-center">
              <span className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-2xl ${meta.tile}`}>
                <FontAwesomeIcon icon={courseIcon(course.icon)} />
              </span>
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-wide text-brand-300">{meta.label}</p>
                <h1 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">{course.title_es}</h1>
                <p className="mt-0.5 text-sm text-slate-400">{course.title}</p>
              </div>
            </div>

            <p className="mt-4 max-w-2xl text-slate-300">{course.description_es}</p>

            <div className="mt-5 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wide">
              <span className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-slate-200">
                <FontAwesomeIcon icon={faClock} /> {course.duration_minutes} min
              </span>
              <span className="rounded-full bg-white/10 px-3 py-1 text-slate-200">
                Nivel recomendado {course.recommended_level}
              </span>
              {course.completed && (
                <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-1 text-emerald-300">
                  <FontAwesomeIcon icon={faCircleCheck} /> Completado
                </span>
              )}
            </div>

            <div className="mt-5 max-w-sm">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                <span>Tu progreso</span>
                <span>
                  {course.completed_scenarios} de {course.scenario_count} escenarios
                </span>
              </div>
              <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-400 transition-[width] duration-500"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
            <h2 className="flex items-center gap-2.5 text-lg font-bold tracking-tight text-slate-900">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-sm text-brand-600">
                <FontAwesomeIcon icon={faLanguage} />
              </span>
              Frases clave
            </h2>
            <p className="mt-1 text-sm text-slate-500">Repásalas antes de practicar: son las que vas a necesitar.</p>
            <ul className="mt-4 divide-y divide-slate-100">
              {course.key_phrases.map((phrase) => (
                <li key={phrase.en} className="py-3">
                  <p className="font-semibold text-slate-900">{phrase.en}</p>
                  <p className="mt-0.5 text-sm text-slate-500">{phrase.es}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-4 lg:col-span-3">
            <div>
              <h2 className="flex items-center gap-2.5 text-lg font-bold tracking-tight text-slate-900">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-sm text-brand-600">
                  <FontAwesomeIcon icon={faMasksTheater} />
                </span>
                Practica con el tutor
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                En cada escenario el tutor hace un papel. Háblale como en la situación real.
              </p>
            </div>

            {course.scenarios.map((scenario, index) => (
              <article
                key={scenario.id}
                className={`rounded-3xl border bg-white p-5 shadow-sm sm:p-6 ${
                  scenario.completed ? "border-emerald-200" : "border-slate-200"
                }`}
              >
                <div className="flex items-start gap-4">
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                      scenario.completed ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {scenario.completed ? <FontAwesomeIcon icon={faCircleCheck} /> : index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-bold text-slate-900">{scenario.title}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-slate-600">{scenario.prompt}</p>
                    <p className="mt-2 text-xs text-slate-400">
                      <span className="font-semibold text-slate-500">El tutor será:</span> {scenario.tutor_role}
                    </p>
                  </div>
                </div>
                <Link
                  to={`/chat?course=${course.slug}&task=${scenario.id}`}
                  className={`mt-4 flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold transition active:scale-[0.98] ${
                    scenario.completed
                      ? "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      : "bg-brand-600 text-white shadow-md shadow-brand-600/20 hover:bg-brand-500"
                  }`}
                >
                  <FontAwesomeIcon icon={faComments} />
                  {scenario.completed ? "Practicar otra vez" : "Practicar con el tutor"}
                </Link>
              </article>
            ))}
          </section>
        </div>
      </div>
    </div>
  )
}
