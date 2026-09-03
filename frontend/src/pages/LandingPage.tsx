import { faArrowRight, faCommentDots, faGraduationCap, faRocket, faWandMagicSparkles } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Navigate, Link } from "react-router-dom"
import { api } from "../api/client"
import type { CEFRLevel } from "../api/types"
import { useAuth } from "../auth/AuthContext"

export default function LandingPage() {
  const { user, isLoading } = useAuth()
  const [levels, setLevels] = useState<CEFRLevel[]>([])

  useEffect(() => {
    api
      .get<CEFRLevel[]>("/levels")
      .then(setLevels)
      .catch(() => setLevels([])) // la landing debe poder pintarse aunque la API esté caída
  }, [])

  // Si ya hay sesión, la landing no pinta — va directo al dashboard.
  if (!isLoading && user) return <Navigate to="/dashboard" replace />

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <span className="flex items-center gap-2 font-bold">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm text-white">
              EA
            </span>
            English Academy
          </span>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-semibold text-slate-600 hover:text-slate-900">
              Ingresar
            </Link>
            <Link
              to="/login?mode=register"
              className="rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500"
            >
              Comenzar
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto w-full max-w-7xl px-4 py-16 text-center sm:px-6 lg:px-8 lg:py-28">
          <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-4 py-1.5 text-xs font-semibold text-blue-600">
            <FontAwesomeIcon icon={faWandMagicSparkles} />
            Tutores de IA · Marco Común Europeo (MCER)
          </span>
          <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-extrabold leading-[1.1] sm:text-5xl lg:text-6xl">
            De A1 a C2 con un tutor que <span className="text-blue-600">entiende tus errores</span> de hispanohablante
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-500">
            No es un chatbot genérico. Cada módulo sabe qué errores comete alguien que piensa en español —
            del <em>“I have 25 years”</em> al imperativo que suena grosero en inglés — y corrige en orden de
            impacto real.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to="/login?mode=register"
              className="flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-8 py-4 font-semibold text-white shadow-sm transition active:scale-[0.98] hover:bg-blue-500 sm:w-auto"
            >
              <FontAwesomeIcon icon={faRocket} />
              Comenzar ahora
            </Link>
            <Link
              to="/login"
              className="flex w-full items-center justify-center gap-2 rounded-full bg-slate-900 px-8 py-4 font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800 sm:w-auto"
            >
              Ingresar
              <FontAwesomeIcon icon={faArrowRight} />
            </Link>
          </div>
        </section>

        {/* Qué hace distinto al producto */}
        <section className="border-y border-slate-200 bg-slate-50">
          <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-8 px-4 py-16 sm:px-6 md:grid-cols-3 lg:px-8 lg:py-20">
            <Feature
              icon={faCommentDots}
              title="Conversación real, corregida"
              text="Hablas con tu tutor y recibes correcciones en el momento, calibradas a tu nivel: lo que rompe la comunicación se corrige ya; lo que está por encima de tu nivel, se ignora."
            />
            <Feature
              icon={faGraduationCap}
              title="Progreso por evidencia, no por clics"
              text="Cada capacidad del MCER se da por dominada solo tras demostrarla varias veces, en contextos y sesiones distintas. Sin atajos."
            />
            <Feature
              icon={faWandMagicSparkles}
              title="Diseñado para hispanohablantes"
              text="Interferencia del español anticipada módulo a módulo: falsos amigos, sujeto nulo, orden de adjetivos y la cortesía que el inglés exige y el español no."
            />
          </div>
        </section>

        {/* Ruta de certificación */}
        <section className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-20">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-3xl font-extrabold lg:text-4xl">Ruta de certificación</h2>
              <p className="mt-2 text-slate-500">Los seis niveles del Marco Común Europeo, de principio a fin.</p>
            </div>
            <span className="rounded-full bg-blue-50 px-4 py-1.5 text-xs font-semibold text-blue-600">
              ~1.050 h de aprendizaje guiado
            </span>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(levels.length > 0 ? levels : PLACEHOLDER_LEVELS).map((level) => (
              <div
                key={level.code}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-extrabold text-blue-600">{level.code}</span>
                  <span className="text-xs text-slate-400">
                    {level.target_hours_min}–{level.target_hours_max} h
                  </span>
                </div>
                <h3 className="mt-2 text-lg font-semibold">{level.name}</h3>
                <p className="mt-1 text-sm text-slate-500">{level.description.split(".")[0]}.</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA final */}
        <section className="border-t border-slate-200 bg-slate-50">
          <div className="mx-auto w-full max-w-7xl px-4 py-16 text-center sm:px-6 lg:px-8 lg:py-20">
            <h2 className="text-3xl font-extrabold lg:text-4xl">Empieza hoy por A1</h2>
            <p className="mx-auto mt-3 max-w-xl text-slate-500">
              Crea tu cuenta y abre el primer módulo. Tu progreso se mide en capacidades reales, no en lecciones vistas.
            </p>
            <Link
              to="/login?mode=register"
              className="mt-8 inline-flex items-center justify-center gap-2 rounded-full bg-blue-600 px-8 py-4 font-semibold text-white shadow-sm transition active:scale-[0.98] hover:bg-blue-500"
            >
              <FontAwesomeIcon icon={faRocket} />
              Crear mi cuenta
            </Link>
          </div>
        </section>
      </main>

      <footer className="mx-auto w-full max-w-7xl px-4 py-10 text-center text-xs text-slate-400 sm:px-6 lg:px-8">
        English Academy © 2026
      </footer>
    </div>
  )
}

function Feature({ icon, title, text }: { icon: typeof faRocket; title: string; text: string }) {
  return (
    <div>
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-white">
        <FontAwesomeIcon icon={icon} />
      </span>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-500">{text}</p>
    </div>
  )
}

// Solo se usa si /levels no responde (ej. backend recién arrancando) —
// para que la landing nunca se vea vacía. Nombres/descripciones y horas
// tomados del propio seed_cefr_levels.py, no inventados.
const PLACEHOLDER_LEVELS: CEFRLevel[] = [
  { id: "a1", code: "A1", name: "Acceso", order: 1, description: "Frases básicas y supervivencia.", target_hours_min: 90, target_hours_max: 100 },
  { id: "a2", code: "A2", name: "Plataforma", order: 2, description: "Intercambio directo de información.", target_hours_min: 90, target_hours_max: 110 },
  { id: "b1", code: "B1", name: "Umbral", order: 3, description: "Autonomía en viajes y situaciones cotidianas.", target_hours_min: 150, target_hours_max: 180 },
  { id: "b2", code: "B2", name: "Avanzado", order: 4, description: "Entendimiento de ideas complejas.", target_hours_min: 180, target_hours_max: 200 },
  { id: "c1", code: "C1", name: "Dominio", order: 5, description: "Uso flexible para fines sociales.", target_hours_min: 200, target_hours_max: 220 },
  { id: "c2", code: "C2", name: "Maestría", order: 6, description: "Comprensión total con facilidad.", target_hours_min: 250, target_hours_max: 300 },
]
