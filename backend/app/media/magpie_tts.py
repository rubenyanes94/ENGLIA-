"""Texto-a-voz con NVIDIA Magpie TTS Multilingual (357M), por API.

Por qué existe además de piper_tts.py: Piper NO puede darnos lo que el
producto necesita. Cada voz suya está entrenada en un solo idioma, así
que la explicación en español y el ejemplo en inglés salen
obligatoriamente de dos personas distintas — el alumno oye cambiar al
profesor a mitad de frase. Magpie es un único modelo multilingüe: el
MISMO hablante dice las dos lenguas.

Eso se comprobó contra el servidor, no se dio por hecho: pidiendo la
subvoz "ES-US.Diego" con language_code "en-US" el servidor sintetiza sin
error. Es lo que permite que `voice_en` y `voice_es` sean el mismo
hablante (ver core/config.py).

gRPC y no HTTP: los microservicios de voz de NVIDIA (Riva) se exponen
por gRPC en NVCF, a diferencia de los LLM del catálogo, que sí son
HTTP compatible-con-OpenAI. Por eso aquí hace falta `nvidia-riva-client`
y una function-id, en vez de un simple POST.
"""

import asyncio

import riva.client
from riva.client.proto.riva_audio_pb2 import AudioEncoding

from app.core.config import settings
from app.media.piper_tts import ENGLISH_SEGMENT_PATTERN, _has_speakable_content
from app.media.wav import build_segment_timeline, build_wav

# Un cliente por proceso: abrir el canal gRPC y negociar TLS cuesta, y
# reabrirlo por cada fragmento del guión multiplicaría ese coste por
# treinta. Mismo motivo que el caché de voces ONNX de Piper.
_service: riva.client.SpeechSynthesisService | None = None


def _get_service() -> riva.client.SpeechSynthesisService:
    global _service
    if _service is None:
        if not settings.nvidia_api_key:
            raise RuntimeError(
                "Falta NVIDIA_API_KEY: Magpie es un servicio remoto y sin clave no "
                "puede sintetizar. Ponla en .env o cambia TTS_PROVIDER a 'piper'."
            )
        auth = riva.client.Auth(
            uri=settings.magpie_grpc_uri,
            use_ssl=True,
            metadata_args=[
                ["function-id", settings.magpie_function_id],
                ["authorization", f"Bearer {settings.nvidia_api_key}"],
            ],
        )
        _service = riva.client.SpeechSynthesisService(auth)
    return _service


def _synthesize_frames(text: str, voice: str, language_code: str) -> bytes:
    """Devuelve PCM crudo (sin cabecera WAV), para poder concatenar los
    fragmentos español/inglés en un solo archivo — igual que en Piper."""
    response = _get_service().synthesize(
        text,
        voice,
        language_code,
        sample_rate_hz=settings.magpie_sample_rate_hz,
        encoding=AudioEncoding.LINEAR_PCM,
    )
    return response.audio


async def synthesize_bilingual_to_wav(script: str) -> tuple[bytes, list[dict]]:
    """Narra un guión mixto: el español con `magpie_voice_es` y los
    fragmentos entre [[corchetes]] con `magpie_voice_en`.

    Devuelve el WAV y la línea de tiempo de cada frase (ver
    wav.build_segment_timeline), que es lo que permite al reproductor ir
    mostrando el texto según se dice.

    Misma firma y mismo protocolo de marcado que la función homónima de
    piper_tts, a propósito: cambiar de motor no debe obligar a reescribir
    ni un guión.
    """

    def _synthesize() -> tuple[bytes, list[dict]]:
        segments: list[tuple[str, str, str]] = []  # (texto, voz, idioma)
        cursor = 0
        for match in ENGLISH_SEGMENT_PATTERN.finditer(script):
            spanish_part = script[cursor : match.start()].strip()
            if _has_speakable_content(spanish_part):
                segments.append((spanish_part, settings.magpie_voice_es, "es-US"))
            english_part = match.group(1).strip()
            if _has_speakable_content(english_part):
                segments.append((english_part, settings.magpie_voice_en, "en-US"))
            cursor = match.end()

        tail = script[cursor:].strip()
        if _has_speakable_content(tail):
            segments.append((tail, settings.magpie_voice_es, "es-US"))

        if not segments:
            if not _has_speakable_content(script):
                raise ValueError("El guión no tiene texto pronunciable.")
            segments = [(script.strip(), settings.magpie_voice_es, "es-US")]

        pieces = [
            (text, lang == "en-US", _synthesize_frames(text, voice, lang))
            for text, voice, lang in segments
        ]
        timeline = build_segment_timeline(pieces, frame_rate=settings.magpie_sample_rate_hz)
        wav = build_wav(b"".join(frames for _, _, frames in pieces), frame_rate=settings.magpie_sample_rate_hz)
        return wav, timeline

    # El cliente de Riva es gRPC SÍNCRONO y bloqueante: fuera del event
    # loop, igual que Piper (que bloquea por ONNX en CPU, no por red).
    return await asyncio.to_thread(_synthesize)
