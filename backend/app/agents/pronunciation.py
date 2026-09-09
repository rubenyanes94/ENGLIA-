"""Evaluación de pronunciación con nemotron-3-nano-omni.

Es la primera vez que Espikin ESCUCHA al alumno. Hasta ahora todo el
producto era de una sola dirección: el tutor habla y el alumno escribe.
Una academia de idiomas que nunca oye hablar al estudiante no puede
corregir lo único que de verdad cuesta aprender.

El modelo recibe el audio y la frase que se le pidió decir, y devuelve
qué oyó realmente, si coincide, una puntuación y una pista en español.
Comprobado con el error de interferencia L1 más típico del currículo:
grabando "I have twenty five years" cuando tocaba "I am twenty five
years old", devuelve transcript exacto, matches=false, score 35 y
"Asegúrate de usar 'am' y añadir 'old' al final".

El audio viaja como data URI dentro del mensaje (`audio_url`), que es el
formato que este endpoint acepta — el `input_audio` del estándar de
OpenAI no respondió. Se manda WAV porque el navegador ya lo produce así
(ver frontend useVoiceRecorder): no hay transcodificación en el
servidor, y por tanto no hace falta ffmpeg en la imagen.
"""

import base64
import json
import logging
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage

from app.agents.llm_client import ainvoke_serialized, get_llm
from app.core.config import settings

logger = logging.getLogger(__name__)

# Dos ejes distintos, separados a propósito. Sin esta distinción el
# modelo los mezcla y produce consejos incoherentes: ante un alumno que
# dijo "I have twenty five years" en vez de "I am twenty five years old",
# devolvió "Pronuncia 'I have' como 'I have'" — una pista de
# pronunciación para un error que era de palabras.
PROMPT = """A Spanish-speaking student learning English at CEFR level {level_code} was asked to say this out loud:

"{expected}"

Listen to the recording. Judge TWO different things and do not mix them up:

1. WORDS — did they say the right words? If they said different words
   (for example "I have 25 years" instead of "I am 25 years old"), that
   is a WORDING mistake, not a pronunciation one. Set matches=false and
   make the tip about which words to use.

2. PRONUNCIATION — if the words are right, how natural do they sound?
   Only then should the tip be about sounds, stress or rhythm.

Reply with nothing but JSON, no markdown fence:
{{"transcript": "<exactly what you hear, in English — do not correct it>",
  "matches": <true only if the words match the target phrase>,
  "score": <0-100. If the words are wrong, score low regardless of how clear the audio is.>,
  "feedback_es": "<ONE short encouraging tip in Latin American Spanish (max 15 words). Say what to DO, never repeat the error as if it were correct.>"}}"""


@dataclass
class PronunciationFeedback:
    transcript: str
    matches: bool
    score: int
    feedback_es: str


def _parse(raw: str) -> PronunciationFeedback:
    # El modelo razona y a veces envuelve el JSON en prosa o en un bloque
    # markdown pese a pedirle lo contrario: se extrae el primer objeto en
    # vez de exigir que la respuesta entera sea JSON válido.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Sin JSON en la respuesta del evaluador: {raw[:150]!r}")
    data = json.loads(match.group(0))

    # El score se acota en vez de confiar: un modelo puede devolver 150 o
    # -10, y ese número se le enseña al alumno como una nota.
    score = max(0, min(100, int(data.get("score", 0))))
    return PronunciationFeedback(
        transcript=str(data.get("transcript", "")).strip(),
        matches=bool(data.get("matches", False)),
        score=score,
        feedback_es=str(data.get("feedback_es", "")).strip(),
    )


async def evaluate_pronunciation(wav_bytes: bytes, expected: str, level_code: str) -> PronunciationFeedback:
    audio_b64 = base64.b64encode(wav_bytes).decode()
    llm = get_llm(model_id=settings.pronunciation_model, temperature=0.0, max_tokens=400)

    message = HumanMessage(content=[
        {"type": "text", "text": PROMPT.format(expected=expected, level_code=level_code)},
        {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{audio_b64}"}},
    ])

    response = await ainvoke_serialized(lambda: llm.ainvoke([message]))
    return _parse(response.content)
