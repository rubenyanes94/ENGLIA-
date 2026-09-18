"""Respuestas del panel de gerencia → Sistema (routers/monitoring.py)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CheckOut(BaseModel):
    key: str
    label: str
    status: Literal["ok", "warning", "critical", "unknown"]
    detail: str
    latency_ms: int | None = None
    hint: str | None = None


class AlertOut(BaseModel):
    severity: Literal["warning", "critical"]
    title: str
    detail: str
    hint: str | None = None
    source: str


class ActiveConfig(BaseModel):
    """Lo que ESTE proceso está usando de verdad (no lo que dice el .env):
    justo lo que no cuadraba cuando el contenedor arrastraba variables viejas."""

    llm_host: str
    llm_model: str
    embedding_model: str
    moderation_model: str
    pronunciation_model: str
    tts_provider: str
    llm_max_concurrency: int
    llm_max_retries: int
    api_key_configured: bool
    environment: str


class StatusOut(BaseModel):
    checked_at: datetime
    overall: Literal["ok", "warning", "critical"]
    checks: list[CheckOut]
    alerts: list[AlertOut]
    config: ActiveConfig


class LLMSummary(BaseModel):
    attempts: int
    calls: int
    failed_calls: int
    retried_calls: int
    failed_attempts: int
    input_tokens: int
    output_tokens: int
    truncated: int
    chat_ok: int
    chat_p50_ms: float | None
    chat_p95_ms: float | None
    tutor_p50_ms: float | None
    tutor_p95_ms: float | None
    queue_p95_ms: float | None
    tts_chars: int


class LLMPoint(BaseModel):
    bucket: datetime
    attempts: int
    errors: int
    input_tokens: int
    output_tokens: int
    p50_ms: float | None
    p95_ms: float | None


class LLMByPurpose(BaseModel):
    purpose: str
    operation: str
    attempts: int
    calls: int
    errors: int
    p50_ms: float | None
    p95_ms: float | None
    avg_input_tokens: float | None
    avg_output_tokens: float | None
    total_tokens: int
    truncated: int


class LLMByModel(BaseModel):
    model: str
    operation: str
    attempts: int
    errors: int
    p50_ms: float | None
    p95_ms: float | None
    input_tokens: int
    output_tokens: int


class HTTPSummary(BaseModel):
    requests: int
    server_errors: int
    client_errors: int
    p50_ms: float | None
    p95_ms: float | None


class HTTPPoint(BaseModel):
    bucket: datetime
    requests: int
    server_errors: int
    p95_ms: float | None


class RouteStats(BaseModel):
    method: str
    route: str
    requests: int
    server_errors: int
    client_errors: int
    p50_ms: float | None
    p95_ms: float | None
    max_ms: int


class Failure(BaseModel):
    at: datetime  # la ocurrencia más reciente
    first_at: datetime
    occurrences: int
    source: Literal["llm", "http", "client"]
    title: str
    message: str
    detail: str | None


class MetricsOut(BaseModel):
    hours: int
    start: datetime
    end: datetime
    bucket_minutes: int
    llm: LLMSummary
    llm_series: list[LLMPoint]
    llm_by_purpose: list[LLMByPurpose]
    llm_by_model: list[LLMByModel]
    http: HTTPSummary
    http_series: list[HTTPPoint]
    routes: list[RouteStats]
    client_errors: int
    failures: list[Failure]


class ClientErrorIn(BaseModel):
    """Lo que manda el navegador. Todo con tope de longitud: es un
    endpoint público y no puede servir para meter megas en la BD."""

    kind: Literal["error", "unhandledrejection"]
    message: str = Field(max_length=1000)
    source: str | None = Field(None, max_length=300)
    path: str | None = Field(None, max_length=300)
    stack: str | None = Field(None, max_length=4000)
    in_app: bool = True
