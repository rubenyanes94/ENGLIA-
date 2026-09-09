import { useEffect } from "react"

/** Diálogo centrado con fondo oscurecido, común a todos los modales de
 * facturación. Existe como pieza aparte porque son cinco pantallas
 * encadenadas y repetir el andamiaje en cada una haría que se separaran
 * solas con el tiempo. */
export default function Modal({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    // Escape cierra, y el fondo no scrollea mientras el diálogo está
    // abierto — si no, en móvil el dedo mueve la página de detrás y el
    // modal parece colgado.
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    document.addEventListener("keydown", onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", onKey)
      document.body.style.overflow = previous
    }
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        // stopPropagation: sin esto, un clic dentro del diálogo burbujea
        // al fondo y lo cierra en mitad de escribir.
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-2xl"
      >
        {children}
      </div>
    </div>
  )
}
