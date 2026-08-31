"""Detección de errores gramaticales — segundo nodo del grafo del tutor.

Analiza ÚNICAMENTE el mensaje del alumno (no la respuesta del tutor) y
devuelve una lista estructurada de errores, con la MISMA forma que la
columna JSONB `corrections` de `conversation_messages`. Así, lo que sale
de aquí se persiste directo, sin transformación.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm_client import get_llm

logger = logging.getLogger(__name__)

CORRECTION_SYSTEM_PROMPT = """\
Eres un corrector gramatical de inglés para estudiantes hispanohablantes \
de nivel MCER {level_code}.

Analiza EXCLUSIVAMENTE el mensaje del alumno (no generes conversación, \
no respondas al alumno) y detecta errores de gramática, vocabulario u \
ortografía en inglés.

Reglas:
- Si el alumno no cometió ningún error, devuelve una lista vacía.
- No inventes errores que no existen. Ante la duda, no lo marques como error.
- Ajusta la exigencia al nivel indicado: en A1/A2 señala solo errores \
básicos evidentes; en B1/B2 errores de estructura y tiempos verbales; \
en C1/C2 señala solo matices de registro o naturalidad, nunca gramática \
básica.
- Las explicaciones ("rule") van en español, breves (una frase).

Responde SIEMPRE con un objeto JSON con esta forma exacta (sin texto \
antes ni después):

{{"corrections": [{{"error": "...", "correction": "...", "rule": "..."}}]}}

Ejemplo. Mensaje del alumno: "Yesterday I go to the store and I buyed milk."
Respuesta correcta:
{{"corrections": [
  {{"error": "I go", "correction": "I went", "rule": "Con 'yesterday' se usa pasado simple, no presente."}},
  {{"error": "I buyed", "correction": "I bought", "rule": "'Buy' es un verbo irregular: su pasado es 'bought', no 'buyed'."}}
]}}

Ejemplo. Mensaje del alumno: "I am very happy today."
Respuesta correcta (sin errores):
{{"corrections": []}}
"""


class GrammarError(BaseModel):
    error: str = Field(description="Fragmento exacto del mensaje del alumno que contiene el error")
    correction: str = Field(description="Cómo debería haberse escrito ese fragmento")
    rule: str = Field(description="Explicación breve, en español, de por qué es un error")


class CorrectionsResult(BaseModel):
    corrections: list[GrammarError]


async def detect_corrections(student_message: str, level_code: str, model_id: str) -> list[dict]:
    """Devuelve una lista de dicts (posiblemente vacía). Nunca lanza: si el
    modelo no logra devolver JSON válido (más probable cuanto más pequeño
    es el modelo), se registra un warning y se responde "sin errores
    detectados" en vez de tumbar el turno de conversación completo."""
    llm = get_llm(model_id=model_id, temperature=0.1)
    structured_llm = llm.with_structured_output(CorrectionsResult, method="json_mode")

    prompt = CORRECTION_SYSTEM_PROMPT.format(level_code=level_code)

    try:
        result = await structured_llm.ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content=student_message)]
        )
    except Exception:
        logger.warning("No se pudo obtener corrections estructuradas del LLM", exc_info=True)
        return []

    # Filtro defensivo: un modelo pequeño a veces "alucina" una corrección
    # idéntica al original (falso positivo). Si error == correction, no es
    # una corrección real — descartarla es más honesto que mostrarla.
    return [
        error.model_dump()
        for error in result.corrections
        if error.error.strip().lower() != error.correction.strip().lower()
    ]
