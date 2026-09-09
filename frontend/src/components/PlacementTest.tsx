import { faArrowRight, faCircleCheck, faCircleXmark, faXmark } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"
import { Link } from "react-router-dom"

/**
 * Prueba de nivel orientativa, 100% en el navegador (no toca el backend).
 *
 * Las preguntas NO son genéricas: cada una ataca un error de interferencia
 * del español documentado en nuestro propio currículo (ver
 * seed_a1_modules.py -> l1_interference, y el documento de diseño MCER
 * § 4) — "I have 25 years", sujeto nulo en verbos meteorológicos, -s de
 * tercera persona, falsos amigos... Es el mismo material que el tutor usa
 * para corregir, así que la prueba enseña de verdad qué hace distinto al
 * producto en vez de ser un quiz de relleno.
 *
 * El resultado se presenta SIEMPRE como orientativo: 12 preguntas de
 * opción múltiple no certifican un nivel MCER (eso exige evidencia
 * acumulada en producción real, ver el gate de salida de nivel). Decir lo
 * contrario sería vender humo.
 */

interface Question {
  level: string
  prompt: string
  sentence: string
  options: string[]
  correct: number
  why: string
}

const QUESTIONS: Question[] = [
  {
    level: "A1",
    prompt: "¿Cuántos años tienes?",
    sentence: "I ___ 25 years old.",
    options: ["have", "am", "make"],
    correct: 1,
    why: "En inglés la edad se expresa con el verbo be, no con have. «I have 25 years» es calco directo de «tengo 25 años».",
  },
  {
    level: "A1",
    prompt: "Hablando de una profesión",
    sentence: "She's ___ doctor.",
    options: ["a", "—", "the"],
    correct: 0,
    why: "El inglés exige artículo indefinido ante profesión. En español decimos «es médica», sin artículo.",
  },
  {
    level: "A1",
    prompt: "El tiempo atmosférico",
    sentence: "___ raining today.",
    options: ["Is", "It's", "There's"],
    correct: 1,
    why: "El inglés siempre necesita sujeto, aunque no signifique nada. En español el sujeto es nulo: «está lloviendo».",
  },
  {
    level: "A1",
    prompt: "Tercera persona del singular",
    sentence: "He ___ in a bank.",
    options: ["work", "works", "working"],
    correct: 1,
    why: "La -s de tercera persona es el error más persistente de todo A1 para un hispanohablante: no existe equivalente en español.",
  },
  {
    level: "A1",
    prompt: "Decir qué hay en un lugar",
    sentence: "In my city ___ many parks.",
    options: ["have", "there are", "it has"],
    correct: 1,
    why: "«Hay» se traduce con there is/there are, nunca con have. «In my city have...» es de los calcos más audibles.",
  },
  {
    level: "A2",
    prompt: "Comparando dos personas",
    sentence: "My brother is ___ than me.",
    options: ["more old", "older", "most old"],
    correct: 1,
    why: "Los adjetivos cortos forman el comparativo con -er, no con more. «Más viejo» invita al error.",
  },
  {
    level: "A2",
    prompt: "Expresar gustos",
    sentence: "I like ___ football.",
    options: ["play", "playing", "to playing"],
    correct: 1,
    why: "Tras like va gerundio. En español usamos infinitivo («me gusta jugar»), de ahí el error.",
  },
  {
    level: "B1",
    prompt: "Un momento pasado concreto",
    sentence: "I ___ to Paris last year.",
    options: ["have gone", "went", "have been going"],
    correct: 1,
    why: "Con un marcador temporal cerrado (last year) va pasado simple. El pretérito perfecto español tiene distribución distinta y provoca este error constantemente.",
  },
  {
    level: "B1",
    prompt: "Duración",
    sentence: "I've lived here ___ five years.",
    options: ["since", "for", "during"],
    correct: 1,
    why: "for + periodo de tiempo; since + momento de inicio. «Desde» y «hace» no mapean uno a uno con since/for.",
  },
  {
    level: "B2",
    prompt: "Falso amigo clásico",
    sentence: "___, I'm not a doctor — I'm a nurse.",
    options: ["Actually", "Currently", "Nowadays"],
    correct: 0,
    why: "Actually significa «en realidad», no «actualmente». Para «actualmente» se usa currently.",
  },
  {
    level: "B2",
    prompt: "Preposición + verbo",
    sentence: "I'm looking forward to ___ you next week.",
    options: ["see", "seeing", "have seen"],
    correct: 1,
    why: "Aquí «to» es preposición, no infinitivo: exige gerundio. Es una trampa incluso en niveles altos.",
  },
  {
    level: "C1",
    prompt: "Estructura marcada (inversión)",
    sentence: "___ had I arrived when the phone rang.",
    options: ["No sooner", "Not sooner", "Hardly than"],
    correct: 0,
    why: "«No sooner... than» con inversión del auxiliar. Estructuras enfáticas como esta separan un B2 sólido de un C1.",
  },
]

