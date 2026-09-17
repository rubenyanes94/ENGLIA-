import {
  faArrowRight,
  faBolt,
  faBookBookmark,
  faBookOpen,
  faChartLine,
  faCircleCheck,
  faClock,
  faComments,
  faGraduationCap,
  faLock,
  faMicrophone,
  faRobot,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type {
  CertificationProgress,
  DescriptorMasterySummary,
  FlashCourseSummary,
  ModuleDetail,
  ModuleProgress,
  Task,
  Tutor,
} from "../api/types"
import { useAuth } from "../auth/AuthContext"
import Avatar from "../components/Avatar"
import CircularProgress from "../components/CircularProgress"
import SentenceGame from "../components/SentenceGame"
import { categoryMeta, courseIcon } from "../components/library/courseMeta"

// Único nivel con currículo sembrado hoy. Si el alumno todavía no
// certificó nada, current_level_code viene null (ver models/user.py) —
// en ese caso, A1 es el punto de partida real de todo alumno nuevo.
const LEVEL_CODE = "A1"

/**
 * Inicio: lo primero que ve el alumno al entrar.
 *
 * Ocupa todo el ancho y lo reparte en columnas en vez de apilar tarjetas
 * estrechas: arriba, dónde está (nivel y métricas); en el centro, algo que
 * hacer ya mismo (el juego y el tutor); abajo, cómo seguir (su camino de
 * módulos y la Biblioteca). Todo sale de datos reales del alumno.
 */
export default function DashboardPage() {
  const { user } = useAuth()
  const [progress, setProgress] = useState<CertificationProgress | null>(null)
  const [descriptors, setDescriptors] = useState<DescriptorMasterySummary | null>(null)
  const [tutor, setTutor] = useState<Tutor | null>(null)
  const [activeModule, setActiveModule] = useState<ModuleDetail | null>(null)
  const [courses, setCourses] = useState<FlashCourseSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api
      .get<FlashCourseSummary[]>("/library/courses")
      .then(setCourses)
      .catch(() => setCourses([]))

    Promise.all([
      api.get<CertificationProgress>(`/levels/${LEVEL_CODE}/certification-progress`),
      api.get<DescriptorMasterySummary>(`/users/me/progress/descriptors/${LEVEL_CODE}`),
      api.get<Tutor>(`/levels/${LEVEL_CODE}/tutor`).catch(() => null),
    ])
      .then(async ([progressData, descriptorData, tutorData]) => {
        setProgress(progressData)
        setDescriptors(descriptorData)
        setTutor(tutorData)

        // El módulo activo se pide APARTE (y solo uno) porque la práctica
        // del día sale de sus `tasks`, que el listado de módulos no trae.
        const next =
          progressData.modules.find((m) => m.status === "in_progress") ??
          progressData.modules.find((m) => m.status === "available")
        if (next) {
          setActiveModule(await api.get<ModuleDetail>(`/modules/${next.id}`).catch(() => null))
        }
      })
      .catch(() => {
        setProgress(null)
        setDescriptors(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const firstName = user?.full_name.split(" ")[0] ?? ""
  const tutorName = tutor?.name ?? "Teacher David"
  const nextModule =
    progress?.modules.find((m) => m.status === "in_progress") ?? progress?.modules.find((m) => m.status === "available")
  const completedCount = progress?.modules.filter((m) => m.status === "completed").length ?? 0
  const moduleTotal = progress?.modules.length ?? 0

  // La "práctica de hoy" es una tarea REAL del módulo activo. Se rota por
  // día del año para que cambie a diario de forma estable, en vez de
  // bailar en cada recarga.
  const dailyTask: Task | undefined = activeModule?.tasks.length
    ? activeModule.tasks[dayOfYear() % activeModule.tasks.length]
    : undefined

  // Cursos de la Biblioteca: primero los empezados y sin terminar, que son
  // los que el alumno tiene más a mano retomar.
  const featuredCourses = [...courses]
    .sort((a, b) => Number(b.completed_scenarios > 0 && !b.completed) - Number(a.completed_scenarios > 0 && !a.completed))
    .slice(0, 4)

  return (
    <div className="space-y-6 lg:space-y-8">
      {/* ---------------- Franja superior: saludo y métricas ---------------- */}
      <section className="relative overflow-hidden rounded-3xl bg-ink-900 text-white shadow-xl">
        <div
          aria-hidden
          className="pointer-events-none absolute -left-24 -top-24 h-80 w-80 rounded-full bg-brand-600/30 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-32 right-0 h-96 w-96 rounded-full bg-brand-500/20 blur-3xl"
        />

        <div className="relative grid grid-cols-1 gap-8 p-6 sm:p-8 lg:grid-cols-12 lg:items-center lg:gap-10 lg:p-10">
          <div className="lg:col-span-5">
            <div className="flex items-center gap-4">
              <Avatar name={user?.full_name ?? ""} avatarUrl={user?.avatar_url} size={64} />
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wider text-brand-300">Bienvenido de vuelta</p>
                <h1 className="truncate text-3xl font-extrabold tracking-tight lg:text-4xl">¡Hola, {firstName}!</h1>
              </div>
            </div>
            <p className="mt-5 max-w-lg text-slate-300">
              {nextModule
                ? `Vas por el módulo ${nextModule.order} de ${moduleTotal} del nivel ${LEVEL_CODE}: ${withFinalPeriod(nextModule.title_es ?? nextModule.title)}`
                : completedCount > 0 && completedCount === moduleTotal
                  ? `Completaste todos los módulos del nivel ${LEVEL_CODE}.`
                  : `Tu camino empieza en el nivel ${LEVEL_CODE}.`}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {nextModule && (
                <Link
                  to={`/modules/${nextModule.id}`}
                  className="flex items-center gap-2 rounded-full bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-brand-600/30 transition active:scale-[0.98] hover:bg-brand-500"
                >
                  <FontAwesomeIcon icon={faBookOpen} className="text-xs" />
                  {nextModule.status === "in_progress" ? "Continuar módulo" : "Empezar módulo"}
                </Link>
              )}
              <Link
                to="/chat"
                className="flex items-center gap-2 rounded-full bg-white/10 px-6 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-white/20"
              >
                <FontAwesomeIcon icon={faComments} className="text-xs" />
                Hablar con {tutorName}
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:col-span-7">
            <div className="flex flex-col items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-5">
              {loading ? (
                <div className="h-14 w-14 animate-pulse rounded-full bg-white/10" />
              ) : (
                <CircularProgress percentage={progress?.percentage ?? 0} size={56} strokeWidth={6} progressColor="#A184FB" />
              )}
              <div>
                <p className="text-xl font-extrabold sm:text-2xl">Nivel {LEVEL_CODE}</p>
                <p className="text-xs text-slate-400">{Math.round(progress?.percentage ?? 0)}% completado</p>
              </div>
            </div>
            <Metric
              icon={faClock}
              value={progress ? `${progress.hours_completed}h` : "—"}
              label={progress ? `de ${progress.target_hours_min}–${progress.target_hours_max}h` : "horas certificadas"}
              loading={loading}
            />
            <Metric
              icon={faChartLine}
              value={descriptors ? `${descriptors.mastered}/${descriptors.total}` : "—"}
              label="descriptores dominados"
              loading={loading}
            />
            <Metric
              icon={faCircleCheck}
              value={progress ? `${completedCount}/${moduleTotal}` : "—"}
              label="módulos aprobados"
              loading={loading}
            />
          </div>
        </div>
      </section>

      {/* ---------------- Centro: juego, tutor y práctica ---------------- */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="xl:col-span-8">
          <SentenceGame />
        </div>

        <div className="flex flex-col gap-6 xl:col-span-4">
          {/* Tutor: oscuro y destacado. El nombre sale de la base de datos
              (GET /levels/{code}/tutor), no de una constante. */}
          <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 to-brand-700 p-6 text-white shadow-lg shadow-brand-600/20 lg:p-7">
            <div
              aria-hidden
              className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-white/10 blur-2xl"
            />
            <div className="relative">
              <div className="flex items-center gap-4">
                <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-2xl backdrop-blur">
                  <FontAwesomeIcon icon={faRobot} />
                </span>
                <div className="min-w-0">
                  {/* El estado va junto a la etiqueta y no encima del icono:
                      superpuesto, la insignia tapaba casi todo el robot. */}
                  <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brand-100">
                    Tu tutor de IA
                    <span className="flex items-center gap-1 rounded-full bg-emerald-400/20 px-2 py-0.5 text-[10px] text-emerald-200">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" /> En línea
                    </span>
                  </p>
                  <h2 className="truncate text-2xl font-extrabold tracking-tight">{tutorName}</h2>
                </div>
              </div>

              {/* Solo lo que el tutor hace de verdad hoy. */}
              <ul className="mt-5 space-y-2.5 text-sm text-brand-50">
                <li className="flex items-center gap-2.5">
                  <FontAwesomeIcon icon={faComments} className="w-4 text-brand-200" /> Conversa contigo y corrige al momento
                </li>
                <li className="flex items-center gap-2.5">
                  <FontAwesomeIcon icon={faBookOpen} className="w-4 text-brand-200" /> Te da las lecciones narradas
                </li>
                <li className="flex items-center gap-2.5">
                  <FontAwesomeIcon icon={faMicrophone} className="w-4 text-brand-200" /> Escucha y evalúa tu pronunciación
                </li>
              </ul>

              <Link
                to="/chat"
                className="mt-6 flex w-full items-center justify-center gap-2.5 rounded-2xl bg-white px-6 py-3.5 font-bold text-brand-700 transition active:scale-[0.98] hover:bg-brand-50"
              >
                <FontAwesomeIcon icon={faGraduationCap} />
                Continuar mi clase
              </Link>
            </div>
          </section>

          {/* Práctica del día: una tarea REAL del módulo activo. */}
          <section className="flex flex-1 flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:p-7">
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
              <FontAwesomeIcon icon={faBolt} className="text-amber-500" /> Práctica de hoy
            </p>
            {dailyTask ? (
              <>
                <p className="mt-3 flex-1 leading-relaxed text-slate-700">{dailyTask.prompt}</p>
                <Link
                  to={`/chat?module=${activeModule?.id}&task=${dailyTask.id}`}
                  className="mt-5 flex items-center justify-center gap-2 rounded-2xl bg-ink-900 px-6 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-ink-800"
                >
                  <FontAwesomeIcon icon={faComments} /> Practicar con {tutorName}
                </Link>
              </>
            ) : (
              <p className="mt-3 flex-1 text-sm text-slate-500">
                {loading ? "Buscando tu práctica de hoy..." : "Empieza un módulo para recibir tu práctica diaria."}
              </p>
            )}
          </section>
        </div>
      </div>

      {/* ---------------- Abajo: camino de módulos y Biblioteca ---------------- */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:p-8 xl:col-span-7">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Tu camino</p>
              <h2 className="mt-1 text-xl font-extrabold tracking-tight text-slate-900">Nivel {LEVEL_CODE}</h2>
            </div>
            <Link to="/classroom" className="flex items-center gap-2 text-sm font-semibold text-brand-600 hover:text-brand-500">
              Ver classroom <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </Link>
          </div>

          {progress && <ModulePath modules={progress.modules} />}

          {nextModule && (
            <div className="mt-6 flex flex-col gap-4 rounded-2xl bg-slate-50 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {nextModule.status === "in_progress" ? "Continúa donde lo dejaste" : "Siguiente módulo"}
                </p>
                <p className="mt-1 font-bold text-slate-900">
                  {nextModule.order}. {nextModule.title_es ?? nextModule.title}
                </p>
                <p className="text-sm text-slate-500">
                  {nextModule.estimated_hours}h · {nextModule.descriptors.length} descriptores
                </p>
              </div>
              <Link
                to={`/modules/${nextModule.id}`}
                className="flex shrink-0 items-center justify-center gap-2 rounded-full bg-brand-600 px-6 py-3 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-brand-500"
              >
                Abrir módulo <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
              </Link>
            </div>
          )}
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:p-8 xl:col-span-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                <FontAwesomeIcon icon={faBookBookmark} /> Biblioteca
              </p>
              <h2 className="mt-1 text-xl font-extrabold tracking-tight text-slate-900">Cursos flash</h2>
            </div>
            <Link to="/library" className="flex items-center gap-2 text-sm font-semibold text-brand-600 hover:text-brand-500">
              Ver todos <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </Link>
          </div>

          <ul className="mt-5 space-y-2">
            {featuredCourses.map((course) => {
              const meta = categoryMeta(course.category)
              return (
                <li key={course.slug}>
                  <Link
                    to={`/library/${course.slug}`}
                    className="group flex items-center gap-4 rounded-2xl p-3 transition hover:bg-slate-50"
                  >
                    <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${meta.tile}`}>
                      <FontAwesomeIcon icon={courseIcon(course.icon)} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold leading-snug text-slate-900">{course.title_es}</span>
                      <span className="block text-xs text-slate-500">
                        {course.completed
                          ? "Completado"
                          : course.completed_scenarios > 0
                            ? `${course.completed_scenarios} de ${course.scenario_count} escenarios`
                            : `${course.duration_minutes} min · ${course.scenario_count} escenarios`}
                      </span>
                    </span>
                    <FontAwesomeIcon
                      icon={course.completed ? faCircleCheck : faArrowRight}
                      className={`text-xs transition group-hover:translate-x-0.5 ${course.completed ? "text-emerald-500" : "text-slate-300"}`}
                    />
                  </Link>
                </li>
              )
            })}
            {featuredCourses.length === 0 && <li className="text-sm text-slate-500">Cargando cursos...</li>}
          </ul>
        </section>
      </div>
    </div>
  )
}

/** Los módulos del nivel como una fila de pasos: se ve de un vistazo
 * cuánto camino queda, cuál toca y cuáles siguen bloqueados. */
function ModulePath({ modules }: { modules: ModuleProgress[] }) {
  return (
    <ol className="mt-6 grid grid-cols-5 gap-2 sm:grid-cols-10">
      {modules.map((module) => {
        const tone =
          module.status === "completed"
            ? "bg-emerald-500 text-white"
            : module.status === "in_progress" || module.status === "available"
              ? "bg-brand-600 text-white ring-4 ring-brand-100"
              : "bg-slate-100 text-slate-400"
        return (
          <li key={module.id}>
            <Link
              to={module.status === "locked" ? "/classroom" : `/modules/${module.id}`}
              title={`${module.order}. ${module.title_es ?? module.title}`}
              className="flex flex-col items-center gap-1.5"
            >
              <span className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${tone}`}>
                {module.status === "completed" ? (
                  <FontAwesomeIcon icon={faCircleCheck} />
                ) : module.status === "locked" ? (
                  <FontAwesomeIcon icon={faLock} className="text-xs" />
                ) : (
                  module.order
                )}
              </span>
              <span className="hidden w-full truncate text-center text-[10px] font-medium text-slate-500 lg:block">
                {module.title_es ?? module.title}
              </span>
            </Link>
          </li>
        )
      })}
    </ol>
  )
}

function Metric({
  icon,
  value,
  label,
  loading,
}: {
  icon: typeof faClock
  value: string
  label: string
  loading: boolean
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <FontAwesomeIcon icon={icon} className="text-brand-300" />
      {loading ? (
        <div className="mt-3 h-7 w-16 animate-pulse rounded bg-white/10" />
      ) : (
        <p className="mt-2 text-2xl font-extrabold">{value}</p>
      )}
      <p className="text-xs text-slate-400">{label}</p>
    </div>
  )
}

/** Día del año (1-366). Sirve para rotar la práctica diaria de forma
 * estable: cambia cada día, pero no en cada recarga. */
function dayOfYear(): number {
  const now = new Date()
  const start = new Date(now.getFullYear(), 0, 0)
  return Math.floor((now.getTime() - start.getTime()) / 86_400_000)
}

/** Añade punto final solo si el texto no termina ya en puntuación: los
 * títulos de módulo pueden acabar en "..." ("Hola, soy...") y un punto de
 * más deja "soy....". */
function withFinalPeriod(text: string): string {
  return /[.!?…]$/.test(text.trim()) ? text : `${text}.`
}
