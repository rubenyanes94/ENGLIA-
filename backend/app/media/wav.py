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


def frames_duration_seconds(
    frames: bytes,
    channels: int = CHANNELS,
    sample_width: int = SAMPLE_WIDTH_BYTES,
    frame_rate: int = SAMPLE_RATE_HZ,
) -> float:
    """Duración de un bloque de PCM crudo, sin escribir un WAV para
    medirlo. Es lo que permite saber en qué segundo empieza y acaba cada
    frase mientras se van concatenando: el sintetizador ya trocea el
    guión para alternar voces, así que la información de tiempo está ahí
    — solo había que anotarla."""
    return len(frames) / (frame_rate * sample_width * channels)


def build_segment_timeline(pieces: list[tuple[str, bool, bytes]], frame_rate: int = SAMPLE_RATE_HZ) -> list[dict]:
    """Convierte los trozos ya sintetizados en una línea de tiempo:
    qué se dice, en qué idioma, y entre qué segundos.

    Los tiempos salen de la duración REAL de cada audio, no de estimar
    por número de caracteres. La estimación se desvía en cuanto hay
    cambios de idioma —el inglés y el español no se hablan al mismo
    ritmo— y en una lección de cuatro minutos el desfase acumulado deja
    el subtítulo señalando una frase que ya pasó.
    """
    timeline: list[dict] = []
    cursor = 0.0
    for text, is_english, frames in pieces:
        duration = frames_duration_seconds(frames, frame_rate=frame_rate)
        timeline.append({
            "text": text,
            "english": is_english,
            "start": round(cursor, 3),
            "end": round(cursor + duration, 3),
        })
        cursor += duration
    return timeline
