/** Evento de ventana: la cola de pagos cambió (se aprobó o rechazó uno).
 * Lo escucha el layout para refrescar el contador de la pestaña "Pagos"
 * sin esperar al siguiente refresco automático. En su propio módulo para
 * que el layout no tenga que importar la página (que se carga aparte). */
export const PAYMENTS_CHANGED = "espikin:payments-changed"
