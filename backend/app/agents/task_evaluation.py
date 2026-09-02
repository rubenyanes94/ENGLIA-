"""Evaluación de la tarea activa — tercer nodo del grafo del tutor (ver
app/agents/graph.py), en paralelo con generate_response/detect_corrections.

Solo hace trabajo real cuando la sesión tiene una tarea activa (un
elemento de Module.tasks). Analiza el turno del alumno Y el turno
INMEDIATAMENTE anterior del tutor para juzgar dos cosas:

1. task_completed: si el alumno cumplió el criterio de éxito de la tarea
   EN ESTE turno — es lo que decide si se registra DescriptorEvidence
   como éxito (ver routers/chat.py).
2. scaffolded: si el turno anterior del tutor le entregó al alumno la
   frase/estructura objetivo casi lista para copiar. Si fue así, este
   éxito no cuenta como evidencia "sin andamiaje" (documento de currículo
   § 1.6, condición 3 de mastery_rule) — mismo campo que
   DescriptorEvidence.scaffolded, pero aquí SÍ puede ser True (a
   diferencia de la evidencia que viene de un Exercise, donde nunca hay
   andamiaje posible).

Nunca lanza: igual que corrections.py/grading.py, si el LLM no da JSON
válido se asume "no completada, sin andamiaje" en vez de tumbar el turno.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agents.llm_client import ainvoke_serialized, get_llm

logger = logging.getLogger(__name__)

TASK_EVALUATION_SYSTEM_PROMPT = """\
Eres un evaluador pedagógico observando una conversación entre un tutor de \
inglés IA y un alumno hispanohablante de nivel MCER {level_code}.

Tarea que el alumno está practicando: "{task_prompt}"
Se considera lograda si: {success_criteria}

Turno anterior del tutor, para contexto (puede estar vacío si es el \
primer turno): "{previous_tutor_message}"

Analiza el mensaje del alumno que se te pasa a continuación y responde \
SIEMPRE con un objeto JSON con esta forma exacta (sin texto antes ni después):

{{"task_completed": true|false, "scaffolded": true|false, "reasoning": "..."}}

- task_completed: true SOLO si el turno del alumno, por sí mismo, cumple \
razonablemente el criterio de éxito. Ante la duda, false.
- scaffolded: true si el turno anterior del tutor ya le dio al alumno la \
frase o estructura objetivo casi lista para repetir, en vez de dejar que \
la produjera solo. Si no hubo turno anterior del tutor, false.
- reasoning: una frase breve en español, solo para depuración.
"""


class TaskEvaluationResult(BaseModel):
    task_completed: bool
    scaffolded: bool
    reasoning: str = ""


async def evaluate_task(
    student_message: str,
    previous_tutor_message: str | None,
    task_prompt: str,
    success_criteria: str,
    level_code: str,
    model_id: str,
) -> TaskEvaluationResult:
    llm = get_llm(model_id=model_id, temperature=0.1)
    structured_llm = llm.with_structured_output(TaskEvaluationResult, method="json_mode")

    prompt = TASK_EVALUATION_SYSTEM_PROMPT.format(
        level_code=level_code,
        task_prompt=task_prompt,
        success_criteria=success_criteria or "El alumno participa de forma relevante en la tarea.",
        previous_tutor_message=previous_tutor_message or "",
    )

    try:
        return await ainvoke_serialized(
            lambda: structured_llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=student_message)])
        )
    except Exception:
        logger.warning("No se pudo evaluar la tarea activa con el LLM", exc_info=True)
        return TaskEvaluationResult(task_completed=False, scaffolded=False, reasoning="fallback: error del LLM")
