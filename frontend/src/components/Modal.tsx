import { useEffect } from "react"

/** Diálogo centrado con fondo oscurecido, compartido por los modales de
 * facturación y el examen de módulo. */
export default function Modal({
  onClose,
  children,
  wide = false,
  dismissible = true,
}: {
  onClose: () => void
  children: React.ReactNode
  /** Más ancho, para contenido que no cabe en una tarjeta estrecha (examen). */
  wide?: boolean
  /** Si Escape y el clic en el fondo cierran el diálogo. Se desactiva
   * mientras hay trabajo sin guardar: un clic despistado fuera del examen
   * tiraría todas las respuestas marcadas. */
  dismissible?: boolean
}) {
  useEffect(() => {
    // El fondo no scrollea mientras el diálogo está abierto — si no, en
    // móvil el dedo mueve la página de detrás y el modal parece colgado.
    const onKey = (e: KeyboardEvent) => dismissible && e.key === "Escape" && onClose()
    document.addEventListener("keydown", onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", onKey)
      document.body.style.overflow = previous
    }
  }, [onClose, dismissible])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
      onClick={() => dismissible && onClose()}
      role="dialog"
      aria-modal="true"
    >
      <div
        // stopPropagation: sin esto, un clic dentro del diálogo burbujea
        // al fondo y lo cierra en mitad de escribir.
        onClick={(e) => e.stopPropagation()}
        className={`max-h-[92vh] w-full overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl ${wide ? "max-w-xl sm:p-8" : "max-w-sm"}`}
      >
        {children}
      </div>
    </div>
  )
}
