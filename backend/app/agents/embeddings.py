"""Cliente de embeddings — mismo servidor (Ollama) que el LLM del tutor,
distinto tipo de modelo. Un embedding es un vector que representa el
"significado" de un texto: textos con significado parecido quedan con
vectores cercanos, y eso es lo que nos permite buscar "sesiones pasadas
parecidas a esto" con SQL normal (pgvector) en vez de comparar texto.
"""

from langchain_openai import OpenAIEmbeddings

from app.agents.llm_client import ainvoke_serialized
from app.core.config import settings


def get_embeddings_client() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        base_url=settings.llm_base_url,
        api_key="not-needed-for-local-inference",
        model=settings.embedding_model,
        check_embedding_ctx_length=False,  # Ollama no expone tokenizer/tiktoken; lo desactivamos
    )


async def embed_text(text: str) -> list[float]:
    # Pasa por el mismo semáforo que el resto de llamadas de inferencia
    # (ver ainvoke_serialized): este es un modelo DISTINTO (nomic-embed-text
    # vs llama3.2:1b) en el MISMO servidor Ollama con
    # OLLAMA_MAX_LOADED_MODELS=1 — sin serializar, una llamada de
    # embeddings concurrente con el chat fuerza a Ollama a descargar y
    # recargar modelos a mitad de una generación, lo que en la práctica
    # es lo que ha tumbado el proceso llama-server.
    client = get_embeddings_client()
    return await ainvoke_serialized(lambda: client.aembed_query(text))
