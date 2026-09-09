"""Endpoint de práctica de pronunciación: el alumno graba, el modelo escucha.

Va en su propio router y no dentro de /chat porque no es una
conversación: es un intento puntual contra una frase concreta de la
lección, sin historial ni sesión que mantener.
"""

import wave
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.agents.pronunciation import evaluate_pronunciation
from app.core.config import settings
from app.core.deps import get_current_user
from app.models import User
from app.schemas.pronunciation import PronunciationFeedbackOut

router = APIRouter(prefix="/pronunciation", tags=["pronunciation"])

# 15s es de sobra para una frase de A1 ("Nice to meet you"). El tope no es
# por coste sino por sentido: si alguien manda dos minutos de audio, no
# está practicando una frase — está haciendo otra cosa, y evaluarlo contra
# una frase concreta daría un resultado sin significado.
MAX_AUDIO_SECONDS = 15


@router.post("/attempts", response_model=PronunciationFeedbackOut, status_code=status.HTTP_200_OK)
async def evaluate_attempt(
    audio: UploadFile = File(..., description="WAV mono con la grabación del alumno"),
    expected: str = Form(..., min_length=1, max_length=300, description="La frase que debía decir"),
    level_code: str = Form("A1"),
    current_user: User = Depends(get_current_user),
) -> PronunciationFeedbackOut:
    content = await audio.read()

    if len(content) > settings.pronunciation_max_audio_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"El audio supera {settings.pronunciation_max_audio_bytes // (1024 * 1024)} MB.",
        )

    # Se valida que sea WAV de verdad ABRIÉNDOLO, no mirando el
    # content-type: la cabecera la elige quien sube el archivo, y esto
    # reenvía el contenido a un tercero. Si no abre como WAV, no sale de aquí.
    try:
        with wave.open(BytesIO(content), "rb") as wav_file:
            seconds = wav_file.getnframes() / wav_file.getframerate()
    except (wave.Error, EOFError, ZeroDivisionError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no es un WAV válido.")

    if seconds > MAX_AUDIO_SECONDS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"La grabación dura {seconds:.0f}s; el máximo para una frase es {MAX_AUDIO_SECONDS}s.",
        )

    feedback = await evaluate_pronunciation(content, expected, level_code)
    return PronunciationFeedbackOut(
        transcript=feedback.transcript,
        matches=feedback.matches,
        score=feedback.score,
        feedback_es=feedback.feedback_es,
        expected=expected,
    )
