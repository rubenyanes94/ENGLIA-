"""Punto único de entrada a la síntesis de voz.

Quien narre una lección (el router de admin, los scripts de siembra) no
debe saber si detrás hay Piper corriendo en este proceso o Magpie al otro
lado de una API: importa de aquí y ya. Cambiar de motor es cambiar
TTS_PROVIDER en .env, sin tocar una línea de los llamadores.

Los dos motores comparten el mismo protocolo de guión — español corrido
con el inglés entre [[dobles corchetes]] — precisamente para que la
biblioteca de guiones ya escrita siga sirviendo si se cambia de motor.
"""

from app.core.config import settings
from app.media.wav import get_wav_duration_seconds  # noqa: F401 — re-exportado

PROVIDERS = ("piper", "magpie")


async def synthesize_bilingual_to_wav(script: str) -> tuple[bytes, list[dict]]:
    """Devuelve (WAV, línea de tiempo). La línea de tiempo dice qué frase
    suena entre qué segundos, y es lo que permite que el reproductor vaya
    mostrando el texto conforme se dice en vez de un muro estático."""
    # Import perezoso y no arriba: importar magpie_tts arrastra el cliente
    # gRPC de Riva, y importar piper_tts carga la librería ONNX. Quien use
    # solo uno de los dos motores no debería pagar el arranque del otro.
    if settings.tts_provider == "magpie":
        from app.media import magpie_tts

        return await magpie_tts.synthesize_bilingual_to_wav(script)

    if settings.tts_provider == "piper":
        from app.media import piper_tts

        return await piper_tts.synthesize_bilingual_to_wav(script)

    raise ValueError(f"TTS_PROVIDER desconocido: {settings.tts_provider!r}. Opciones: {PROVIDERS}.")
