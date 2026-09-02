"""El grafo del tutor, con LangGraph.

Tres nodos que corren en PARALELO (fan-out desde START), no en cadena:

    START ─┬─> generate_response  ──┬─> END
           ├─> detect_corrections ──┤
           └─> evaluate_active_task ┘

`generate_response` conversa con el alumno (usa TODO el historial, con
el system prompt compuesto por app.agents.prompt_builder — persona +
política del nivel + tutor_config/l1_interference del módulo activo +
tarea activa, si las hay). `detect_corrections` analiza solo el último
mensaje del alumno y busca errores. `evaluate_active_task` solo hace
trabajo real si hay una tarea activa (ver app/agents/task_evaluation.py);
si no la hay, devuelve de inmediato sin llamar al LLM. Ninguno depende
del resultado de otro, así que no pagamos latencia extra por tenerlos
como pasos separados.

El siguiente nodo natural para seguir extendiendo este grafo: memoria
semántica de largo plazo ANTES de generar la respuesta (hoy se resuelve
fuera del grafo, en routers/chat.py) y moderación/guardrails.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.corrections import detect_corrections as run_correction_detection
from app.agents.llm_client import get_llm
from app.agents.prompt_builder import build_system_prompt
from app.agents.task_evaluation import evaluate_task as run_task_evaluation
from app.models import AgentPersona, Module


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

    # Para evaluate_active_task: la tarea concreta que el alumno está
    # practicando (un elemento de Module.tasks), o None si esta sesión no
    # está atada a una — y el último turno del tutor, para poder juzgar
    # si hubo andamiaje directo. Ambos None/vacío = el nodo no hace nada.
    active_task: dict | None
    previous_tutor_message: str | None
    task_completed: bool
    task_scaffolded: bool


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


async def evaluate_active_task(state: TutorState) -> dict:
    task = state.get("active_task")
    if not task:
        return {"task_completed": False, "task_scaffolded": False}

    previous_tutor_message = state.get("previous_tutor_message")
    result = await run_task_evaluation(
        student_message=state["student_message"],
        previous_tutor_message=previous_tutor_message,
        task_prompt=task["prompt"],
        success_criteria=task.get("success_criteria", ""),
        level_code=state["level_code"],
        model_id=state["model_id"],
    )

    # Override determinista: sin turno previo del tutor, el andamiaje es
    # IMPOSIBLE por definición — no dependemos del juicio del LLM para
    # esto (un modelo pequeño puede equivocarse aquí pese a la instrucción
    # explícita del prompt, y esto sí lo sabemos con certeza en código).
    scaffolded = result.scaffolded and previous_tutor_message is not None

    return {"task_completed": result.task_completed, "task_scaffolded": scaffolded}


def build_tutor_graph():
    graph = StateGraph(TutorState)
    graph.add_node("generate_response", generate_response)
    graph.add_node("detect_corrections", detect_corrections)
    graph.add_node("evaluate_active_task", evaluate_active_task)

    # Fan-out: los tres nodos arrancan a la vez desde START...
    graph.add_edge(START, "generate_response")
    graph.add_edge(START, "detect_corrections")
    graph.add_edge(START, "evaluate_active_task")
    # ...y el grafo no termina hasta que los tres hayan acabado.
    graph.add_edge("generate_response", END)
    graph.add_edge("detect_corrections", END)
    graph.add_edge("evaluate_active_task", END)

    return graph.compile()


# Se compila una sola vez al importar el módulo; es barato y reutilizable
# entre requests (no guarda estado propio, el estado vive en cada llamada).
tutor_graph = build_tutor_graph()


class TutorTurnResult(TypedDict):
    reply: str
    corrections: list[dict]
    task_completed: bool
    task_scaffolded: bool


def _find_previous_tutor_message(history: list[AnyMessage]) -> str | None:
    """El último turno del ASISTENTE en el historial (no del alumno) —
    evaluate_active_task lo necesita para juzgar si hubo andamiaje."""
    for m in reversed(history):
        if isinstance(m, AIMessage):
            return m.content
    return None


async def run_tutor_turn(
    persona: AgentPersona,
    history: list[AnyMessage],
    message: str,
    level_code: str,
    module: Module | None = None,
    active_task: dict | None = None,
    long_term_context: str | None = None,
) -> TutorTurnResult:
    """Ejecuta un turno de conversación con el tutor de una persona/nivel dados.

    `history` es el historial de ESTA sesión, recuperado de Redis (memoria
    de corto plazo). `module`/`active_task` son lo que conecta el
    currículo real (tutor_config, l1_interference, tareas comunicativas)
    con este turno — ver app.agents.prompt_builder. `long_term_context` es
    distinto: resúmenes de OTRAS sesiones pasadas del mismo alumno,
    recuperados por similitud semántica (pgvector) — se inyecta en el
    system prompt, no en el historial de mensajes, porque no son turnos
    de ESTA conversación.
    """
    system_prompt = build_system_prompt(persona, module, active_task, long_term_context)

    result = await tutor_graph.ainvoke(
        {
            "messages": [*history, HumanMessage(content=message)],
            "system_prompt": system_prompt,
            "model_id": persona.model_id,
            "temperature": persona.temperature,
            "student_message": message,
            "level_code": level_code,
            "active_task": active_task,
            "previous_tutor_message": _find_previous_tutor_message(history),
        }
    )
    last_message = result["messages"][-1]
    return TutorTurnResult(
        reply=last_message.content,
        corrections=result.get("corrections", []),
        task_completed=result.get("task_completed", False),
        task_scaffolded=result.get("task_scaffolded", False),
    )
