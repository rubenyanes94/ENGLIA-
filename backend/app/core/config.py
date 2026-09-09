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
    # Endpoint del CHAT. Por defecto el catálogo de NVIDIA y no Ollama
    # desde que se midió la diferencia con el tutor real: Ollama con el
    # 0.5B que cabe en este entorno tardó 34s en contestar "Hello Ruben!"
    # SIN corregir nada; nemotron-3-super responde en ~1-3s y sí detecta
    # los errores de interferencia del currículo ("I have 25 years" →
    # "I am 25 years old"). Ollama sigue sirviendo los embeddings (ver
    # embedding_base_url) y queda como alternativa sin conexión.
    llm_base_url: str = "https://integrate.api.nvidia.com/v1"
    # qwen2.5:0.5b (~400MB), no llama3.2:1b (~1.3GB): en un Codespace de
    # 8GB compartido con VS Code+extensiones, cargar el modelo de 1.3GB
    # ha tumbado el proceso llama-server de Ollama más de una vez por
    # simple presión de memoria (ni siquiera con concurrencia — pasaba
    # también en aislamiento). Este es más chico y responde peor, pero
    # responde. En producción, con vLLM/NIM sobre GPU dedicada, esto se
    # sube por env var (LLM_MODEL) a un modelo real sin este compromiso.
    # super-120b y NO lightning-30b, contra lo que sugiere la ficha de cada
    # uno: lo que importa es la latencia MEDIDA en el endpoint real, no
    # los parámetros activos del modelo. lightning tardó 73-111s por turno
    # (está encolado); super, 0.8-2.7s. Ochenta veces más rápido el que
    # en teoría era el lento.
    llm_model: str = "nvidia/nemotron-3-super-120b-a12b"

    # Clave del endpoint de chat. Vacía para motores locales (Ollama y
    # vLLM no la validan, pero el SDK de OpenAI exige el campo no vacío —
    # ver llm_client.get_llm).
    llm_api_key: str = ""

    # Los Nemotron razonan en voz alta ANTES de responder, y ese
    # razonamiento sale dentro del `content`, no en un campo aparte: el
    # alumno leería "Here'"'"'s a thinking process: 1. Analyze User Input..."
    # en mitad de su clase. Apagado para el chat. Se puede encender para
    # tareas offline donde el razonamiento mejore el resultado y nadie lo
    # lea en crudo. None = no mandar el parámetro (motores que no lo
    # entienden, como Ollama).
    llm_enable_thinking: bool | None = False
    # Mismo servidor (Ollama), otro tipo de modelo: embeddings para la
    # memoria semántica. Un solo motor de inferencia para todo el agente.
    embedding_model: str = "nvidia/nemotron-3-embed-1b"

    # Endpoint SEPARADO del chat. Estaban unidos solo porque los dos
    # modelos vivían en el mismo Ollama; al mover el chat a NVIDIA, seguir
    # compartiendo la URL habría hecho que se pidiera "nomic-embed-text"
    # a un catálogo que no lo tiene. Se separan ahora para que cada motor
    # se pueda mover sin arrastrar al otro.
    embedding_base_url: str = "https://integrate.api.nvidia.com/v1"
    embedding_api_key: str = ""

    # Semáforo propio, separado del de chat: aunque ahora los dos apunten
    # al mismo proveedor, son cuotas y patrones de uso distintos (el chat
    # lo dispara un alumno esperando; los embeddings, Celery en segundo
    # plano). Manteniéndolos separados, una tanda de resúmenes no puede
    # comerse los huecos de inferencia de quien está conversando.
    #
    # Era 1 mientras vivían en Ollama con OLLAMA_MAX_LOADED_MODELS=1.
    embedding_max_concurrency: int = 2
    embedding_dim: int = 2048

    # Cuántas inferencias simultáneas tolera el motor configurado en
    # llm_base_url (ver app/agents/llm_client.py, ainvoke_serialized).
    # Era 1 mientras el chat corría en Ollama sobre CPU: dos inferencias a
    # la vez tumbaban el proceso llama-server, incluido el fan-out
    # "paralelo" del propio grafo del tutor (generate_response +
    # detect_corrections + evaluate_active_task). Con el chat en un
    # endpoint remoto ese motivo desapareció, y mantener 1 sería un fallo
    # de producto: dos alumnos hablando a la vez harían cola uno detrás
    # del otro.
    #
    # 4 y no más porque el límite real ahora es la cuota del proveedor
    # (40 req/min en el tier gratuito de NVIDIA) y cada turno del tutor
    # gasta 3 llamadas. Súbelo con LLM_MAX_CONCURRENCY cuando haya plan
    # de pago o motor propio.
    llm_max_concurrency: int = 4

    # Reintentos ante fallos transitorios del proveedor (ver
    # app/agents/llm_client.py, RETRYABLE_ERRORS). Con el motor en local
    # esto no hacía falta: Ollama estaba arriba o no. Con inferencia
    # remota sí — el tier gratuito de NVIDIA devolvió un 503 "Service
    # temporarily overloaded" con las ocho llamadas siguientes
    # funcionando. 3 reintentos con espera 1s/2s/4s cubren esa clase de
    # bache sin que el alumno note nada; más allá, algo pasa de verdad y
    # es mejor fallar que dejarle mirando una animación de carga.
    llm_max_retries: int = 3
    llm_retry_base_delay_seconds: float = 1.0

    # Tope de tokens para GENERAR un guión de lección, aparte del tope del
    # chat: son dos trabajos con formas distintas. Una respuesta de tutor
    # son dos frases; un guión son 150-300 palabras de prosa narrada.
    #
    # Estaba en 500 para frenar al modelo de 0.5B, que se disparó a 11.000
    # tokens en una sola llamada. Con super-120b ese tope ya no protege:
    # MUTILA. Comprobado — con 500 el guión termina en "...a describir el
    # pelo y" (finish_reason "length"); con 1200 cierra solo en 581 tokens
    # ("¡Hasta la próxima!"). El tope sigue existiendo como red de
    # seguridad, pero por encima de lo que el trabajo necesita de verdad.
    lesson_script_max_tokens: int = 1200

    # Cuántas veces se le pide al modelo que rehaga un guión que no pasa
    # la validación (ver agents/lesson_script_validation.py). 3 porque el
    # fallo típico es de descuido y se corrige al decírselo; si a la
    # tercera sigue mal, el problema es el prompt o el tema, y conviene
    # enterarse en vez de gastar llamadas en silencio.
    lesson_script_max_attempts: int = 3

    # --- Moderación del chat (ver app/agents/moderation.py) ---
    # Espikin tiene chat libre y alumnos probablemente menores. Se revisa
    # cada turno en las dos direcciones (lo que escribe el alumno y lo que
    # responde el tutor) en una sola llamada de 0.1-0.9s.
    moderation_model: str = "nvidia/nemotron-3.5-content-safety"
    # Apagarlo deja pasar todo SIN revisar y marcado como tal. Existe para
    # desarrollo sin conexión, no como interruptor de producción.
    moderation_enabled: bool = True

    # --- Evaluación de pronunciación (ver app/agents/pronunciation.py) ---
    pronunciation_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    # Tope del audio que sube el alumno. 10s a 16kHz mono son ~320KB; el
    # límite deja margen y ataja de golpe que alguien suba un archivo
    # grande a un endpoint que reenvía su contenido a un tercero.
    pronunciation_max_audio_bytes: int = 2 * 1024 * 1024

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
    #
    # Por defecto "magpie" desde que se eligió a Diego: es LA voz del
    # producto, y dejar "piper" por defecto haría que un despliegue sin
    # configurar narrara con la voz equivocada EN SILENCIO. Sin
    # NVIDIA_API_KEY, Magpie falla con un mensaje explícito (ver
    # media/magpie_tts.py) — un fallo ruidoso al generar audio nuevo es
    # mucho mejor que audio correcto con la voz de otro tutor. Y no afecta
    # al alumno: las lecciones se sirven como archivos ya generados, así
    # que sin clave solo se bloquea CREAR narraciones, no escucharlas.
    tts_provider: str = "magpie"

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
