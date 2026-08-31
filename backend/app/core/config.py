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

    # --- Narración de lecciones (Ollama genera el guión, Piper TTS lo narra) ---
    # Piper corre EN el proceso del backend (no como servicio Docker
    # aparte, a diferencia de Ollama): es una librería ONNX ligera, no un
    # servidor de inferencia que necesite estar siempre corriendo — carga
    # el modelo de voz una vez por proceso y sintetiza en un hilo aparte
    # (ver app/media/piper_tts.py). Fuera de /app a propósito: en dev
    # ./backend:/app se monta encima del contenedor, así que cualquier
    # cosa horneada en /app durante el build quedaría oculta.
    tts_voice_model_path: str = "/opt/piper-voices/en_US-lessac-medium.onnx"

    # Dónde se guardan los archivos generados (hoy: audio de lecciones).
    # Disco local + un volumen Docker dedicado (ver docker-compose.yml) y
    # servido como estáticos en /media (ver app/main.py) — suficiente
    # para un único contenedor backend; migrar a S3/R2 más adelante solo
    # tocaría app/media/storage.py, nada que hable con esta carpeta directamente.
    media_root: str = "/app/media"

    # --- Facturación ---
    # Dónde redirige el navegador del alumno tras aprobar/cancelar un pago
    # en la pasarela (PayPal, Stripe) antes de volver al frontend.
    frontend_base_url: str = "http://localhost:5173"

    # Todas las credenciales de pasarelas por defecto vacías a propósito:
    # cada gateway (app/billing/*.py) comprueba si las suyas están
    # configuradas y devuelve un 503 explicable en vez de fallar oscuro
    # si alguien intenta cobrar antes de tener las cuentas reales dadas
    # de alta. Nada de esto se sube a git (ver .env vs .env.example).

    # Stripe (tarjetas: Mastercard/Visa/Amex)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # PayPal (Subscriptions API — requiere haber creado un Product+Plan
    # en el dashboard/API de PayPal de antemano; ver Plan.paypal_plan_id)
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_api_base: str = "https://api-m.sandbox.paypal.com"
    paypal_webhook_id: str = ""

    # Binance Pay (cripto). A diferencia de PayPal/Stripe, Binance Pay no
    # tiene "suscripciones" recurrentes reales: cada mes es una orden
    # nueva que el alumno paga a mano — ver Subscription.auto_renew.
    binance_pay_api_key: str = ""
    binance_pay_api_secret: str = ""
    binance_pay_api_base: str = "https://bpay.binanceapi.com"


settings = Settings()
