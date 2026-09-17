import { faArrowRight, faCircleCheck, faClock, faLayerGroup, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { FlashCourseSummary } from "../api/types"
import { ApiError } from "../api/types"
import AppFooter from "../components/AppFooter"
import { CATEGORIES, categoryMeta, courseIcon } from "../components/library/courseMeta"

/** La Biblioteca: cursos cortos por tema que se practican con el tutor.
 *
 * Complementa al Classroom, no lo sustituye. El Classroom es el camino del
 * nivel, en orden y con certificación; aquí el alumno entra directo a lo
 * que necesita esta semana (una entrevista, un viaje) sin tener que
 * desbloquear nada.
 */
export default function LibraryPage() {
  const [courses, setCourses] = useState<FlashCourseSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [category, setCategory] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<FlashCourseSummary[]>("/library/courses")
      .then(setCourses)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar la Biblioteca."))
      .finally(() => setLoading(false))
  }, [])

  const visible = category ? courses.filter((course) => course.category === category) : courses
  // Solo se ofrecen como filtro las categorías que tienen cursos: un
  // filtro que no devuelve nada es un callejón sin salida.
  const categories = Object.keys(CATEGORIES).filter((key) => courses.some((course) => course.category === key))
  const inProgress = courses.filter((course) => course.completed_scenarios > 0 && !course.completed).length
  const finished = courses.filter((course) => course.completed).length

  return (
    <div>
      <div className="space-y-8">
        <header className="relative overflow-hidden rounded-3xl bg-slate-900 p-7 text-white shadow-lg sm:p-10">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-blue-500/25 blur-3xl"
          />
          <div className="relative max-w-2xl">
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-blue-300">
              <FontAwesomeIcon icon={faLayerGroup} /> Biblioteca
            </p>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
              Inglés para lo que necesitas hoy
            </h1>
            <p className="mt-3 text-slate-300">
              Cursos flash de 15 a 25 minutos. Repasas las frases clave y las practicas con el tutor en situaciones
              reales: una entrevista, un restaurante, un turno en la plataforma.
            </p>
            {(inProgress > 0 || finished > 0) && (
              <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold">
                {inProgress > 0 && (
                  <span className="rounded-full bg-white/10 px-3 py-1.5">{inProgress} en curso</span>
                )}
                {finished > 0 && (
                  <span className="rounded-full bg-emerald-500/20 px-3 py-1.5 text-emerald-300">
                    {finished} completado{finished === 1 ? "" : "s"}
                  </span>
                )}
              </div>
            )}
          </div>
        </header>

        {loading && (
          <p className="flex items-center justify-center gap-2 py-16 text-slate-400">
            <FontAwesomeIcon icon={faSpinner} spin /> Cargando cursos...
          </p>
        )}
        {error && <p className="text-red-500">{error}</p>}

        {!loading && courses.length > 0 && (
          <>
            <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filtrar por categoría">
              <FilterChip active={category === null} onClick={() => setCategory(null)} label="Todos" />
              {categories.map((key) => (
                <FilterChip
                  key={key}
                  active={category === key}
                  onClick={() => setCategory(key)}
                  label={CATEGORIES[key].label}
                  icon={CATEGORIES[key].icon}
                />
              ))}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {visible.map((course) => (
                <CourseCard key={course.slug} course={course} />
              ))}
            </div>
          </>
        )}
      </div>

      <AppFooter />
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean
  onClick: () => void
  label: string
  icon?: typeof faClock
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition active:scale-[0.97] ${
        active ? "bg-slate-900 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
      }`}
    >
      {icon && <FontAwesomeIcon icon={icon} className="text-xs" />}
      {label}
    </button>
  )
}

function CourseCard({ course }: { course: FlashCourseSummary }) {
  const meta = categoryMeta(course.category)
  const started = course.completed_scenarios > 0
  const percent = course.scenario_count ? (course.completed_scenarios / course.scenario_count) * 100 : 0

  return (
    <Link
      to={`/library/${course.slug}`}
      className="group flex flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <span className={`flex h-12 w-12 items-center justify-center rounded-2xl text-lg ${meta.tile}`}>
          <FontAwesomeIcon icon={courseIcon(course.icon)} />
        </span>
        {course.completed ? (
          <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
            <FontAwesomeIcon icon={faCircleCheck} /> Completado
          </span>
        ) : (
          <span className={`text-xs font-bold uppercase tracking-wide ${meta.accent}`}>{meta.label}</span>
        )}
      </div>

      <h2 className="mt-4 text-lg font-extrabold leading-snug tracking-tight text-slate-900">{course.title_es}</h2>
      <p className="mt-1.5 flex-1 text-sm leading-relaxed text-slate-500">{course.description_es}</p>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-semibold text-slate-400">
        <span className="flex items-center gap-1.5">
          <FontAwesomeIcon icon={faClock} /> {course.duration_minutes} min
        </span>
        <span>{course.scenario_count} escenarios</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-500">{course.recommended_level}</span>
      </div>

      {started && !course.completed ? (
        <div className="mt-4">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-blue-600" style={{ width: `${percent}%` }} />
          </div>
          <p className="mt-1.5 text-xs font-semibold text-blue-600">
            {course.completed_scenarios} de {course.scenario_count} escenarios
          </p>
        </div>
      ) : (
        <span className="mt-4 flex items-center gap-2 text-sm font-semibold text-blue-600">
          {course.completed ? "Repasar" : "Empezar"}
          <FontAwesomeIcon icon={faArrowRight} className="text-xs transition group-hover:translate-x-1" />
        </span>
      )}
    </Link>
  )
}
