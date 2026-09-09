import { faCheck, faCopy } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"

/** Un dato bancario con su botón de copiar.
 *
 * El botón no es un adorno: el alumno está tecleando una cédula y un
 * teléfono en la app de su banco, y un dígito mal escrito manda el dinero
 * a otra persona. Copiar y pegar es la diferencia entre un pago que se
 * verifica y uno que hay que rastrear a mano.
 */
export default function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      // Vuelve al icono normal solo: dejar el check para siempre haría
      // creer que ya se copió cuando el alumno vuelva más tarde.
      setTimeout(() => setCopied(false), 1800)
    } catch {
      // El portapapeles falla sin permiso o fuera de HTTPS. No se avisa
      // con un error: el dato está a la vista y se puede copiar a mano.
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</p>
        <p className="truncate font-semibold text-slate-800">{value}</p>
      </div>
      <button
        onClick={copy}
        aria-label={`Copiar ${label}`}
        className={`shrink-0 rounded-lg p-2 transition ${copied ? "text-emerald-500" : "text-slate-400 hover:bg-white hover:text-slate-600"}`}
      >
        <FontAwesomeIcon icon={copied ? faCheck : faCopy} />
      </button>
    </div>
  )
}
