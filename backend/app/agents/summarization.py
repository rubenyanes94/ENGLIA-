"""Resume una sesión de chat cerrada. Es lo que luego se embebe y se usa
como memoria semántica de largo plazo (ver app/workers/tasks.py)."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm_client import get_llm
from app.monitoring.llm_metrics import inference_purpose

SUMMARY_SYSTEM_PROMPT = """\
A continuación recibirás la TRANSCRIPCIÓN COMPLETA de una sesión ya \
terminada entre un tutor de inglés y un alumno (líneas "user:"/"assistant:").

Tu única tarea es escribir un RESUMEN de esa transcripción en 2-3 frases, \
en español, para que un tutor lo lea antes de la PRÓXIMA sesión.

IMPORTANTE: no continúes la conversación, no corrijas nada, no te \
dirijas al alumno. Eres un observador describiendo lo que pasó, en \
tercera persona.

Incluye: de qué temas habló el alumno, y qué errores gramaticales \
cometió con más frecuencia (si los hubo).

Ejemplo de transcripción:
user: I work as a teacher. I goed to Madrid last year.
assistant: That's interesting! What do you teach?
user: I teach mathematics to high school students.

Ejemplo de resumen correcto:
El alumno habló sobre su trabajo como profesor de matemáticas en un \
instituto y un viaje a Madrid el año pasado. Cometió un error recurrente \
con el pasado de verbos irregulares ("goed" en vez de "went").

Ahora escribe el resumen de la transcripción real que recibas a continuación.
"""


async def summarize_transcript(transcript: str, model_id: str) -> str:
    llm = get_llm(model_id=model_id, temperature=0.3)
    # Corre en el worker de Celery, fuera de ainvoke_serialized: se etiqueta
    # a mano para que el panel de monitoreo sepa de dónde viene la llamada.
    with inference_purpose("session_summary"):
        response = await llm.ainvoke(
            [SystemMessage(content=SUMMARY_SYSTEM_PROMPT), HumanMessage(content=transcript)]
        )
    return response.content
