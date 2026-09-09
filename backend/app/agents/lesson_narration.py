"""Genera el guión que el tutor narra en una lección — mismo LLM que el
chat (app/agents/llm_client.get_llm), pero aquí es un monólogo
pedagógico armado a partir de un tema, no una respuesta conversacional.

A diferencia de corrections.py o grading.py, esto NO necesita salida
estructurada (JSON): el resultado es directamente el texto a narrar.

El guión es BILINGÜE por diseño: se explica en español (el alumno es
hispanohablante y está empezando) y los ejemplos se dicen en inglés,
marcados entre [[dobles corchetes]] para que el sintetizador los narre
con la voz inglesa y no con la española — ver
app/media/piper_tts.py, synthesize_bilingual_to_wav.
"""

from langchain_core.messages import HumanMessage, SystemMessage

import logging

from app.agents.lesson_script_validation import validate_lesson_script
from app.agents.llm_client import ainvoke_serialized, get_llm
from app.agents.prompt_builder import SPANISH_VARIETY
from app.core.config import settings
from app.models import AgentPersona

logger = logging.getLogger(__name__)

SCRIPT_SYSTEM_PROMPT = """\
Eres {persona_name}, tutor de inglés para alumnos hispanohablantes de \
nivel MCER {level_code}. Vas a grabar el guión de una lección en AUDIO — \
el alumno solo lo va a ESCUCHAR, no a leer.

REGLA MÁS IMPORTANTE — el idioma:
- EXPLICAS EN ESPAÑOL. Toda la enseñanza, las aclaraciones y las \
instrucciones van en español, porque el alumno todavía no entiende \
explicaciones en inglés.
- Cada vez que digas una palabra o frase EN INGLÉS, enciérrala entre \
dobles corchetes. Ejemplo de cómo debe verse tu guión:
  Para decir tu edad no uses el verbo "tener". Se dice [[I am 25 years old]], \
literalmente "yo soy 25 años". Repite conmigo: [[I am 25 years old]].
- Usa los corchetes SOLO para el inglés real que el alumno debe escuchar \
y repetir, nunca para palabras en español.
- SIN EXCEPCIÓN: si escribes una sola palabra en inglés fuera de los \
corchetes, el sintetizador la leerá con acento español y la lección \
enseñará mal la pronunciación. Antes de terminar, relee tu guión y \
comprueba que TODO el inglés está entre [[corchetes]].
- {spanish_variety}

Otras reglas:
- Habla en primera persona, directo al alumno ("Hoy vamos a...", "Fíjate \
que...", "Repite conmigo...").
- Nada de títulos, listas ni markdown: es un guión para leer en voz alta \
de corrido, tiene que sonar natural narrado, no como un documento.
- Calibra la dificultad al nivel {level_code}: en A1/A2 frases cortas y \
vocabulario básico; en B1/B2 más matiz; en C1/C2 puedes ser más denso.
- Entre 150 y 300 palabras (para que la narración dure entre 2 y 4 \
minutos con una voz normal).
- Da al menos tres ejemplos en inglés entre corchetes, y anima a repetirlos.
- PROHIBIDO dejar huecos para rellenar ("___", "____"): esto se ESCUCHA, \
no se lee. Un hueco en blanco no se puede oír. Si quieres que el alumno \
complete algo, dilo con palabras ("ahora di tu nombre").

Tema de esta lección: {topic}
"""


async def generate_lesson_script(topic: str, level_code: str, persona: AgentPersona) -> str:
    """Genera el guión y NO devuelve uno inservible.

    El reintento con la crítica incorporada, en vez de aceptar lo primero
    que salga: de la primera tanda de nueve, uno escribió todo el inglés
    sin marcar (se habría narrado entero con voz española) y cinco
    colaron huecos "___" que en audio no significan nada. Reintentar
    diciéndole al modelo QUÉ falló cuesta una llamada y evita que un
    guión roto llegue a narrarse — que cuesta ~40 llamadas de síntesis y,
    peor, le enseña mal al alumno.
    """
    # Tope propio del guión, no el del chat: ver
    # settings.lesson_script_max_tokens para por qué 500 se quedó corto y
    # cortaba las lecciones a media frase.
    llm = get_llm(model_id=persona.model_id, temperature=0.5, max_tokens=settings.lesson_script_max_tokens)
    system_prompt = SCRIPT_SYSTEM_PROMPT.format(
        persona_name=persona.name,
        level_code=level_code,
        topic=topic,
        # La voz que narra este guión es mexicana (ver core/config.py):
        # un texto en español peninsular leído con acento latinoamericano
        # suena a doblaje mal hecho, no a un profesor hablando.
        spanish_variety=SPANISH_VARIETY,
    )

    # ainvoke_serialized y no llm.ainvoke directo: comparte el motor de
    # inferencia con el chat y las correcciones, y pedirle a Ollama dos
    # generaciones a la vez en este entorno tumba el proceso (ver
    # app/agents/llm_client.py).
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=f"Escribe el guión sobre: {topic}")]

    problems: list[str] = []
    for attempt in range(settings.lesson_script_max_attempts):
        if problems:
            # Se le devuelve la crítica concreta, no un "hazlo otra vez":
            # un modelo que sabe QUÉ falló corrige; uno que solo sabe que
            # falló vuelve a tirar los mismos dados.
            messages.append(HumanMessage(content=(
                "Ese guión no sirve por: " + "; ".join(problems) + ". "
                "Reescríbelo entero corrigiendo exactamente eso, sin cambiar el tema."
            )))

        response = await ainvoke_serialized(lambda: llm.ainvoke(messages))
        script = response.content
        problems = validate_lesson_script(script)
        if not problems:
            return script
        logger.warning("Guión rechazado (intento %d/%d): %s", attempt + 1, settings.lesson_script_max_attempts, problems)
        messages.append(response)

    raise ValueError(
        f"No se logró un guión válido para {topic!r} tras "
        f"{settings.lesson_script_max_attempts} intentos. Último fallo: {'; '.join(problems)}"
    )
