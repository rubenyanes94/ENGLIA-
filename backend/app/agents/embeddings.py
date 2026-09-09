"""Cliente de embeddings — sigue en el Ollama local, aunque el chat del
tutor ya se haya ido a un endpoint remoto. Un embedding es un vector que representa el
"significado" de un texto: textos con significado parecido quedan con
vectores cercanos, y eso es lo que nos permite buscar "sesiones pasadas
parecidas a esto" con SQL normal (pgvector) en vez de comparar texto.
"""

import asyncio

from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

# Semáforo PROPIO, ya no el del chat. Se compartía porque los dos modelos
# vivían en el mismo Ollama y competían por el único hueco que
# OLLAMA_MAX_LOADED_MODELS=1 permite. Ahora el chat está en otro motor:
# seguir compartiendo el semáforo haría que una llamada de embeddings
# frenara a un alumno que está conversando, sin ninguna razón técnica.
_embedding_semaphore = asyncio.Semaphore(settings.embedding_max_concurrency)


def get_embeddings_client() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key or "not-needed-for-local-inference",
        model=settings.embedding_model,
        check_embedding_ctx_length=False,  # Ollama no expone tokenizer/tiktoken; lo desactivamos
    )


async def embed_text(text: str) -> list[float]:
    # Serializado igual que antes, pero por su propio semáforo: Ollama con
    # OLLAMA_MAX_LOADED_MODELS=1 sigue sin tolerar dos peticiones a la vez.
    async with _embedding_semaphore:
        client = get_embeddings_client()
        return await client.aembed_query(text)
