import asyncio
from typing import Awaitable, Callable, TypeVar

from langchain_openai import ChatOpenAI

from app.core.config import settings

T = TypeVar("T")

# Serializa TODAS las llamadas de inferencia del backend (chat, detección
# de correcciones, evaluación de tareas, calificación de ejercicios
# abiertos, embeddings) contra el motor de settings.llm_base_url —
# incluidas las que el grafo del tutor lanza "en paralelo" (ver
# app/agents/graph.py). Tamaño configurable vía settings.llm_max_concurrency
# (1 en dev con Ollama+CPU; se sube en producción con un motor que sí
# soporte concurrencia real). Un único semáforo a nivel de módulo, no uno
# por función: lo que hay que proteger es el motor de inferencia
# compartido, no cada punto de llamada por separado.
_inference_semaphore = asyncio.Semaphore(settings.llm_max_concurrency)


async def ainvoke_serialized(call: Callable[[], Awaitable[T]]) -> T:
    """Ejecuta `call` (una llamada async ya armada, ej. `lambda: llm.ainvoke(messages)`)
    sin dejar que compita por el motor de inferencia con otra llamada
    concurrente — ver el porqué en `_inference_semaphore`. Recibe un
    callable (no la coroutine ya creada) para que el `await` real ocurra
    DENTRO del `async with`, no antes."""
    async with _inference_semaphore:
        return await call()


def get_llm(model_id: str | None = None, temperature: float = 0.6) -> ChatOpenAI:
    """Crea un cliente de chat apuntando a nuestro endpoint OpenAI-compatible.

    En desarrollo, `settings.llm_base_url` apunta a Ollama. En producción
    apuntará a vLLM o NVIDIA NIM. `ChatOpenAI` no sabe ni le importa la
    diferencia: solo habla el protocolo /v1/chat/completions.

    `api_key` es un valor cualquiera no vacío: Ollama/vLLM en local no lo
    validan, pero el SDK de OpenAI exige que el campo no esté vacío.

    OJO: cualquier `.ainvoke(...)` sobre el cliente que devuelve esto debe
    pasar por `ainvoke_serialized()`, no llamarse directo — ver el porqué
    arriba.
    """
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key="not-needed-for-local-inference",
        model=model_id or settings.llm_model,
        temperature=temperature,
    )
