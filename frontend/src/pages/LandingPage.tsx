import { faArrowRight, faRocket } from "@fortawesome/free-solid-svg-icons"
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
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="mx-auto flex max-w-lg items-center justify-between px-5 py-4">
        <span className="flex items-center gap-2 font-bold">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm text-white">EA</span>
          English Academy
        </span>
        <Link to="/login" className="text-sm font-semibold text-blue-600">
          Ingresar
        </Link>
      </header>

      <main className="mx-auto max-w-lg px-5 pb-16">
        <section className="pt-6 text-center">
          <h1 className="text-4xl font-extrabold leading-tight text-slate-900">
            A1 a C2 <span className="text-blue-600">con tutores de IA</span>
          </h1>
          <p className="mx-auto mt-3 max-w-sm text-slate-500">
            Aprende inglés con agentes de IA que corrigen tus errores según cómo hablan realmente los
            hispanohablantes, siguiendo el Marco Común Europeo de Referencia.
          </p>
        </section>

        <section className="mt-10">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Ruta de certificación</h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {(levels.length > 0 ? levels : PLACEHOLDER_LEVELS).map((level) => (
              <div key={level.code} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <span className="text-lg font-extrabold text-blue-600">{level.code}</span>
                <h3 className="mt-1 font-semibold text-slate-900">{level.name}</h3>
                <p className="mt-1 text-xs text-slate-500">{level.description.split(".")[0]}.</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10 space-y-3">
          <Link
            to="/login?mode=register"
            className="flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 px-6 py-3.5 font-semibold text-white shadow-sm transition hover:bg-blue-500"
          >
            <FontAwesomeIcon icon={faRocket} />
            Comenzar ahora
          </Link>
          <Link
            to="/login"
            className="flex w-full items-center justify-center gap-2 rounded-full bg-slate-900 px-6 py-3.5 font-semibold text-white transition hover:bg-slate-800"
          >
            Ingresar
            <FontAwesomeIcon icon={faArrowRight} />
          </Link>
        </section>

        <p className="mt-10 text-center text-xs text-slate-400">English Academy © 2026</p>
      </main>
    </div>
  )
}

// Solo se usa si /levels no responde (ej. backend recién arrancando) —
// para que la landing nunca se vea vacía. Nombres/descripciones tomados
// del propio seed_cefr_levels.py, no inventados.
const PLACEHOLDER_LEVELS: CEFRLevel[] = [
  { id: "a1", code: "A1", name: "Acceso", order: 1, description: "Frases básicas y supervivencia.", target_hours_min: 90, target_hours_max: 100 },
  { id: "a2", code: "A2", name: "Plataforma", order: 2, description: "Intercambio directo de información.", target_hours_min: 90, target_hours_max: 110 },
  { id: "b1", code: "B1", name: "Umbral", order: 3, description: "Autonomía en viajes y situaciones cotidianas.", target_hours_min: 150, target_hours_max: 180 },
  { id: "b2", code: "B2", name: "Avanzado", order: 4, description: "Entendimiento de ideas complejas.", target_hours_min: 180, target_hours_max: 200 },
  { id: "c1", code: "C1", name: "Dominio", order: 5, description: "Uso flexible para fines sociales.", target_hours_min: 200, target_hours_max: 220 },
  { id: "c2", code: "C2", name: "Maestría", order: 6, description: "Comprensión total con facilidad.", target_hours_min: 250, target_hours_max: 300 },
]
