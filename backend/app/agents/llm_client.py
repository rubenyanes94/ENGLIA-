from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_llm(model_id: str | None = None, temperature: float = 0.6) -> ChatOpenAI:
    """Crea un cliente de chat apuntando a nuestro endpoint OpenAI-compatible.

    En desarrollo, `settings.llm_base_url` apunta a Ollama. En producción
    apuntará a vLLM o NVIDIA NIM. `ChatOpenAI` no sabe ni le importa la
    diferencia: solo habla el protocolo /v1/chat/completions.

    `api_key` es un valor cualquiera no vacío: Ollama/vLLM en local no lo
    validan, pero el SDK de OpenAI exige que el campo no esté vacío.
    """
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key="not-needed-for-local-inference",
        model=model_id or settings.llm_model,
        temperature=temperature,
    )
