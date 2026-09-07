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


def get_llm(model_id: str | None = None, temperature: float = 0.6, max_tokens: int = 700) -> ChatOpenAI:
    """Crea un cliente de chat apuntando a nuestro endpoint OpenAI-compatible.

    En desarrollo, `settings.llm_base_url` apunta a Ollama. En producción
    apuntará a vLLM o NVIDIA NIM. `ChatOpenAI` no sabe ni le importa la
    diferencia: solo habla el protocolo /v1/chat/completions.

    `api_key` sale de settings. Para motores locales (Ollama, vLLM) va
    vacía y se sustituye por un relleno: no la validan, pero el SDK de
    OpenAI exige que el campo no esté vacío.

    `max_tokens` NO es opcional en la práctica, aunque tenga default: un
    modelo pequeño ignora alegremente un "escribe 150-300 palabras" del
    prompt. Visto de verdad generando un guión de lección: se fue a
    11.000+ tokens a 12 tok/s — quince minutos en UNA llamada, con el
    semáforo de inferencia bloqueado todo ese rato. El tope convierte ese
    fallo en una respuesta cortada (recuperable) en vez de un cuelgue.

    Va por `extra_body` y NO como argumento `max_tokens=` del constructor
    ni por `model_kwargs`: langchain-openai 0.2.x traduce AMBOS a
    `max_completion_tokens` (el nombre nuevo de la API de OpenAI), que
    Ollama NO reconoce — lo ignora en silencio y sigue generando sin
    límite. `extra_body` es la única vía que deja pasar el `max_tokens`
    crudo, que es el que entienden tanto Ollama como vLLM. Comprobado
    contra el endpoint real: con `max_tokens` corta en seco
    (finish_reason "length"); con `max_completion_tokens` no corta nada.

    `chat_template_kwargs.enable_thinking` apaga el razonamiento en voz
    alta de los Nemotron. No es un ajuste de rendimiento: con él
    encendido, la cadena de pensamiento sale DENTRO del `content` (no en
    un campo aparte), así que el alumno leería "Here's a thinking
    process: 1. Analyze User Input..." en mitad de su clase de inglés.
    Comprobado contra el endpoint real. Solo se manda si
    `llm_enable_thinking` no es None, para no ensuciar la petición hacia
    motores que no conocen el parámetro.

    OJO: cualquier `.ainvoke(...)` sobre el cliente que devuelve esto debe
    pasar por `ainvoke_serialized()`, no llamarse directo — ver el porqué
    arriba.
    """
    extra_body: dict = {"max_tokens": max_tokens}
    if settings.llm_enable_thinking is not None:
        extra_body["chat_template_kwargs"] = {"enable_thinking": settings.llm_enable_thinking}

    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "not-needed-for-local-inference",
        model=model_id or settings.llm_model,
        temperature=temperature,
        extra_body=extra_body,
    )
