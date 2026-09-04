import {
  faArrowRight,
  faBolt,
  faCircleCheck,
  faComments,
  faGaugeHigh,
  faGraduationCap,
  faLanguage,
  faPlus,
  faRoute,
  faWandMagicSparkles,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useEffect, useState } from "react"
import { Link, Navigate } from "react-router-dom"
import { api } from "../api/client"
import type { CEFRLevel } from "../api/types"
import { useAuth } from "../auth/AuthContext"
import PlacementTest from "../components/PlacementTest"

// El precio no se inventa aquí: es el plan "premium_monthly" que ya define
// el backend (backend/app/scripts/seed_plans.py, price_cents=1000 USD/mes).
// Si allí cambia, esto tiene que cambiar con él.
const PRICE_USD = 10

export default function LandingPage() {
  const { user, isLoading } = useAuth()
  const [levels, setLevels] = useState<CEFRLevel[]>([])
  const [testOpen, setTestOpen] = useState(false)

  useEffect(() => {
    api
      .get<CEFRLevel[]>("/levels")
      .then(setLevels)
      .catch(() => setLevels([])) // la landing debe pintarse aunque la API esté caída
  }, [])

  // Si ya hay sesión, la landing no pinta — va directo al dashboard.
  if (!isLoading && user) return <Navigate to="/dashboard" replace />

  const shownLevels = levels.length > 0 ? levels : PLACEHOLDER_LEVELS

  return (
    <div className="min-h-screen bg-white text-slate-900">
      {testOpen && <PlacementTest onClose={() => setTestOpen(false)} />}

      {/* ---------------- Nav ---------------- */}
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-6 px-4 py-3.5 sm:px-6 lg:px-8">
          <a href="#top" className="flex shrink-0 items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 text-sm font-black text-white shadow-sm">
              E
            </span>
            <span className="text-lg font-extrabold tracking-tight">Espikin</span>
          </a>

          <nav className="hidden items-center gap-1 md:flex">
            {[
              { href: "#como-funciona", label: "Cómo funciona" },
              { href: "#niveles", label: "Niveles" },
              { href: "#precio", label: "Precio" },
              { href: "#faq", label: "Preguntas" },
            ].map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={() => setTestOpen(true)}
              className="hidden rounded-full px-4 py-2.5 text-sm font-semibold text-blue-600 transition hover:bg-blue-50 sm:block"
            >
              Prueba tu nivel
            </button>
            <Link
              to="/login"
              className="rounded-full px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            >
              Entrar
            </Link>
            <Link
              to="/login?mode=register"
              className="rounded-full bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition active:scale-[0.98] hover:bg-slate-800"
            >
              Empezar
            </Link>
          </div>
        </div>
      </header>

      <main id="top">
        {/* ---------------- Hero ---------------- */}
        <section className="relative overflow-hidden">
          {/* Halo de color detrás del hero, sin imágenes: gradiente difuminado. */}
          <div
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-[-12rem] h-[32rem] w-[52rem] -translate-x-1/2 rounded-full bg-gradient-to-br from-blue-200 via-sky-100 to-transparent blur-3xl"
          />
          <div className="relative mx-auto w-full max-w-7xl px-4 pb-16 pt-16 text-center sm:px-6 lg:px-8 lg:pb-24 lg:pt-24">
            <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-4 py-1.5 text-xs font-semibold text-blue-700">
              <FontAwesomeIcon icon={faWandMagicSparkles} />
              Tutor de IA · Certificación MCER (A1–C2)
            </span>

            <h1 className="mx-auto mt-7 max-w-4xl text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
              Habla inglés de verdad con un tutor que{" "}
              <span className="bg-gradient-to-r from-blue-600 to-sky-500 bg-clip-text text-transparent">
                entiende tus errores de hispanohablante
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-500">
              No es un chatbot genérico. Espikin sabe que dirás <em>“I have 25 years”</em> antes de que lo digas, y que
              tu <em>“Give me a coffee”</em> suena grosero sin que nadie te lo haya dicho nunca.
            </p>

            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <button
                onClick={() => setTestOpen(true)}
                className="flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-8 py-4 font-semibold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500 sm:w-auto"
              >
                <FontAwesomeIcon icon={faGaugeHigh} />
                Prueba tu nivel gratis
              </button>
              <Link
                to="/login?mode=register"
                className="flex w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-8 py-4 font-semibold text-slate-900 transition active:scale-[0.98] hover:bg-slate-50 sm:w-auto"
              >
                Crear cuenta
                <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
              </Link>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              La prueba tarda 2 minutos · sin tarjeta · sin registro
            </p>

            <div className="mx-auto mt-14 grid max-w-3xl grid-cols-3 gap-4 border-t border-slate-100 pt-8">
              {[
                { value: "6", label: "niveles, de A1 a C2" },
                { value: "24/7", label: "tu tutor, sin agenda" },
                { value: `$${PRICE_USD}`, label: "al mes, todo incluido" },
              ].map((stat) => (
                <div key={stat.label}>
                  <p className="text-2xl font-extrabold text-slate-900 sm:text-3xl">{stat.value}</p>
                  <p className="mt-1 text-xs text-slate-500 sm:text-sm">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------- Diferenciadores ---------------- */}
        <section className="border-y border-slate-200 bg-slate-50">
          <div className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-extrabold tracking-tight lg:text-4xl">
                Por qué aprendes más rápido aquí
              </h2>
              <p className="mt-3 text-slate-500">
                Tres decisiones de diseño que casi ninguna academia toma.
              </p>
            </div>

            <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
              <Feature
                icon={faLanguage}
                title="Diseñado para tu idioma, no traducido"
                text="Cada módulo anticipa los errores que comete alguien que piensa en español: sujeto nulo, orden de adjetivos, falsos amigos, la -s de tercera persona. Tu tutor los espera."
              />
              <Feature
                icon={faComments}
                title="Corrige en orden de impacto"
                text="Lo que rompe la comunicación se corrige al momento. Lo que está por encima de tu nivel, se ignora. Corregirlo todo es lo que hace que la gente deje de hablar."
              />
              <Feature
                icon={faGraduationCap}
                title="Progreso por evidencia real"
                text="Una capacidad se da por dominada tras demostrarla tres veces, en contextos y días distintos. Sin atajos, sin barras que suben por hacer clic."
              />
            </div>
          </div>
        </section>

        {/* ---------------- Cómo funciona ---------------- */}
        <section id="como-funciona" className="mx-auto w-full max-w-7xl scroll-mt-20 px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
          <div className="mx-auto max-w-2xl text-center">
            <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">Cómo funciona</span>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight lg:text-4xl">De cero a certificado, en tres pasos</h2>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            {[
              {
                step: "01",
                icon: faGaugeHigh,
                title: "Descubre tu nivel",
                text: "Dos minutos de prueba y sabes en cuál de los seis niveles MCER estás — y exactamente qué fallaste y por qué.",
              },
              {
                step: "02",
                icon: faComments,
                title: "Practica con tu tutor",
                text: "Conversas por escrito con un tutor que se adapta al módulo activo: nunca usa estructuras por encima de tu nivel ni te deja sin corregir lo que importa.",
              },
              {
                step: "03",
                icon: faGraduationCap,
                title: "Certifica el nivel",
                text: "Cuando acumulas evidencia suficiente en las capacidades críticas, el nivel se certifica solo y pasas al siguiente.",
              },
            ].map((item) => (
              <div key={item.step} className="relative rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                <span className="text-sm font-black text-blue-200">{item.step}</span>
                <span className="mt-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                  <FontAwesomeIcon icon={item.icon} />
                </span>
                <h3 className="mt-4 text-lg font-bold">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-500">{item.text}</p>
              </div>
            ))}
          </div>

          <div className="mt-10 text-center">
            <button
              onClick={() => setTestOpen(true)}
              className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-7 py-3.5 font-semibold text-white transition active:scale-[0.98] hover:bg-blue-500"
            >
              <FontAwesomeIcon icon={faBolt} />
              Empezar por la prueba de nivel
            </button>
          </div>
        </section>

        {/* ---------------- Niveles ---------------- */}
        <section id="niveles" className="scroll-mt-20 border-y border-slate-200 bg-slate-50">
          <div className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">
                  <FontAwesomeIcon icon={faRoute} className="mr-1.5" />
                  Ruta de certificación
                </span>
                <h2 className="mt-2 text-3xl font-extrabold tracking-tight lg:text-4xl">Los seis niveles del MCER</h2>
                <p className="mt-2 max-w-xl text-slate-500">
                  El mismo marco que usan Cambridge y el Consejo de Europa. Con las horas reales que cuesta cada nivel,
                  no promesas de “fluidez en 30 días”.
                </p>
              </div>
              <span className="rounded-full border border-blue-100 bg-white px-4 py-2 text-xs font-semibold text-blue-700">
                ~1.050 h de A1 a C2
              </span>
            </div>

            <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {shownLevels.map((level) => (
                <div
                  key={level.code}
                  className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg"
                >
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-extrabold text-blue-600">{level.code}</span>
                    <span className="text-xs font-medium text-slate-400">
                      {level.target_hours_min}–{level.target_hours_max} h
                    </span>
                  </div>
                  <h3 className="mt-2 text-lg font-bold">{level.name}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{level.description.split(".")[0]}.</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------- Precio ---------------- */}
        <section id="precio" className="mx-auto w-full max-w-7xl scroll-mt-20 px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
          <div className="mx-auto max-w-2xl text-center">
            <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">Precio</span>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight lg:text-4xl">Un plan. Todo incluido.</h2>
            <p className="mt-3 text-slate-500">
              Sin niveles de suscripción, sin cobrar aparte por hablar con tu tutor, sin permanencia.
            </p>
          </div>

          <div className="mx-auto mt-12 max-w-lg">
            <div className="overflow-hidden rounded-3xl border-2 border-blue-600 bg-white shadow-xl shadow-blue-600/10">
              <div className="bg-gradient-to-br from-blue-600 to-blue-500 px-8 py-8 text-center text-white">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-100">Premium mensual</p>
                <p className="mt-3 flex items-baseline justify-center gap-1">
                  <span className="text-6xl font-extrabold">${PRICE_USD}</span>
                  <span className="text-lg font-medium text-blue-100">/mes</span>
                </p>
                <p className="mt-2 text-sm text-blue-100">Cancela cuando quieras</p>
              </div>

              <div className="px-8 py-8">
                <ul className="space-y-3.5">
                  {[
                    "Acceso completo a los 6 niveles, de A1 a C2",
                    "Tutor de IA ilimitado, 24/7, sin reservar hora",
                    "Corrección explicada: qué fallaste y por qué tu español te llevó ahí",
                    "Certificación MCER por evidencia acumulada, nivel a nivel",
                    "Currículo de 60+ módulos con tareas comunicativas reales",
                    "Seguimiento por capacidad: sabes exactamente qué dominas",
                    "Prueba de nivel y reubicación cuando avances",
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-3 text-sm text-slate-600">
                      <FontAwesomeIcon icon={faCircleCheck} className="mt-0.5 shrink-0 text-blue-600" />
                      {item}
                    </li>
                  ))}
                </ul>

                <Link
                  to="/login?mode=register"
                  className="mt-8 flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-6 py-4 font-semibold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500"
                >
                  Empezar ahora
                  <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
                </Link>
                <button
                  onClick={() => setTestOpen(true)}
                  className="mt-3 w-full rounded-full px-6 py-3 text-sm font-semibold text-slate-500 transition hover:bg-slate-100"
                >
                  Antes quiero probar mi nivel
                </button>
              </div>
            </div>

            <p className="mt-5 text-center text-xs text-slate-400">
              Pago con tarjeta, PayPal, Binance Pay o Pago Móvil (Venezuela).
            </p>
          </div>
        </section>

        {/* ---------------- FAQ ---------------- */}
        <section id="faq" className="scroll-mt-20 border-t border-slate-200 bg-slate-50">
          <div className="mx-auto w-full max-w-3xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
            <h2 className="text-center text-3xl font-extrabold tracking-tight lg:text-4xl">Preguntas frecuentes</h2>
            <div className="mt-10 space-y-4">
              {[
                {
                  q: "¿La prueba de nivel me certifica?",
                  a: "No, y no queremos que lo creas. Doce preguntas te dan una foto rápida para saber por dónde empezar. La certificación de un nivel exige demostrar cada capacidad varias veces, en contextos y días distintos, dentro de la plataforma.",
                },
                {
                  q: "¿Qué tan rápido llego a B2?",
                  a: "Depende de tus horas, pero seamos honestos: llegar a B2 desde cero son unas 560 horas de aprendizaje guiado según Cambridge y el Consejo de Europa. Cualquiera que te prometa B2 en tres meses está redefiniendo qué significa B2.",
                },
                {
                  q: "¿El tutor es una persona o una IA?",
                  a: "Una IA, y por eso está disponible 24/7 y cuesta $10 al mes en vez de $30 la hora. Está configurada por nivel y por módulo: nunca usa estructuras que aún no has visto ni te corrige cosas que no tocan todavía.",
                },
                {
                  q: "¿Sirve si ya sé algo de inglés?",
                  a: "Sí. La prueba de nivel te coloca donde estás realmente, no en A1 por defecto. Y si avanzas más rápido de lo esperado, la certificación por evidencia te deja pasar de nivel en cuanto lo demuestres.",
                },
                {
                  q: "¿Puedo cancelar?",
                  a: "Cuando quieras, sin permanencia ni penalización. La suscripción es mensual.",
                },
              ].map((item) => (
                <details
                  key={item.q}
                  className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm [&_summary::-webkit-details-marker]:hidden"
                >
                  <summary className="flex cursor-pointer items-center justify-between gap-4 font-semibold text-slate-900">
                    {item.q}
                    {/* El "+" gira 45° al abrir y se convierte en una "×":
                        el gesto de acordeón que todo el mundo reconoce. */}
                    <span className="shrink-0 text-blue-600 transition-transform duration-200 group-open:rotate-45">
                      <FontAwesomeIcon icon={faPlus} />
                    </span>
                  </summary>
                  <p className="mt-3 text-sm leading-relaxed text-slate-500">{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------- CTA final ---------------- */}
        <section className="relative overflow-hidden border-t border-slate-200">
          <div
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 h-[24rem] w-[42rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-br from-blue-200 via-sky-100 to-transparent blur-3xl"
          />
          <div className="relative mx-auto w-full max-w-3xl px-4 py-20 text-center sm:px-6 lg:px-8">
            <h2 className="text-3xl font-extrabold tracking-tight lg:text-4xl">
              Descubre tu nivel real en 2 minutos
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-slate-500">
              Sin tarjeta, sin registro. Solo doce preguntas que te dirán exactamente dónde estás y qué te está frenando.
            </p>
            <button
              onClick={() => setTestOpen(true)}
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-blue-600 px-8 py-4 font-semibold text-white shadow-lg shadow-blue-600/20 transition active:scale-[0.98] hover:bg-blue-500"
            >
              <FontAwesomeIcon icon={faGaugeHigh} />
              Hacer la prueba gratis
            </button>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-6 lg:px-8">
          <span className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-blue-500 text-xs font-black text-white">
              E
            </span>
            <span className="font-bold">Espikin</span>
          </span>
          <p className="text-xs text-slate-400">Inglés con tutores de IA · Marco Común Europeo · © 2026</p>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/login" className="text-slate-500 hover:text-slate-900">
              Entrar
            </Link>
            <Link to="/login?mode=register" className="font-semibold text-blue-600 hover:text-blue-500">
              Crear cuenta
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

function Feature({ icon, title, text }: { icon: typeof faLanguage; title: string; text: string }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-sm">
        <FontAwesomeIcon icon={icon} />
      </span>
      <h3 className="mt-5 text-lg font-bold">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-500">{text}</p>
    </div>
  )
}

// Solo se usa si /levels no responde (ej. backend recién arrancando) —
// para que la landing nunca se vea vacía. Datos tomados del propio
// seed_cefr_levels.py, no inventados.
const PLACEHOLDER_LEVELS: CEFRLevel[] = [
  { id: "a1", code: "A1", name: "Acceso", order: 1, description: "Frases básicas y supervivencia cotidiana.", target_hours_min: 90, target_hours_max: 100 },
  { id: "a2", code: "A2", name: "Plataforma", order: 2, description: "Intercambio directo de información habitual.", target_hours_min: 90, target_hours_max: 110 },
  { id: "b1", code: "B1", name: "Umbral", order: 3, description: "Autonomía en viajes y situaciones cotidianas.", target_hours_min: 150, target_hours_max: 180 },
  { id: "b2", code: "B2", name: "Avanzado", order: 4, description: "Comprensión de ideas complejas y abstractas.", target_hours_min: 180, target_hours_max: 200 },
  { id: "c1", code: "C1", name: "Dominio", order: 5, description: "Uso flexible y eficaz para fines sociales y profesionales.", target_hours_min: 200, target_hours_max: 220 },
  { id: "c2", code: "C2", name: "Maestría", order: 6, description: "Comprensión total con facilidad y matiz.", target_hours_min: 250, target_hours_max: 300 },
]
