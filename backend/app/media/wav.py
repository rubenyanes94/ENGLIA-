"""Utilidades de WAV compartidas por los motores de voz.

Viven aparte de piper_tts.py porque ahora hay DOS motores (Piper local y
Magpie por API) y los dos hacen lo mismo al final: reciben fragmentos de
audio crudo, sin cabecera, y tienen que pegarlos en un único archivo. Es
la pieza que permite alternar de motor sin duplicar el manejo del
formato.
"""

import wave
from io import BytesIO

# Los dos motores producen 22050 Hz, 16 bits, mono. No es casualidad
# afortunada: es un REQUISITO para poder concatenar fragmentos de idiomas
# distintos sin remuestrear. Si algún día se usa una voz con otro
# formato, hay que convertir antes de pegar, no cambiar esto.
SAMPLE_RATE_HZ = 22050
SAMPLE_WIDTH_BYTES = 2
CHANNELS = 1


def build_wav(
    frames: bytes,
    channels: int = CHANNELS,
    sample_width: int = SAMPLE_WIDTH_BYTES,
    frame_rate: int = SAMPLE_RATE_HZ,
) -> bytes:
    """Envuelve audio PCM crudo en un WAV servible."""
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(frame_rate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


def get_wav_duration_seconds(wav_bytes: bytes) -> float:
    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()
