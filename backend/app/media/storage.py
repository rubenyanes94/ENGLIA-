"""Almacenamiento de archivos generados — hoy, solo audio de lecciones.

Disco local + un volumen Docker dedicado (ver docker-compose.yml),
servido como estáticos por FastAPI en /media (ver app/main.py). Alcanza
para un único contenedor backend. Si el día de mañana hace falta un CDN
o varias réplicas, este archivo es lo ÚNICO que habría que tocar — el
resto del código solo conoce "una URL", nunca una ruta de disco.
"""

import uuid
from pathlib import Path

from app.core.config import settings

LESSONS_AUDIO_DIR = Path(settings.media_root) / "lessons"


def save_lesson_audio(lesson_id: uuid.UUID, wav_bytes: bytes) -> str:
    """Guarda el WAV y devuelve la URL pública (relativa) para servirlo.

    El nombre del archivo incluye un sufijo aleatorio, no solo
    lesson_id: así, si algo cachea la URL vieja mientras se regenera el
    guión, sigue apuntando al audio anterior (todavía válido) en vez de
    a un archivo a medio escribir. El router es responsable de borrar el
    archivo anterior DESPUÉS de guardar el nuevo con éxito (ver
    delete_lesson_audio) — nunca antes, para no perder el único audio
    servible si la síntesis fallara a mitad de camino.
    """
    LESSONS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{lesson_id}-{uuid.uuid4().hex[:8]}.wav"
    (LESSONS_AUDIO_DIR / filename).write_bytes(wav_bytes)
    return f"/media/lessons/{filename}"


def delete_lesson_audio(audio_url: str) -> None:
    """Borra un audio de lección previamente guardado, a partir de la URL
    que devolvió save_lesson_audio. Nunca lanza si el archivo ya no
    existe (ej. lo borraron a mano, o esto se llama dos veces) — borrar
    algo que ya no está no es un error del que valga la pena tumbar el request."""
    filename = audio_url.rsplit("/", 1)[-1]
    (LESSONS_AUDIO_DIR / filename).unlink(missing_ok=True)
