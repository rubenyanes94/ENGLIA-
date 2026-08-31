from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada de la app.

    pydantic-settings lee automáticamente las variables de entorno
    (las que definimos en docker-compose.yml / .env). Si una variable
    no existe en el entorno, usa el valor por defecto de aquí abajo.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://englia:englia_dev_password@db:5432/englia"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change_me_in_production"
    environment: str = "development"

    # --- JWT ---
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # sin refresh token todavía: al expirar, login de nuevo

    # Endpoint OpenAI-compatible del motor de inferencia. En dev apunta a
    # Ollama; en producción, a vLLM o NVIDIA NIM. El código del agente
    # (app/agents/) nunca sabe cuál de los dos es — solo habla "OpenAI API".
    llm_base_url: str = "http://ollama:11434/v1"
    llm_model: str = "llama3.2:1b"
    # Mismo servidor (Ollama), otro tipo de modelo: embeddings para la
    # memoria semántica. Un solo motor de inferencia para todo el agente.
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Cola de tareas async (resumen + embedding al cerrar una sesión).
    # DB 1 de Redis, separada de la DB 0 (memoria de corto plazo del chat)
    # para que un `FLUSHDB` o una inspección de una no toque a la otra.
    celery_broker_url: str = "redis://redis:6379/1"

    # Cuánto tiempo vive en Redis el historial de una sesión de chat sin
    # actividad. Pasado este tiempo, la conversación se "olvida" del corto
    # plazo (pero el historial permanente sigue en Postgres, intacto).
    chat_session_ttl_minutes: int = 120


settings = Settings()
