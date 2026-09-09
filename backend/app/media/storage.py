"""Almacenamiento de archivos: audio de lecciones y fotos de perfil.

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
AVATARS_DIR = Path(settings.media_root) / "avatars"

# Formatos aceptados para la foto de perfil, mapeados a su extensión. La
# lista es blanca (no negra) a propósito: aceptar "cualquier cosa que no
# esté prohibida" es como se cuelan SVGs con <script> dentro, que el
# navegador ejecutaría al servirlos desde nuestro propio dominio.
ALLOWED_AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB


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


def save_avatar(user_id: uuid.UUID, image_bytes: bytes, content_type: str) -> str:
    """Guarda la foto de perfil y devuelve su URL pública (relativa).

    El nombre lo componemos NOSOTROS (user_id + sufijo aleatorio +
    extensión derivada del content-type validado), nunca el nombre de
    archivo que manda el cliente: un `filename` con "../" o con doble
    extensión (foto.jpg.html) es el camino directo a escribir fuera del
    directorio o a servir HTML desde nuestro dominio.

    El sufijo aleatorio además rompe la caché del navegador al cambiar de
    foto — sin él, la URL sería idéntica y el usuario seguiría viendo la
    anterior.
    """
    extension = ALLOWED_AVATAR_TYPES[content_type]
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}-{uuid.uuid4().hex[:8]}{extension}"
    (AVATARS_DIR / filename).write_bytes(image_bytes)
    return f"/media/avatars/{filename}"


def delete_avatar(avatar_url: str) -> None:
    """Borra una foto de perfil anterior. No lanza si ya no está, por la
    misma razón que delete_lesson_audio."""
    filename = avatar_url.rsplit("/", 1)[-1]
    (AVATARS_DIR / filename).unlink(missing_ok=True)
