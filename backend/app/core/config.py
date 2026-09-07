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
    # qwen2.5:0.5b (~400MB), no llama3.2:1b (~1.3GB): en un Codespace de
    # 8GB compartido con VS Code+extensiones, cargar el modelo de 1.3GB
    # ha tumbado el proceso llama-server de Ollama más de una vez por
    # simple presión de memoria (ni siquiera con concurrencia — pasaba
    # también en aislamiento). Este es más chico y responde peor, pero
    # responde. En producción, con vLLM/NIM sobre GPU dedicada, esto se
    # sube por env var (LLM_MODEL) a un modelo real sin este compromiso.
    llm_model: str = "qwen2.5:0.5b"
    # Mismo servidor (Ollama), otro tipo de modelo: embeddings para la
    # memoria semántica. Un solo motor de inferencia para todo el agente.
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Cuántas inferencias simultáneas tolera el motor configurado en
    # llm_base_url (ver app/agents/llm_client.py, ainvoke_serialized).
    # Default=1 porque Ollama sobre CPU en un Codespace de 8GB compartido
    # (Postgres+Redis+Celery+Vite+el propio VS Code) NO soporta 2+
    # inferencias a la vez con fiabilidad: se ha visto tumbar el proceso
    # llama-server entero bajo el fan-out "paralelo" del grafo del tutor
    # (generate_response + detect_corrections + evaluate_active_task a la
    # vez), sin mencionar una llamada de embeddings compitiendo por el
    # único modelo que OLLAMA_MAX_LOADED_MODELS permite tener cargado. En
    # producción, con vLLM/NVIDIA NIM sobre GPU dedicada, sube esto por
    # env var (LLM_MAX_CONCURRENCY) a lo que el motor real soporte.
    llm_max_concurrency: int = 1

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
    # DOS voces, no una: la lección se explica en español pero los
    # ejemplos se dicen en inglés. Narrar los ejemplos con la voz
    # española enseñaría pronunciación incorrecta — inaceptable en una
    # app de idiomas — y narrar la explicación con la voz inglesa suena
    # a robot leyendo un idioma que no conoce. Ver
    # app/media/piper_tts.py (synthesize_bilingual_to_wav).
    #
    # Ningún modelo de Piper habla los dos idiomas: cada uno está
    # entrenado sobre una sola lengua, así que "la misma voz para todo"
    # no existe. Lo que SÍ se puede es que las dos suenen al mismo
    # tutor, y por eso ambas son MASCULINAS y de la misma calidad
    # (medium, 22050 Hz — requisito para poder concatenar los
    # fragmentos sin remuestrear). Antes el par era davefx (hombre) +
    # lessac (mujer): en mitad de una frase el profesor cambiaba de
    # persona, y eso rompe la ilusión de estar en una clase.
    #
    # Español de LATAM (es_MX), no de España: el público objetivo de
    # Espikin es hispanohablante de América. El acento peninsular no
    # impide entender, pero un alumno mexicano o colombiano no reconoce
    # a su profesor en él — y la voz del tutor es media cara del producto.
    tts_voice_model_path: str = "/opt/piper-voices/en_US-ryan-medium.onnx"
    tts_voice_model_path_es: str = "/opt/piper-voices/es_MX-ald-medium.onnx"

    # --- Motor de voz: "piper" (local) o "magpie" (NVIDIA, por API) ---
    # Piper es gratis y no depende de la red, pero tiene un límite
    # estructural: cada voz suya habla UN idioma, así que el español y el
    # inglés salen por fuerza de dos personas distintas. Magpie es un
    # único modelo multilingüe y el MISMO hablante dice los dos idiomas —
    # que es justo lo que pide una lección donde se explica en español y
    # se ejemplifica en inglés.
    tts_provider: str = "piper"

    # Voces de Magpie. Comprobado contra el servidor (no contra la
    # documentación, que lista voces que el endpoint no sirve): en
    # español solo hay dos, Diego (hombre) e Isabela (mujer). Y la subvoz
    # española de Diego ACEPTA language_code "en-US", que es lo que
    # permite que estas dos líneas apunten al mismo hablante y el alumno
    # no oiga cambiar de profesor al llegar al ejemplo en inglés.
    #
    # ES-US, además, es español de Estados Unidos: base latinoamericana,
    # no peninsular — la variedad del doblaje neutro que busca el producto.
    magpie_voice_es: str = "Magpie-Multilingual.ES-US.Diego"
    magpie_voice_en: str = "Magpie-Multilingual.ES-US.Diego"

    # 22050 Hz para que los fragmentos se concatenen igual que los de
    # Piper y ambos motores sean intercambiables (ver media/wav.py).
    magpie_sample_rate_hz: int = 22050
    magpie_grpc_uri: str = "grpc.nvcf.nvidia.com:443"
    magpie_function_id: str = "877104f7-e885-42b9-8de8-f6e4c6303969"

    # Clave del catálogo de NVIDIA (build.nvidia.com). Vacía por defecto:
    # sin ella, Magpie falla con un mensaje explicable en vez de un error
    # de red oscuro, y Piper sigue funcionando sin configurar nada.
    nvidia_api_key: str = ""

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
