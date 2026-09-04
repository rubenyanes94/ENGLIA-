"""Texto-a-voz con Piper — la voz del tutor.

A diferencia de Ollama (un servicio Docker propio, porque un LLM
necesita un servidor de inferencia siempre corriendo), Piper es una
librería ONNX ligera: carga un modelo de ~60MB y sintetiza en CPU en
segundos. No amerita un contenedor aparte — vive dentro del proceso del
backend, cargando cada modelo UNA vez (ver `_get_voice`) y
reutilizándolo en cada síntesis.

DOS voces, no una: la lección se explica en ESPAÑOL y los ejemplos se
dicen en INGLÉS (ver synthesize_bilingual_to_wav). Con una sola voz, una
de las dos partes sale mal — y si la que sale mal es el inglés, la app
estaría enseñando pronunciación incorrecta, que es peor que no tener
audio.
"""

import asyncio
import re
import wave
from io import BytesIO

from piper import PiperVoice

from app.core.config import settings

# Cache de voces por ruta de modelo: cargar el ONNX cuesta ~1-2s y no
# tiene sentido repetirlo por cada síntesis. Un dict y no una global
# suelta porque ahora hay más de una voz viva a la vez.
_voices: dict[str, PiperVoice] = {}

# El guión marca los fragmentos en inglés entre [[dobles corchetes]]
# (ver app/agents/lesson_narration.py). Se eligió ese delimitador porque
# no aparece de forma natural en español ni en inglés — a diferencia de
# comillas o asteriscos, que el LLM usa por su cuenta constantemente.
ENGLISH_SEGMENT_PATTERN = re.compile(r"\[\[(.+?)\]\]", re.DOTALL)


def _get_voice(model_path: str) -> PiperVoice:
    if model_path not in _voices:
        # No hace falta lock: esto solo se llama desde dentro de
        # asyncio.to_thread (ver abajo), nunca concurrentemente desde el
        # propio event loop.
        _voices[model_path] = PiperVoice.load(model_path)
    return _voices[model_path]


def _synthesize_frames(text: str, model_path: str) -> tuple[bytes, tuple]:
    """Sintetiza y devuelve (frames crudos, parámetros del WAV). Se
    devuelven los frames sin cabecera para poder concatenar varios
    fragmentos en un único archivo."""
    voice = _get_voice(model_path)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    buffer.seek(0)
    with wave.open(buffer, "rb") as wav_file:
        return wav_file.readframes(wav_file.getnframes()), wav_file.getparams()


async def synthesize_to_wav(text: str) -> bytes:
    """Síntesis simple con la voz inglesa. Se mantiene para cualquier uso
    monolingüe; la narración de lecciones usa synthesize_bilingual_to_wav."""

    def _synthesize() -> bytes:
        frames, params = _synthesize_frames(text, settings.tts_voice_model_path)
        return _build_wav(frames, params)

    # ONNX Runtime en CPU es síncrono y bloqueante — lo corremos en un
    # hilo aparte para no congelar el event loop de FastAPI mientras
    # sintetiza (mismo patrón que stripe_gateway.py con el SDK de Stripe).
    return await asyncio.to_thread(_synthesize)


async def synthesize_bilingual_to_wav(script: str) -> bytes:
    """Narra un guión mixto: español con la voz española, y los
    fragmentos marcados entre [[corchetes]] con la voz inglesa.

    Ambos modelos son 22050 Hz mono, así que los fragmentos se concatenan
    tal cual, sin remuestrear. Si algún día se cambia una voz por otra de
    distinto sample rate, esto lanzará en vez de producir audio a
    velocidad equivocada (ver la comprobación de params).
    """

    def _synthesize() -> bytes:
        segments: list[tuple[str, str]] = []  # (texto, ruta del modelo)
        cursor = 0
        for match in ENGLISH_SEGMENT_PATTERN.finditer(script):
            spanish_part = script[cursor : match.start()].strip()
            if spanish_part:
                segments.append((spanish_part, settings.tts_voice_model_path_es))
            english_part = match.group(1).strip()
            if english_part:
                segments.append((english_part, settings.tts_voice_model_path))
            cursor = match.end()

        tail = script[cursor:].strip()
        if tail:
            segments.append((tail, settings.tts_voice_model_path_es))

        # Guión sin ninguna marca: se narra entero en español.
        if not segments:
            segments = [(script.strip(), settings.tts_voice_model_path_es)]

        all_frames = b""
        base_params = None
        for text, model_path in segments:
            frames, params = _synthesize_frames(text, model_path)
            if base_params is None:
                base_params = params
            elif (params.nchannels, params.sampwidth, params.framerate) != (
                base_params.nchannels,
                base_params.sampwidth,
                base_params.framerate,
            ):
                raise ValueError(
                    "Las voces de Piper configuradas tienen formatos de audio distintos "
                    "(canales/bits/sample rate); no se pueden concatenar sin remuestrear."
                )
            all_frames += frames

        return _build_wav(all_frames, base_params)

    return await asyncio.to_thread(_synthesize)


def _build_wav(frames: bytes, params) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(params.nchannels)
        wav_file.setsampwidth(params.sampwidth)
        wav_file.setframerate(params.framerate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


def get_wav_duration_seconds(wav_bytes: bytes) -> float:
    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def strip_english_markers(script: str) -> str:
    """Quita los [[corchetes]] para MOSTRAR el guión como subtítulo. El
    texto marcado se conserva: solo desaparecen las marcas, que son una
    instrucción para el sintetizador, no algo que el alumno deba leer."""
    return ENGLISH_SEGMENT_PATTERN.sub(r"\1", script)
