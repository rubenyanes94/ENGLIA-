/** Tipos del panel de gerencia → Sistema: espejo de backend/app/schemas/monitoring.py.
 * Tiempos en milisegundos; fechas en hora local del negocio, sin zona. */

export type CheckStatus = "ok" | "warning" | "critical" | "unknown"
export type WindowHours = 1 | 24 | 168 | 720

export interface Check {
  key: string
  label: string
  status: CheckStatus
  detail: string
  latency_ms: number | null
  hint: string | null
}

export interface Alert {
  severity: "warning" | "critical"
  title: string
  detail: string
  hint: string | null
  source: string
}

export interface MonitoringStatus {
  checked_at: string
  overall: "ok" | "warning" | "critical"
  checks: Check[]
  alerts: Alert[]
  config: {
    llm_host: string
    llm_model: string
    embedding_model: string
    moderation_model: string
    pronunciation_model: string
    tts_provider: string
    llm_max_concurrency: number
    llm_max_retries: number
    api_key_configured: boolean
    environment: string
  }
}

export interface MonitoringMetrics {
  hours: WindowHours
  start: string
  end: string
  bucket_minutes: number
  llm: {
    attempts: number
    calls: number
    failed_calls: number
    retried_calls: number
    failed_attempts: number
    input_tokens: number
    output_tokens: number
    truncated: number
    chat_ok: number
    chat_p50_ms: number | null
    chat_p95_ms: number | null
    tutor_p50_ms: number | null
    tutor_p95_ms: number | null
    queue_p95_ms: number | null
    tts_chars: number
  }
  llm_series: {
    bucket: string
    attempts: number
    errors: number
    input_tokens: number
    output_tokens: number
    p50_ms: number | null
    p95_ms: number | null
  }[]
  llm_by_purpose: {
    purpose: string
    operation: string
    attempts: number
    calls: number
    errors: number
    p50_ms: number | null
    p95_ms: number | null
    avg_input_tokens: number | null
    avg_output_tokens: number | null
    total_tokens: number
    truncated: number
  }[]
  llm_by_model: {
    model: string
    operation: string
    attempts: number
    errors: number
    p50_ms: number | null
    p95_ms: number | null
    input_tokens: number
    output_tokens: number
  }[]
  http: { requests: number; server_errors: number; client_errors: number; p50_ms: number | null; p95_ms: number | null }
  http_series: { bucket: string; requests: number; server_errors: number; p95_ms: number | null }[]
  routes: {
    method: string
    route: string
    requests: number
    server_errors: number
    client_errors: number
    p50_ms: number | null
    p95_ms: number | null
    max_ms: number
  }[]
  client_errors: number
  /** Agrupados por fallo idéntico: `at` es la última vez, `first_at` la primera. */
  failures: {
    at: string
    first_at: string
    occurrences: number
    source: "llm" | "http" | "client"
    title: string
    message: string
    detail: string | null
  }[]
}
