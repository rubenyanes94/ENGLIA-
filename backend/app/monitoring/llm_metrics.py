"""Medición de cada llamada a un modelo: latencia, tokens y errores.

Cómo llega aquí cada llamada sin tocar los puntos de llamada uno a uno:

- **Chat** (tutor, correcciones, evaluación, moderación, pronunciación,
  guiones, resúmenes): `get_llm()` engancha `LLMMetricsCallback` a cada
  cliente. LangChain lo avisa al empezar y al acabar CADA llamada al
  modelo, incluidas las de `with_structured_output`, que devuelven un
  objeto ya parseado y por fuera no dejan ver los tokens.
- **Embeddings y voz**: no pasan por un ChatOpenAI, así que se miden a
  mano con `measure_call()`.

El "para qué" (tutor_reply, corrections...) y el número de intento viajan
en ContextVars que pone `ainvoke_serialized()`: cada tarea de asyncio ve
los suyos aunque el grafo del tutor lance varias llamadas a la vez.

Registrar NUNCA puede romper una respuesta: cualquier fallo al guardar se
traga (con un aviso en el log). Perder una métrica es aceptable; que un
alumno vea un error porque falló la telemetría, no.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.db import AsyncSessionLocal
from app.models import LLMCall

logger = logging.getLogger(__name__)

_purpose: ContextVar[str] = ContextVar("llm_purpose", default="other")
_call_id: ContextVar[uuid.UUID | None] = ContextVar("llm_call_id", default=None)
_attempt: ContextVar[int] = ContextVar("llm_attempt", default=1)
_queue_ms: ContextVar[int | None] = ContextVar("llm_queue_ms", default=None)


@contextmanager
def inference_purpose(purpose: str):
    """Etiqueta las llamadas de este bloque. Para los pocos sitios que
    llaman al modelo sin pasar por ainvoke_serialized (el resumen de Celery)."""
    token = _purpose.set(purpose)
    try:
        yield
    finally:
        _purpose.reset(token)


@contextmanager
def logical_call(purpose: str):
    """Abre una llamada "lógica" (con sus posibles reintentos). Lo usa
    ainvoke_serialized: todos los intentos comparten call_id."""
    tokens = [_purpose.set(purpose), _call_id.set(uuid.uuid4()), _attempt.set(1), _queue_ms.set(None)]
    try:
        yield
    finally:
        for var, token in zip((_purpose, _call_id, _attempt, _queue_ms), tokens):
            var.reset(token)


def set_attempt(attempt: int, queue_ms: int | None) -> None:
    _attempt.set(attempt)
    _queue_ms.set(queue_ms)


def _truncate(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    return text if len(text) <= limit else text[: limit - 1] + "…"


async def record_call(**fields: Any) -> None:
    """Guarda un intento en su PROPIA sesión, nunca en la de la petición:
    un commit de telemetría no puede arrastrar ni romper la transacción
    del alumno."""
    fields.setdefault("call_id", _call_id.get() or uuid.uuid4())
    fields.setdefault("attempt", _attempt.get())
    fields.setdefault("purpose", _purpose.get())
    fields.setdefault("queue_ms", _queue_ms.get())
    fields["error_message"] = _truncate(fields.get("error_message"), 1000)
    try:
        async with AsyncSessionLocal() as session:
            session.add(LLMCall(**fields))
            await session.commit()
    except Exception:  # noqa: BLE001 — la telemetría no puede tumbar la app
        logger.warning("No se pudo registrar la llamada al modelo", exc_info=True)


def _usage(response: LLMResult) -> tuple[int | None, int | None, str | None, str | None]:
    """(tokens de entrada, de salida, modelo, finish_reason). Se prueba primero
    `usage_metadata` del mensaje (formato estándar de LangChain) y luego el
    `token_usage` crudo del proveedor, por si alguna versión solo trae uno."""
    input_tokens = output_tokens = finish_reason = None
    model = (response.llm_output or {}).get("model_name")
    try:
        generation = response.generations[0][0]
        finish_reason = (generation.generation_info or {}).get("finish_reason")
        message = getattr(generation, "message", None)
        usage = getattr(message, "usage_metadata", None)
        if usage:
            input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        meta = getattr(message, "response_metadata", None) or {}
        model = model or meta.get("model_name")
    except (IndexError, AttributeError):
        pass
    if input_tokens is None:
        raw = (response.llm_output or {}).get("token_usage") or {}
        input_tokens, output_tokens = raw.get("prompt_tokens"), raw.get("completion_tokens")
    return input_tokens, output_tokens, model, finish_reason


class LLMMetricsCallback(AsyncCallbackHandler):
    """Cronometra cada llamada de chat por su run_id y la registra al acabar.

    Asíncrono a propósito: LangChain ESPERA a los callbacks asíncronos en
    la misma tarea, así que ven las ContextVars de quien llamó (un callback
    síncrono podría ejecutarse en otro hilo y perder el "para qué")."""

    def __init__(self, default_model: str) -> None:
        self._default_model = default_model
        self._starts: dict[uuid.UUID, float] = {}

    async def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs) -> None:
        self._starts[run_id] = time.perf_counter()

    async def on_llm_start(self, serialized, prompts, *, run_id, **kwargs) -> None:
        self._starts[run_id] = time.perf_counter()

    def _elapsed(self, run_id) -> int:
        start = self._starts.pop(run_id, None)
        return int((time.perf_counter() - start) * 1000) if start is not None else 0

    async def on_llm_end(self, response: LLMResult, *, run_id, **kwargs) -> None:
        latency = self._elapsed(run_id)
        input_tokens, output_tokens, model, finish_reason = _usage(response)
        await record_call(
            operation="chat",
            model=model or self._default_model,
            status="ok",
            latency_ms=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
        )

    async def on_llm_error(self, error: BaseException, *, run_id, **kwargs) -> None:
        await record_call(
            operation="chat",
            model=self._default_model,
            status="error",
            latency_ms=self._elapsed(run_id),
            error_type=type(error).__name__,
            error_message=str(error),
        )


@asynccontextmanager
async def measure_call(*, operation: str, purpose: str, model: str, input_chars: int | None = None):
    """Mide a mano lo que no pasa por LangChain (embeddings, voz). El bloque
    puede poner los tokens en el dict que devuelve:

        async with measure_call(operation="embedding", ...) as m:
            ...
            m["input_tokens"] = response.usage.prompt_tokens
    """
    extra: dict[str, Any] = {}
    start = time.perf_counter()
    with inference_purpose(purpose):
        try:
            yield extra
        except Exception as exc:
            await record_call(
                operation=operation, model=model, status="error", input_chars=input_chars,
                latency_ms=int((time.perf_counter() - start) * 1000),
                error_type=type(exc).__name__, error_message=str(exc),
            )
            raise
        await record_call(
            operation=operation, model=model, status="ok", input_chars=input_chars,
            latency_ms=int((time.perf_counter() - start) * 1000), **extra,
        )
