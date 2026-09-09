"""Moderación del chat con nemotron-3.5-content-safety.

Espikin tiene chat de texto libre y alumnos que muy probablemente son
menores. Eso obliga a mirar las DOS direcciones, no solo una:

- Lo que ESCRIBE el alumno. El caso que más importa no es el insulto,
  es el niño que suelta su dirección y su teléfono en el chat. Se
  comprobó: el modelo marca como insegura "Tengo 12 años y vivo en Av.
  Bolívar 45, mi teléfono es...".
- Lo que RESPONDE el tutor. Un LLM puede producir algo inadecuado aunque
  el alumno no lo haya provocado, y aquí quien habla lleva nuestra marca.

Ambas verificaciones caben en UNA llamada: pasando el turno completo
(mensaje del alumno + respuesta del tutor) el modelo devuelve
"User Safety" y "Response Safety" por separado. Medido: 0.1-0.9s, lo que
hace viable moderar cada turno sin que el alumno lo note.

El modelo NO devuelve categorías, solo safe/unsafe — se intentó pedirlas
con un system prompt al estilo Aegis y sigue devolviendo el veredicto a
secas. Por eso el aviso al alumno es genérico: no podemos decirle "no
compartas tu dirección" porque no sabemos que ESE fue el motivo, y
adivinarlo sería peor que ser vagos.
"""

import logging
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessage

from app.agents.llm_client import ainvoke_serialized, get_llm
from app.core.config import settings

logger = logging.getLogger(__name__)

_VERDICT = re.compile(r"^\s*(User|Response)\s+Safety:\s*(safe|unsafe)", re.IGNORECASE | re.MULTILINE)


@dataclass
class ModerationVerdict:
    user_safe: bool
    response_safe: bool
    # False cuando la comprobación no se pudo hacer (proveedor caído,
    # respuesta ilegible). Se distingue de "salió segura" a propósito:
    # "no lo sabemos" y "lo revisamos y está bien" no son lo mismo, y
    # mezclarlos haría imposible auditar después cuántos turnos pasaron
    # sin revisar.
    checked: bool = True

    @property
    def blocked(self) -> bool:
        return not (self.user_safe and self.response_safe)


def _parse(raw: str) -> ModerationVerdict:
    verdicts = {kind.lower(): value.lower() == "safe" for kind, value in _VERDICT.findall(raw)}
    if "user" not in verdicts:
        raise ValueError(f"Veredicto de moderación ilegible: {raw[:120]!r}")
    # "Response Safety" solo aparece si se mandó una respuesta que juzgar.
    return ModerationVerdict(user_safe=verdicts["user"], response_safe=verdicts.get("response", True))


async def moderate_turn(student_message: str, tutor_reply: str | None) -> ModerationVerdict:
    """Revisa un turno completo. Nunca lanza.

    FALLA EN ABIERTO — si la moderación no se puede hacer, el turno pasa
    marcado como no revisado. Es una decisión deliberada y discutible, así
    que conviene entender el porqué antes de invertirla: fallar en cerrado
    convertiría cualquier hipo del proveedor de moderación en una caída
    TOTAL de las clases (el tutor respondería "no puedo contestar" a
    todo), y ya vimos un 503 pasajero de este mismo catálogo. El daño de
    dejar pasar un mensaje sin revisar durante un incidente es pequeño y
    acotado; el de dejar sin clase a todos los alumnos, no.

    Si el producto pasa a un contexto de más riesgo (menores sin
    supervisión, chat entre alumnos), esta decisión hay que revisarla.
    """
    if not settings.moderation_enabled:
        return ModerationVerdict(user_safe=True, response_safe=True, checked=False)

    llm = get_llm(model_id=settings.moderation_model, temperature=0.0, max_tokens=100)
    messages: list = [HumanMessage(content=student_message)]
    if tutor_reply:
        messages.append(AIMessage(content=tutor_reply))

    try:
        response = await ainvoke_serialized(lambda: llm.ainvoke(messages))
        return _parse(response.content)
    except Exception as exc:  # noqa: BLE001 — ver "falla en abierto" arriba
        logger.warning("Moderación no disponible, el turno pasa sin revisar: %s", exc)
        return ModerationVerdict(user_safe=True, response_safe=True, checked=False)
