import {
  faCircleCheck,
  faCircleExclamation,
  faCircleMinus,
  faCircleQuestion,
  faCircleXmark,
  faSeedling,
  faTriangleExclamation,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons"
import type { FunnelKey, Segment } from "../../api/management"
import { STATUS } from "../charts/tokens"

/** Textos del panel en un solo sitio: la misma clave del backend se lee
 * igual en una tarjeta, en un gráfico y en su tabla. */

export const FEATURE_LABELS: Record<string, { label: string; unit: string }> = {
  tutor: { label: "Conversación con el tutor", unit: "mensajes" },
  library: { label: "Biblioteca (cursos flash)", unit: "mensajes" },
  exam: { label: "Exámenes de módulo", unit: "respuestas" },
  exercise: { label: "Ejercicios de práctica", unit: "respuestas" },
  sentence_game: { label: "Juego de oraciones", unit: "partidas" },
  app: { label: "Abrieron la app", unit: "pantallas vistas" },
  milestone: { label: "Hitos (inscripciones y logros)", unit: "hitos" },
}

export const SCREEN_LABELS: Record<string, string> = {
  "/dashboard": "Inicio",
  "/classroom": "Classroom",
  "/chat": "Tutor",
  "/progress": "Progreso",
  "/library": "Biblioteca",
  "/library/:slug": "Curso de la biblioteca",
  "/modules/:id": "Módulo",
  "/profile": "Perfil",
}

export const FUNNEL_LABELS: Record<FunnelKey, { label: string; description: string }> = {
  registered: { label: "Se registraron", description: "Crearon su cuenta en el periodo" },
  activated: { label: "Practicaron", description: "Hablaron con el tutor o hicieron un examen" },
  engaged: { label: "Volvieron", description: "Practicaron al menos 3 días distintos" },
  achieved: { label: "Lograron algo", description: "Completaron un módulo o certificaron nivel" },
  paid: { label: "Pagaron", description: "Tienen al menos un pago aprobado" },
}

/** `label` para grupos ("Activos: 91"); `one` para la ficha de UN cliente ("Activo"). */
export const SEGMENTS: Record<Segment, { label: string; one: string; description: string; action: string; color: string; icon: IconDefinition }> = {
  new: {
    label: "Nuevos",
    one: "Nuevo",
    description: "Se registraron en los últimos 7 días",
    action: "Que practiquen en su primera semana: es cuando más se pierden.",
    color: "#6D3BE6",
    icon: faSeedling,
  },
  current: {
    label: "Activos",
    one: "Activo",
    description: "Usaron la app en los últimos 7 días",
    action: "El núcleo del negocio: cuidar que no pasen a en riesgo.",
    color: STATUS.good,
    icon: faCircleCheck,
  },
  at_risk: {
    label: "En riesgo",
    one: "En riesgo",
    description: "Su último uso fue hace 8 a 30 días",
    action: "Candidatos a un recordatorio o una campaña de reactivación.",
    color: STATUS.warning,
    icon: faTriangleExclamation,
  },
  dormant: {
    label: "Dormidos",
    one: "Dormido",
    description: "Más de 30 días sin usar la app",
    action: "Difíciles de recuperar; medir si una oferta los trae de vuelta.",
    color: STATUS.critical,
    icon: faCircleXmark,
  },
  never_active: {
    label: "Nunca practicaron",
    one: "Nunca practicó",
    description: "Registrados hace más de 7 días sin actividad",
    action: "Revisar el registro y la primera pantalla: algo los frena.",
    color: "#94a3b8",
    icon: faCircleMinus,
  },
}

export const SEGMENT_ORDER: Segment[] = ["new", "current", "at_risk", "dormant", "never_active"]

export const PROVIDER_LABELS: Record<string, string> = {
  pago_movil: "Pago Móvil",
  paypal: "PayPal",
  credit_card: "Tarjeta",
  binance_pay: "Binance Pay",
  // Pagos del botón "Reportar pago" (solo en desarrollo): $0, sin cobro real.
  test: "Prueba",
}

export const PAYMENT_STATUS: Record<string, { label: string; color: string; icon: IconDefinition }> = {
  approved: { label: "Aprobados", color: STATUS.good, icon: faCircleCheck },
  pending_verification: { label: "Por verificar", color: STATUS.warning, icon: faTriangleExclamation },
  rejected: { label: "Rechazados", color: STATUS.critical, icon: faCircleXmark },
  failed: { label: "Fallidos", color: STATUS.critical, icon: faCircleExclamation },
  refunded: { label: "Reembolsados", color: STATUS.serious, icon: faCircleMinus },
}

export const SUBSCRIPTION_LABELS: Record<string, string> = {
  active: "Activa",
  past_due: "Cobro atrasado",
  pending: "Pendiente",
  canceled: "Cancelada",
  expired: "Vencida",
  free: "Gratis",
}

export const LEVEL_LABELS: Record<string, string> = { none: "Sin nivel asignado" }

export const WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

export const TIMELINE_LABELS: Record<string, string> = {
  tutor_session: "Sesión con el tutor",
  module_enrolled: "Empezó un módulo",
  module_exam_submitted: "Presentó un examen",
  module_completed: "Completó un módulo",
  level_certified: "Certificó un nivel",
  chat_session_ended: "Cerró una sesión",
  payment: "Pago",
  subscription_canceled: "Canceló la suscripción",
}

// --- Sistema (monitoreo técnico) -------------------------------------------

/** Para qué se llamó al modelo (el `purpose` que pone ainvoke_serialized). */
export const PURPOSE_LABELS: Record<string, string> = {
  tutor_reply: "Respuesta del tutor",
  corrections: "Detección de errores",
  moderation: "Moderación de contenido",
  task_evaluation: "Evaluación de tareas",
  grading: "Calificación de respuestas",
  pronunciation: "Evaluación de pronunciación",
  session_summary: "Resumen de sesión",
  embedding: "Embeddings (memoria del tutor)",
  lesson_script: "Guion de lección",
  exam_generation: "Generación de exámenes",
  exam_verification: "Verificación de exámenes",
  lesson_audio: "Voz de las lecciones",
  other: "Otras",
}

export const OPERATION_LABELS: Record<string, string> = { chat: "Chat", embedding: "Embeddings", tts: "Voz" }

export const CHECK_STATUS: Record<string, { label: string; color: string; icon: IconDefinition }> = {
  ok: { label: "Funciona", color: STATUS.good, icon: faCircleCheck },
  warning: { label: "Aviso", color: STATUS.warning, icon: faTriangleExclamation },
  critical: { label: "Falla", color: STATUS.critical, icon: faCircleXmark },
  unknown: { label: "Sin datos", color: "#94a3b8", icon: faCircleQuestion },
}

export const FAILURE_SOURCES: Record<string, string> = {
  llm: "Modelo",
  http: "API",
  client: "Navegador",
}

/** Estado de UN pago, en singular (PAYMENT_STATUS, arriba, va en plural
 * para los totales de Ingresos). Siempre con icono: nunca solo color. */
export const PAYMENT_STATUS_ONE: Record<string, { label: string; color: string; icon: IconDefinition }> = {
  pending_verification: { label: "Por verificar", color: STATUS.warning, icon: faTriangleExclamation },
  approved: { label: "Aprobado", color: STATUS.good, icon: faCircleCheck },
  rejected: { label: "Rechazado", color: STATUS.critical, icon: faCircleXmark },
  failed: { label: "Fallido", color: STATUS.critical, icon: faCircleExclamation },
  refunded: { label: "Reembolsado", color: STATUS.serious, icon: faCircleMinus },
}


/** Los tipos de correo, con una frase de cuándo sale cada uno: la lista
 * de "Enviados" es el sitio donde alguien descubre que existe el aviso de
 * "te echamos de menos". */
export const EMAIL_KINDS: Record<string, { label: string; when: string }> = {
  bienvenida: { label: "Bienvenida", when: "Al registrarse" },
  pago_aprobado: { label: "Pago confirmado", when: "Al aprobar su pago" },
  pago_rechazado: { label: "Pago rechazado", when: "Al rechazar su pago" },
  vence_pronto: { label: "Vence pronto", when: "3 días antes de que termine su acceso" },
  ultimo_dia: { label: "Último día", when: "El último día de su acceso" },
  vencio: { label: "Se le venció", when: "El día que pierde el acceso" },
  te_echamos_de_menos: { label: "Te echamos de menos", when: "Una semana sin practicar" },
  campana: { label: "Campaña", when: "Escrita y enviada desde aquí" },
}

export const EMAIL_STATUS: Record<string, { label: string; className: string }> = {
  sent: { label: "Enviado", className: "bg-emerald-50 text-emerald-700" },
  sending: { label: "Enviando", className: "bg-slate-100 text-slate-600" },
  failed: { label: "Falló", className: "bg-rose-50 text-rose-700" },
  skipped: { label: "No se envió", className: "bg-amber-50 text-amber-800" },
}
