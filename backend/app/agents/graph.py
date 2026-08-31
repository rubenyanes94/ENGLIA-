"""El grafo del tutor, con LangGraph.

Dos nodos que corren en PARALELO (fan-out desde START), no en cadena:

    START ─┬─> generate_response  ──┬─> END
           └─> detect_corrections ──┘

`generate_response` conversa con el alumno (usa TODO el historial).
`detect_corrections` analiza solo el último mensaje del alumno y busca
errores — no necesita esperar a que el otro nodo termine, así que no
pagamos el doble de latencia por tenerlos como pasos separados.

Los siguientes nodos naturales para seguir extendiendo este grafo:
memoria semántica (recuperar resúmenes de sesiones pasadas antes de
generar la respuesta) y moderación/guardrails.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.corrections import detect_corrections as run_correction_detection
from app.agents.llm_client import get_llm
from app.models import AgentPersona


class TutorState(TypedDict):
    # `add_messages` es el "reducer" estándar de LangGraph: en vez de
    # sobrescribir la lista de mensajes en cada paso, la va acumulando.
    messages: Annotated[list[AnyMessage], add_messages]
    system_prompt: str
    model_id: str
    temperature: float

    # Para el nodo de corrección: el mensaje crudo del alumno (sin el
    # historial ni el prompt del tutor) y el nivel MCER, para calibrar
    # cuánto exigir.
    student_message: str
    level_code: str
    corrections: list[dict]


async def generate_response(state: TutorState) -> dict:
    llm = get_llm(model_id=state["model_id"], temperature=state["temperature"])
    messages = [SystemMessage(content=state["system_prompt"]), *state["messages"]]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}


async def detect_corrections(state: TutorState) -> dict:
    corrections = await run_correction_detection(
        student_message=state["student_message"],
        level_code=state["level_code"],
        model_id=state["model_id"],
    )
    return {"corrections": corrections}


def build_tutor_graph():
    graph = StateGraph(TutorState)
    graph.add_node("generate_response", generate_response)
    graph.add_node("detect_corrections", detect_corrections)

    # Fan-out: ambos nodos arrancan a la vez desde START...
    graph.add_edge(START, "generate_response")
    graph.add_edge(START, "detect_corrections")
    # ...y el grafo no termina hasta que los dos hayan acabado.
    graph.add_edge("generate_response", END)
    graph.add_edge("detect_corrections", END)

    return graph.compile()


# Se compila una sola vez al importar el módulo; es barato y reutilizable
# entre requests (no guarda estado propio, el estado vive en cada llamada).
tutor_graph = build_tutor_graph()


class TutorTurnResult(TypedDict):
    reply: str
    corrections: list[dict]


async def run_tutor_turn(
    persona: AgentPersona,
    history: list[AnyMessage],
    message: str,
    level_code: str,
    long_term_context: str | None = None,
) -> TutorTurnResult:
    """Ejecuta un turno de conversación con el tutor de una persona/nivel dados.

    `history` es el historial de ESTA sesión, recuperado de Redis (memoria
    de corto plazo). `long_term_context` es distinto: resúmenes de OTRAS
    sesiones pasadas del mismo alumno, recuperados por similitud semántica
    (pgvector) — se inyecta en el system prompt, no en el historial de
    mensajes, porque no son turnos de ESTA conversación.
    """
    system_prompt = persona.system_prompt
    if long_term_context:
        system_prompt += (
            "\n\nContexto de sesiones anteriores con este alumno (para dar continuidad, "
            f"no lo menciones explícitamente salvo que encaje natural):\n{long_term_context}"
        )

    result = await tutor_graph.ainvoke(
        {
            "messages": [*history, HumanMessage(content=message)],
            "system_prompt": system_prompt,
            "model_id": persona.model_id,
            "temperature": persona.temperature,
            "student_message": message,
            "level_code": level_code,
        }
    )
    last_message = result["messages"][-1]
    return TutorTurnResult(reply=last_message.content, corrections=result.get("corrections", []))
