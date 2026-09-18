import { useEffect, useRef, useState } from "react"

/** Ancho real del contenedor, vivo: los gráficos SVG se dibujan a ese
 * ancho en vez de escalarse con viewBox, para que el texto de los ejes
 * mida siempre lo mismo en un móvil que en un monitor de 27". */
export function useElementWidth<T extends HTMLElement>(initial = 600) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(initial)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width)
      if (w > 0) setWidth(w)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return [ref, width] as const
}
