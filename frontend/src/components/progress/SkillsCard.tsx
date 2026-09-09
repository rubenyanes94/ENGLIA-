import { faBookOpen, faHeadphones, faMicrophone, faPen } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core"
import type { SkillBreakdown } from "../../api/types"

/** Las cuatro destrezas del MCER con su barra.
 *
 * El orden NO es alfabético ni por puntuación: es
 * listening → speaking → reading → writing, el orden canónico del marco y
 * también el orden en que se adquieren. Ordenarlas por nota dejaría al
 * alumno viendo cada semana una lista distinta, cuando lo que se busca es
 * que reconozca de un vistazo cuál lleva floja.
 */
const DESTREZAS: { key: string; label: string; icon: IconDefinition }[] = [
  { key: "listening", label: "Listening", icon: faHeadphones },
  { key: "speaking", label: "Speaking", icon: faMicrophone },
  { key: "reading", label: "Reading", icon: faBookOpen },
  { key: "writing", label: "Writing", icon: faPen },
]

export default function SkillsCard({ data }: { data: SkillBreakdown }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-extrabold text-slate-900">Habilidades CEFR</h2>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-blue-600">
          Promedio: {Math.round(data.average)}%
        </span>
      </div>

      <div className="mt-5 space-y-4">
        {DESTREZAS.map(({ key, label, icon }) => {
          const value = Math.round(data.skills[key] ?? 0)
          return (
            <div key={key}>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 font-semibold text-slate-700">
                  <FontAwesomeIcon icon={icon} className="w-4 text-blue-500" />
                  {label}
                </span>
                <span className="font-bold text-blue-600">{value}%</span>
              </div>
              <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-blue-600 transition-[width] duration-700"
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {data.average === 0 && (
        // Se explica por qué está a cero en vez de dejar cuatro barras
        // vacías: sin esto parece un error de la app, no un alumno que
        // todavía no ha practicado.
        <p className="mt-5 text-xs text-slate-400">
          Estas barras se llenan conforme practicas con el tutor y completas ejercicios.
        </p>
      )}
    </section>
  )
}
