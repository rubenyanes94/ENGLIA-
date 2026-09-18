"""Cliente de embeddings — sigue en el Ollama local, aunque el chat del
tutor ya se haya ido a un endpoint remoto. Un embedding es un vector que representa el
"significado" de un texto: textos con significado parecido quedan con
vectores cercanos, y eso es lo que nos permite buscar "sesiones pasadas
parecidas a esto" con SQL normal (pgvector) en vez de comparar texto.
"""

import asyncio

from openai import AsyncOpenAI

from app.core.config import settings
from app.monitoring.llm_metrics import measure_call

# Semáforo PROPIO, ya no el del chat. Se compartía porque los dos modelos
# vivían en el mismo Ollama y competían por el único hueco que
# OLLAMA_MAX_LOADED_MODELS=1 permite. Ahora el chat está en otro motor:
# seguir compartiendo el semáforo haría que una llamada de embeddings
# frenara a un alumno que está conversando, sin ninguna razón técnica.
_embedding_semaphore = asyncio.Semaphore(settings.embedding_max_concurrency)


def get_embeddings_client() -> AsyncOpenAI:
    # El SDK de OpenAI directo y no OpenAIEmbeddings de LangChain: LangChain
    # tira la cabecera `usage` de la respuesta, y el panel de monitoreo
    # necesita los tokens reales. Misma petición que antes (modelo + texto,
    # sin recortar por longitud: NVIDIA no expone su tokenizador).
    return AsyncOpenAI(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key or "not-needed-for-local-inference",
    )


async def embed_text(text: str) -> list[float]:
    # Serializado por su propio semáforo (ver arriba) y medido para el
    # panel de gerencia → Sistema: latencia, tokens y errores.
    async with _embedding_semaphore:
        async with measure_call(
            operation="embedding", purpose="embedding", model=settings.embedding_model, input_chars=len(text)
        ) as metrics:
            response = await get_embeddings_client().embeddings.create(model=settings.embedding_model, input=[text])
            if response.usage is not None:
                metrics["input_tokens"] = response.usage.prompt_tokens
            return response.data[0].embedding
