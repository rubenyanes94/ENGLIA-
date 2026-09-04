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

from app.agents.llm_client import ainvoke_serialized, get_llm
from app.models import AgentPersona

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

Tema de esta lección: {topic}
"""


async def generate_lesson_script(topic: str, level_code: str, persona: AgentPersona) -> str:
    # 500 tokens ≈ 300 palabras largas: suficiente para el guión que pide
    # el prompt, y un techo que impide que un modelo pequeño se dispare
    # (ver la nota en get_llm).
    llm = get_llm(model_id=persona.model_id, temperature=0.5, max_tokens=500)
    system_prompt = SCRIPT_SYSTEM_PROMPT.format(persona_name=persona.name, level_code=level_code, topic=topic)

    # ainvoke_serialized y no llm.ainvoke directo: comparte el motor de
    # inferencia con el chat y las correcciones, y pedirle a Ollama dos
    # generaciones a la vez en este entorno tumba el proceso (ver
    # app/agents/llm_client.py).
    response = await ainvoke_serialized(
        lambda: llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Escribe el guión sobre: {topic}")])
    )
    return response.content
