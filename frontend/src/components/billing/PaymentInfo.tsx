import type { ReactNode } from "react"
import type { Plan } from "../../api/types"
import { money } from "../charts/format"

/** Piezas comunes a las cuatro pantallas de pago: el precio y los pasos.
 * En su propio módulo (no en BillingModal) porque las usan las pantallas y
 * el registro, y BillingModal importa las pantallas: evita un ciclo. */

export function planPrice(plan: Plan): string {
  return money(plan.price_cents)
}

export function planPeriod(plan: Plan): string {
  return plan.interval === "year" ? "año" : "mes"
}

/** Precio y condiciones en una línea: cuánto, cada cuánto y si se
 * renueva solo. No en grande: el precio ya se ve en la tarjeta del plan, y
 * aquí lo que el alumno necesita es saber qué implica ESTE método. */
export function PriceTag({ plan, note }: { plan: Plan; note: string }) {
  return (
    <p className="mt-4 rounded-2xl bg-brand-50 px-4 py-3 text-center text-sm text-slate-600">
      <strong className="text-slate-900">
        {planPrice(plan)} USD al {planPeriod(plan)}
      </strong>{" "}
      · {note}
    </p>
  )
}

/** Qué va a pasar, paso a paso. Lo que evita el "¿y ahora qué?" a mitad
 * de un pago, que es cuando más gente abandona. */
export function Steps({ items }: { items: ReactNode[] }) {
  return (
    <ol className="mt-4 space-y-2.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3 text-sm leading-relaxed text-slate-600">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500">
            {i + 1}
          </span>
          <span className="pt-0.5">{item}</span>
        </li>
      ))}
    </ol>
  )
}