// Umbrales sobre 12 aciertos. C2 no se asigna a propósito: un test de
// opción múltiple no puede distinguir maestría, y prometerlo sería falso.
const LEVEL_BANDS = [
  { min: 11, code: "C1", name: "Dominio operativo eficaz", blurb: "Manejas estructuras marcadas y matices que la mayoría no domina." },
  { min: 9, code: "B2", name: "Avanzado", blurb: "Te desenvuelves con soltura; te falta pulir precisión y registro." },
  { min: 6, code: "B1", name: "Umbral", blurb: "Sostienes conversación; los tiempos verbales aún te juegan malas pasadas." },
  { min: 3, code: "A2", name: "Plataforma", blurb: "Base sólida para intercambios cotidianos, con estructuras por afianzar." },
  { min: 0, code: "A1", name: "Acceso", blurb: "Empezamos por lo esencial: presentarte, tu rutina, tu entorno." },
]

export default function PlacementTest({ onClose }: { onClose: () => void }) {
  const [current, setCurrent] = useState(0)
  const [answers, setAnswers] = useState<number[]>([])

  const finished = answers.length === QUESTIONS.length
  const score = answers.filter((a, i) => a === QUESTIONS[i].correct).length
  const band = LEVEL_BANDS.find((b) => score >= b.min) ?? LEVEL_BANDS[LEVEL_BANDS.length - 1]
  const missed = QUESTIONS.filter((q, i) => answers[i] !== undefined && answers[i] !== q.correct)

  function answer(index: number) {
    setAnswers((prev) => [...prev, index])
    setCurrent((prev) => prev + 1)
  }

  function restart() {
    setAnswers([])
    setCurrent(0)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-white">
      <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-5 py-6 sm:px-8">
        <header className="flex items-center justify-between gap-4">
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Cerrar prueba"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
            {finished ? "Tu resultado" : "Prueba de nivel"}
          </p>
          <span className="w-9" />
        </header>

        {!finished && (
          <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-300"
              style={{ width: `${(current / QUESTIONS.length) * 100}%` }}
            />
          </div>
        )}

        {!finished ? (
          <div className="flex flex-1 flex-col justify-center py-10">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Pregunta {current + 1} de {QUESTIONS.length}
            </span>
            <p className="mt-4 text-sm text-slate-500">{QUESTIONS[current].prompt}</p>
            <h2 className="mt-2 text-2xl font-extrabold text-slate-900 sm:text-3xl">
              {QUESTIONS[current].sentence}
            </h2>

            <div className="mt-8 space-y-3">
              {QUESTIONS[current].options.map((option, i) => (
                <button
                  key={option}
                  onClick={() => answer(i)}
                  className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-5 py-4 text-left font-medium text-slate-800 shadow-sm transition active:scale-[0.99] hover:border-blue-400 hover:bg-blue-50"
                >
                  {option}
                  <FontAwesomeIcon icon={faArrowRight} className="text-xs text-slate-300" />
                </button>
              ))}
            </div>

            <p className="mt-8 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
              💡 Si no sabes una, elige la que te suene mejor. Queremos tu punto de partida real, no tu mejor cara.
            </p>
          </div>
        ) : (
          <div className="flex-1 py-8">
            <div className="rounded-3xl bg-gradient-to-br from-blue-600 to-blue-500 p-8 text-center text-white">
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-100">Nivel orientativo</p>
              <p className="mt-2 text-6xl font-extrabold">{band.code}</p>
              <p className="mt-1 text-lg font-semibold">{band.name}</p>
              <p className="mx-auto mt-3 max-w-sm text-sm text-blue-100">{band.blurb}</p>
              <p className="mt-5 inline-block rounded-full bg-white/15 px-4 py-1.5 text-sm font-semibold">
                {score} de {QUESTIONS.length} correctas
              </p>
            </div>

            {missed.length > 0 && (
              <div className="mt-8">
                <h3 className="text-lg font-bold text-slate-900">Lo que fallaste, explicado</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Así es exactamente como corrige tu tutor: no solo qué está mal, sino por qué tu español te llevó ahí.
                </p>
                <div className="mt-4 space-y-3">
                  {missed.map((q) => (
                    <div key={q.sentence} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-600">
                          {q.level}
                        </span>
                        <span className="font-mono text-slate-700">{q.sentence.replace("___", "…")}</span>
                        <span className="font-mono font-semibold text-emerald-600">
                          <FontAwesomeIcon icon={faCircleCheck} className="mr-1" />
                          {q.options[q.correct]}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-500">{q.why}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {missed.length === 0 && (
              <p className="mt-6 flex items-center gap-2 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                <FontAwesomeIcon icon={faCircleCheck} /> Sin fallos. Impresionante — el tutor te llevará directo a matices
                de registro y naturalidad.
              </p>
            )}

            <div className="mt-8 space-y-3">
              <Link
                to="/login?mode=register"
                className="flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-6 py-4 font-semibold text-white shadow-sm transition active:scale-[0.98] hover:bg-blue-500"
              >
                Empezar en {band.code} por $10/mes
                <FontAwesomeIcon icon={faArrowRight} />
              </Link>
              <button
                onClick={restart}
                className="w-full rounded-full px-6 py-3 text-sm font-semibold text-slate-500 transition hover:bg-slate-100"
              >
                Repetir la prueba
              </button>
            </div>

            <p className="mt-6 flex items-start gap-2 text-xs text-slate-400">
              <FontAwesomeIcon icon={faCircleXmark} className="mt-0.5 shrink-0" />
              Resultado orientativo: 12 preguntas dan una foto rápida, no una certificación. Tu nivel real se confirma
              con evidencia acumulada dentro de la plataforma.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
