"""Corrección de ejercicios.

Dos caminos, según el tipo de ejercicio:

- CERRADOS (multiple_choice, fill_blank): hay una única respuesta
  correcta en `answer_key`. Se comparan como texto, sin pasar por el
  LLM — es más rápido, 100% determinista, y no tiene sentido gastar una
  llamada de inferencia en comparar dos strings.
- ABIERTOS (writing, speaking): no hay una única respuesta "correcta"
  que comparar, hace falta juicio. Mismo patrón que
  app/agents/corrections.py: salida estructurada vía JSON mode, con
  fallback si el LLM no coopera.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm_client import get_llm

logger = logging.getLogger(__name__)

CLOSED_EXERCISE_TYPES = {"multiple_choice", "fill_blank"}

GRADING_SYSTEM_PROMPT = """\
Eres un profesor de inglés corrigiendo la respuesta de un alumno \
hispanohablante de nivel MCER {level_code} a un ejercicio abierto.

Ejercicio planteado: "{prompt}"

Evalúa la respuesta del alumno CALIBRADA a su nivel MCER: no exijas la \
precisión de un C1 a un alumno de A2. Da una nota de 0.0 a 1.0 (1.0 = \
respuesta correcta y natural para su nivel) y un feedback breve, en \
español, dirigido directamente al alumno (segunda persona: "tú"), \
constructivo — señala qué mejorar, no solo si acertó.

Responde SIEMPRE con un objeto JSON con esta forma exacta (sin texto \
antes ni después):

{{"score": 0.0-1.0, "feedback": "..."}}
"""


class GradingResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str


def grade_closed_exercise(exercise_type: str, student_answer: str, answer_key: dict) -> GradingResult:
    """Comparación exacta (sin mayúsculas/espacios) contra answer_key["correct"].
    Determinista a propósito: el alumno debe poder confiar en que un
    ejercicio cerrado se corrige siempre igual, sin la variabilidad de un LLM.
    """
    correct = str(answer_key.get("correct", "")).strip().lower()
    given = student_answer.strip().lower()

    if given == correct:
        return GradingResult(score=1.0, feedback="¡Correcto!")

    return GradingResult(
        score=0.0,
        feedback=f'No es correcto. La respuesta esperada era: "{answer_key.get("correct", "")}".',
    )


async def grade_open_exercise(prompt: str, student_answer: str, level_code: str, model_id: str) -> GradingResult:
    """Nunca lanza: si el LLM no devuelve JSON válido (más probable cuanto
    más pequeño es el modelo), se registra un warning y se devuelve una
    nota neutra en vez de tumbar el envío del alumno — su intento ya
    quedó guardado, solo no se pudo evaluar automáticamente."""
    llm = get_llm(model_id=model_id, temperature=0.2)
    structured_llm = llm.with_structured_output(GradingResult, method="json_mode")

    system_prompt = GRADING_SYSTEM_PROMPT.format(level_code=level_code, prompt=prompt)

    try:
        result = await structured_llm.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=student_answer)]
        )
    except Exception:
        logger.warning("No se pudo obtener una nota estructurada del LLM para este ejercicio", exc_info=True)
        return GradingResult(
            score=0.0,
            feedback="No pudimos evaluar automáticamente esta respuesta. Tu intento quedó guardado igualmente.",
        )

    # Clamp defensivo: un modelo pequeño a veces se sale del rango 0.0-1.0
    # a pesar del Field(ge=0.0, le=1.0) — ese constraint valida el JSON
    # parseado, no evita que el modelo "invente" un número fuera de rango
    # que technically pase la validación si el parseo es laxo.
    score = max(0.0, min(1.0, result.score))
    return GradingResult(score=score, feedback=result.feedback)
