"""Texto-a-voz con Piper — la voz de James.

A diferencia de Ollama (un servicio Docker propio, porque un LLM
necesita un servidor de inferencia siempre corriendo), Piper es una
librería ONNX ligera: carga un modelo de ~60MB y sintetiza en CPU en
segundos. No amerita un contenedor aparte — vive dentro del proceso del
backend, cargando el modelo UNA vez (ver `_get_voice`) y reutilizándolo
en cada síntesis.

Probado de verdad durante el desarrollo (no es código sin verificar como
las pasarelas de pago): generar un WAV de ~5s con el texto de ejemplo
"Hello! My name is James..." funcionó de punta a punta contra la voz
en_US-lessac-medium.
"""

import asyncio
import wave
from io import BytesIO

from piper import PiperVoice

from app.core.config import settings

_voice: PiperVoice | None = None


def _get_voice() -> PiperVoice:
    global _voice
    if _voice is None:
        # Cargar el modelo ONNX es lo caro (~1-2s) — una sola vez por
        # proceso, no en cada síntesis. No hace falta lock: FastAPI con
        # uvicorn corre un solo proceso Python por worker, y esta función
        # solo se llama desde dentro de asyncio.to_thread (ver abajo),
        # nunca concurrentemente desde el propio event loop.
        _voice = PiperVoice.load(settings.tts_voice_model_path)
    return _voice


async def synthesize_to_wav(text: str) -> bytes:
    """Devuelve los bytes de un archivo WAV completo (con cabecera) listo
    para guardar o servir tal cual."""

    def _synthesize() -> bytes:
        voice = _get_voice()
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return buffer.getvalue()

    # ONNX Runtime en CPU es síncrono y bloqueante — lo corremos en un
    # hilo aparte para no congelar el event loop de FastAPI mientras
    # sintetiza (mismo patrón que stripe_gateway.py con el SDK de Stripe).
    return await asyncio.to_thread(_synthesize)


def get_wav_duration_seconds(wav_bytes: bytes) -> float:
    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()
