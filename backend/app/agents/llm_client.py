import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Errores que SÍ merecen reintento: el proveedor está saturado, nos limita
# el ritmo, o se cayó la conexión. Todos son transitorios y ajenos a
# nosotros. Visto de verdad en el tier gratuito de NVIDIA: un 503
# "Service temporarily overloaded" en mitad de una generación, con las
# ocho llamadas siguientes funcionando sin tocar nada.
#
# Deliberadamente NO se reintentan 404 (modelo mal escrito), 401 (clave
# inválida) ni 400 (petición malformada): esos son errores NUESTROS, y
# reintentarlos solo los esconde y multiplica por tres el tiempo hasta
# ver el fallo real.
RETRYABLE_ERRORS = (InternalServerError, RateLimitError, APIConnectionError, APITimeoutError)

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
    concurrente — ver el porqué en `_inference_semaphore` — y reintentando
    los fallos transitorios del proveedor.

    Recibe un callable (no la coroutine ya creada) por DOS razones: para
    que el `await` real ocurra dentro del `async with`, y para poder
    volver a armar la llamada en cada reintento (una coroutine ya
    consumida no se puede reesperar).

    El reintento vive aquí y no en cada punto de llamada porque este es el
    único sitio por el que pasa TODA la inferencia del backend: respuesta
    del tutor, detección de correcciones, evaluación de tareas,
    calificación y generación de guiones. Sin esto, un 503 pasajero del
    proveedor le llega al alumno como un error de la aplicación.

    La espera crece (1s, 2s, 4s...) y lleva jitter aleatorio: si varios
    alumnos se topan con la misma caída, reintentar todos a la vez en el
    mismo instante es justo lo que impide que el proveedor se recupere.
    """
    last_error: Exception | None = None
    for attempt in range(settings.llm_max_retries + 1):
        async with _inference_semaphore:
            try:
                return await call()
            except RETRYABLE_ERRORS as exc:
                last_error = exc

        if attempt < settings.llm_max_retries:
            # El sleep va FUERA del semáforo: esperar con el hueco de
            # inferencia ocupado bloquearía a los demás alumnos por un
            # fallo que no es suyo.
            delay = settings.llm_retry_base_delay_seconds * (2**attempt) * (1 + random.random() * 0.25)
            logger.warning(
                "Inferencia falló (%s), reintento %d/%d en %.1fs",
                type(last_error).__name__, attempt + 1, settings.llm_max_retries, delay,
            )
            await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error


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
