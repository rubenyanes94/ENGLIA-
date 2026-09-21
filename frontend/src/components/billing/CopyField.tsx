import { faCheck, faCopy } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useState } from "react"

/** Un dato para pegar en la app del banco, que se copia con UN clic en
 * cualquier parte de la caja (no solo en el icono: en un móvil, acertarle
 * a un icono de 16 px es un segundo intento).
 *
 * No es un adorno: el alumno está tecleando un RIF y un teléfono en su
 * banco, y un dígito mal escrito manda el dinero a otra persona. Copiar y
 * pegar es la diferencia entre un pago que se verifica y uno que hay que
 * rastrear a mano.
 *
 * `copyValue` permite copiar algo distinto de lo que se ve: el monto se
 * muestra "8.495,64" (legible) pero se copia "8495,64", sin el punto de
 * miles que algunas apps de banco rechazan al pegar. */
export default function CopyField({ label, value, copyValue }: { label: string; value: string; copyValue?: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    // "Copiado" solo si se copió de verdad: decirlo sin haberlo hecho es
    // peor que no decir nada (el alumno pegaría lo que tuviera antes).
    if (await copyToClipboard(copyValue ?? value)) {
      setCopied(true)
      // Vuelve al estado normal solo: dejar el check para siempre haría
      // creer que ya se copió cuando el alumno vuelva más tarde.
      setTimeout(() => setCopied(false), 1800)
    }
  }

  return (
    // Fondo blanco con borde y no gris: el mismo campo vive en el modal
    // (fondo blanco) y en el registro (fondo gris), y en gris sobre gris
    // no se veía dónde empezaba cada dato.
    <button
      type="button"
      onClick={copy}
      aria-label={`Copiar ${label}: ${value}`}
      className={`flex w-full items-center gap-3 rounded-2xl bg-white px-4 py-3 text-left ring-1 transition active:scale-[0.99] ${
        copied ? "ring-emerald-400" : "ring-slate-200 hover:ring-brand-300"
      }`}
    >
      <span className="min-w-0 flex-1">
        <span className="block text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</span>
        {/* Que pase a otra línea, no que se corte: "Banco Nacional de
            Crédito (0…" escondía justo el código del banco. */}
        <span className="block break-words font-semibold text-slate-800">{value}</span>
      </span>
      <span
        aria-live="polite"
        className={`flex shrink-0 items-center gap-1.5 text-xs font-semibold ${copied ? "text-emerald-600" : "text-slate-400"}`}
      >
        <FontAwesomeIcon icon={copied ? faCheck : faCopy} />
        {copied ? "Copiado" : "Copiar"}
      </span>
    </button>
  )
}

/** Copia `text` y dice si lo consiguió.
 *
 * navigator.clipboard solo existe en contextos seguros (HTTPS o localhost):
 * servida por HTTP normal, la API ni siquiera está y el botón fallaba en
 * silencio. El respaldo — seleccionar un <textarea> oculto y
 * execCommand("copy") — está obsoleto pero funciona en todos los
 * navegadores y contextos, que para un dato bancario es lo que importa. */
async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Sin permiso: se intenta con el respaldo.
    }
  }
  const area = document.createElement("textarea")
  area.value = text
  area.setAttribute("readonly", "")
  area.style.position = "fixed"
  area.style.opacity = "0"
  document.body.appendChild(area)
  area.select()
  try {
    return document.execCommand("copy")
  } catch {
    return false
  } finally {
    document.body.removeChild(area)
  }
}

