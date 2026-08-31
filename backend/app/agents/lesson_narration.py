"""Genera el guión que James narra en una lección — mismo LLM que el
chat (app/agents/llm_client.get_llm), pero aquí es un monólogo
pedagógico armado a partir de un tema, no una respuesta conversacional.

A diferencia de corrections.py o grading.py, esto NO necesita salida
estructurada (JSON): el resultado es directamente el texto a narrar.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm_client import get_llm
from app.models import AgentPersona

SCRIPT_SYSTEM_PROMPT = """\
Eres {persona_name}, tutor de inglés para alumnos hispanohablantes de \
nivel MCER {level_code}. Vas a grabar el guión de una lección en AUDIO — \
el alumno solo lo va a ESCUCHAR, no a leer. Ten esto en cuenta:

- Habla en primera persona, directo al alumno ("Hoy vamos a...", "Fíjate \
que...", "Repite conmigo...").
- Explica en español y da los ejemplos de inglés dentro de la frase —
  igual que le hablarías en voz alta a un alumno real.
- Nada de títulos, listas ni markdown: es un guión para leer en voz alta
  de corrido, tiene que sonar natural narrado, no como un documento.
- Calibra la dificultad al nivel {level_code}: en A1/A2 frases cortas y
  vocabulario básico; en B1/B2 más matiz; en C1/C2 puedes ser más denso.
- Entre 150 y 300 palabras (para que la narración dure entre 2 y 4
  minutos con una voz normal).

Tema de esta lección: {topic}
"""


async def generate_lesson_script(topic: str, level_code: str, persona: AgentPersona) -> str:
    llm = get_llm(model_id=persona.model_id, temperature=0.5)
    system_prompt = SCRIPT_SYSTEM_PROMPT.format(persona_name=persona.name, level_code=level_code, topic=topic)

    response = await llm.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=f"Escribe el guión sobre: {topic}")]
    )
    return response.content
