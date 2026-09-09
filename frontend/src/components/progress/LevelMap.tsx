import { faCircleCheck, faLock } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import type { CEFRLevel } from "../../api/types"

/** El camino MCER completo, de C2 arriba a A1 abajo.
 *
 * De arriba abajo y no al revés a propósito: así lo que queda POR
 * conquistar aparece por encima del alumno y lo ya logrado le sostiene
 * desde abajo. Leído en orden natural, la página cuenta "hasta dónde
 * puedes llegar" antes que "dónde estás", que es lo que sostiene a
 * alguien en un plan de dos años.
 *
 * Los tres estados salen de datos reales, no de una lista escrita a
 * mano: certificar un nivel mueve `current_level_id` al siguiente (ver
 * services/certification.certify), así que el nivel actual del alumno
 * parte la escalera en dos — lo de abajo está superado, lo de arriba
 * bloqueado.
 */
export default function LevelMap({
  levels,
  currentLevelCode,
  hoursRemaining,
}: {
  levels: CEFRLevel[]
  currentLevelCode: string
  /** Horas que faltan para el mínimo del nivel actual, si se sabe. */
  hoursRemaining?: number | null
}) {
  const currentOrder = levels.find((l) => l.code === currentLevelCode)?.order ?? 1
  const descending = [...levels].sort((a, b) => b.order - a.order)

  return (
    <section>
      <h2 className="flex items-center gap-2 text-lg font-extrabold text-slate-900">
        <span aria-hidden>🗺️</span> Mapa de Progreso MCER
      </h2>

      <ol className="relative mt-4">
        {descending.map((level, index) => {
          const done = level.order < currentOrder
          const current = level.order === currentOrder
          const isLast = index === descending.length - 1

          return (
            <li key={level.code} className="relative flex gap-4 pb-6 last:pb-0">
              {/* Raíl vertical. Se pinta azul solo en el tramo ya
                  recorrido: la línea misma es la barra de progreso, sin
                  necesidad de una segunda. */}
              {!isLast && (
                <span
                  aria-hidden
                  className={`absolute left-[9px] top-6 h-full w-0.5 ${done ? "bg-blue-600" : "bg-slate-200"}`}
                />
              )}

              <span
                aria-hidden
                className={`relative z-10 mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                  done
                    ? "border-blue-600 bg-blue-600"
                    : current
                      ? "border-blue-600 bg-white"
                      : "border-slate-200 bg-white"
                }`}
              >
                {current && <span className="h-2 w-2 rounded-full bg-blue-600" />}
              </span>

              <div
                className={`min-w-0 flex-1 ${
                  current ? "rounded-2xl border border-blue-100 bg-blue-50/60 p-4" : "pt-0.5"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <h3
                    className={`font-bold ${
                      current ? "text-blue-700" : done ? "text-slate-900" : "text-slate-300"
                    }`}
                  >
                    {level.code} — {level.name}
                  </h3>
                  {current ? (
                    <span className="shrink-0 rounded-full bg-blue-600 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                      Meta
                    </span>
                  ) : done ? (
                    <FontAwesomeIcon icon={faCircleCheck} className="shrink-0 text-blue-600" />
                  ) : (
                    <FontAwesomeIcon icon={faLock} className="shrink-0 text-xs text-slate-300" />
                  )}
                </div>

                <p className={`mt-1 text-sm ${current ? "text-blue-600/80" : done ? "text-slate-500" : "text-slate-300"}`}>
                  {level.description}
                </p>

                {/* Solo en el nivel actual, y solo si el dato existe: un
                    "faltan 0 horas" en cada peldaño sería ruido, y una
                    cifra inventada sería peor. */}
                {current && hoursRemaining != null && hoursRemaining > 0 && (
                  <p className="mt-2 text-xs font-semibold text-orange-500">
                    Te faltan {Math.ceil(hoursRemaining)} h de práctica para completarlo
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
