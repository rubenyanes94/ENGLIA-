// Tipos que reflejan 1:1 los schemas Pydantic del backend (app/schemas/*).
// Se mantienen a mano, no generados — el backend es pequeño y cambia
// despacio; para un proyecto de este tamaño, un generador de tipos desde
// el OpenAPI de FastAPI sería más ceremonia que la que ahorra hoy.

export interface CEFRLevel {
  id: string
  code: string
  name: string
  order: number
  description: string
  target_hours_min: number
  target_hours_max: number
}

export interface Module {
  id: string
  code: string | null
  title: string
  title_es: string | null
  skill_focus: string
  order: number
  estimated_hours: number
  descriptors: string[]
  communicative_objectives: string[]
}

export interface ModuleProgress extends Module {
  status: "locked" | "available" | "in_progress" | "completed"
}

export interface Task {
  id: string
  type: string
  descriptor: string
  prompt: string
  success_criteria?: string
  note?: string
}

export interface L1InterferenceItem {
  error: string
  target: string
  origin: string
  severity: "low" | "medium" | "high" | "critical"
  note?: string
}

export interface ModuleDetail extends Module {
  recycles: string[]
  grammar: { focus?: string[]; note?: string }
  lexis: { target_items?: number; sets?: string[]; chunks?: string[] }
  pronunciation: { focus?: string; l1_alerts?: string[] }
  l1_interference: L1InterferenceItem[]
  tasks: Task[]
  assessment: { evidence_required?: number; gate_descriptors?: string[]; level_exit_criteria?: string[]; note?: string }
  tutor_config: { persona?: string; correction_policy?: string; scaffolds?: string[]; forbidden?: string[]; speech_rate?: string }
  lessons: { id: string; title: string; order: number; audio_duration_seconds: number | null }[]
}

export interface CertificationProgress {
  level_code: string
  target_hours_min: number
  target_hours_max: number
  hours_completed: number
  percentage: number
  modules: ModuleProgress[]
}

export interface Descriptor {
  id: string
  code: string
  skill: string
  statement_en: string
  statement_es: string
  modules: string[]
  priority: string | null
  l1_specific: boolean
  note: string | null
  target: string | null
}

export interface DescriptorMastery {
  code: string
  skill: string
  statement_es: string
  priority: string | null
  mastery: number
  is_mastered: boolean
}

export interface DescriptorMasterySummary {
  level_code: string
  threshold: number
  total: number
  mastered: number
  percentage: number
  descriptors: DescriptorMastery[]
}

export interface ExitCriterion {
  key: string
  label: string
  met: boolean
  detail: Record<string, unknown>
}

export interface LevelExitGate {
  level_code: string
  eligible: boolean
  criteria: ExitCriterion[]
}

export interface CertificationResult {
  level_code: string
  certified: boolean
  next_level_code: string | null
  certified_at: string
}

export interface Progress {
  current_level_code: string | null
  modules: { module_id: string; module_title: string; level_code: string; status: string; mastery_score: number }[]
}

export interface User {
  id: string
  email: string
  full_name: string
  native_language: string
  current_level_id: string | null
  // URL relativa servida por el backend en /media/avatars/... — null si el
  // alumno no ha subido foto (se pinta la inicial de su nombre).
  avatar_url: string | null
}

export interface Tutor {
  name: string
  level_code: string
}

/** GET /modules/{moduleId}/lessons/{lessonId}. A diferencia del resumen
 * que trae ModuleDetail.lessons, este SÍ incluye el audio y el guión —
 * por eso el reproductor necesita pedirlo aparte. */
export interface LessonDetail {
  id: string
  title: string
  order: number
  content: Record<string, unknown>
  script: string | null
  audio_url: string | null
  audio_duration_seconds: number | null
}

// --- Chat ---

export interface CreateSessionResponse {
  session_id: string
  persona_name: string
  level_code: string
  module_title: string | null
}

export interface Correction {
  error: string
  correction: string
  rule: string
}

export interface SendMessageResponse {
  session_id: string
  reply: string
  persona_name: string
  corrections: Correction[]
  task_completed: boolean | null
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  created_at: string
  corrections: Correction[] | null
}

// --- Errores de la API ---
// El backend devuelve `detail` como string en la mayoría de errores, pero
// como objeto estructurado en el 409 de certificación (ver
// routers/users.py, certify_level) — este tipo cubre ambos casos.
export interface ApiErrorDetail {
  message?: string
  eligible?: boolean
  criteria?: ExitCriterion[]
}

export class ApiError extends Error {
  status: number
  detail: string | ApiErrorDetail

  constructor(status: number, detail: string | ApiErrorDetail) {
    super(typeof detail === "string" ? detail : detail.message ?? "Error de la API")
    this.status = status
    this.detail = detail
  }
}
