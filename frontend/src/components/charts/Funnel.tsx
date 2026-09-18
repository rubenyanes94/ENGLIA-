import { faArrowDownLong } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { int, pct } from "./format"
import { ORDINAL } from "./tokens"

export interface FunnelStageView {
  key: string
  label: string
  description: string
  customers: number
}

/** Embudo de etapas anidadas. Etapas ORDENADAS, así que van en una rampa
 * de un solo tono (oscuro → claro) validada como ordinal: el color dice
 * "en qué punto del recorrido", no "qué categoría".
 *
 * Entre etapas se rotula la conversión de paso ("pasa el 78 %"): es la
 * cifra que dice dónde se pierde la gente, más útil que el % sobre el total. */
export default function Funnel({ stages }: { stages: FunnelStageView[] }) {
  const top = stages[0]?.customers ?? 0

  if (!top) return <p className="py-8 text-center text-sm text-slate-400">Nadie se registró en este periodo.</p>

  return (
    <ol className="space-y-1">
      {stages.map((stage, i) => {
        const share = top ? stage.customers / top : 0
        const prev = i > 0 ? stages[i - 1].customers : null
        const step = prev ? stage.customers / prev : null
        return (
          <li key={stage.key}>
            {step != null && (
              <p className="flex items-center gap-2 py-1.5 pl-1 text-xs text-slate-500">
                <FontAwesomeIcon icon={faArrowDownLong} className="text-slate-300" />
                Pasa el <span className="font-semibold text-slate-700">{pct(step)}</span>
                <span className="text-slate-400">· se quedan {int((prev ?? 0) - stage.customers)}</span>
              </p>
            )}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
              <div className="sm:w-48 sm:shrink-0">
                <p className="text-sm font-semibold text-slate-900">
                  <span className="mr-1.5 text-slate-400">{i + 1}.</span>
                  {stage.label}
                </p>
                <p className="text-xs leading-snug text-slate-500">{stage.description}</p>
              </div>
              <div className="flex flex-1 items-center gap-3">
                <div className="h-6 flex-1">
                  <div
                    className="h-full rounded-r"
                    style={{ width: `${Math.max(share * 100, stage.customers > 0 ? 1 : 0)}%`, background: ORDINAL[i] ?? ORDINAL[ORDINAL.length - 1] }}
                    title={`${stage.label}: ${int(stage.customers)}`}
                  />
                </div>
                <div className="w-24 shrink-0 text-right">
                  <p className="text-sm font-bold tabular-nums text-slate-900">{int(stage.customers)}</p>
                  <p className="text-xs tabular-nums text-slate-500">{pct(share)}</p>
                </div>
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
