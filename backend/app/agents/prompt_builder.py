"""Compone el system prompt real que ve el LLM en cada turno, cruzando
las capas de configuración pedagógica que hasta ahora vivían en la base
de datos SIN que ningún código las leyera:

1. AgentPersona.system_prompt — la personalidad base del tutor, por NIVEL.
2. CEFRLevel.tutor_policy — el "level_policy" del documento de currículo
   (techo de lenguaje, velocidad de habla, jerarquía de corrección...),
   heredado por todos los módulos del nivel.
3. Module.tutor_config + Module.l1_interference — el contrato de
   comportamiento y los errores anticipados de ESTE módulo, solo cuando
   la sesión está atada a uno (ConversationSession.module_id).
4. La tarea activa (un elemento de Module.tasks), si el alumno está
   practicando una en concreto en este turno.

Antes de este archivo, (2), (3) y (4) se guardaban pero nada los usaba —
run_tutor_turn solo montaba (1). Esta es la pieza que convierte
"currículo guardado en la base de datos" en "el tutor se comporta según
el currículo".
"""

from app.models import AgentPersona, Module


def _render_level_policy(policy: dict) -> str:
    if not policy:
        return ""

    lines = ["Política del nivel (aplica salvo que el módulo activo la sobreescriba):"]

    ceiling = policy.get("tutor_language_ceiling") or {}
    if ceiling.get("allowed"):
        lines.append(f"- Estructuras permitidas: {', '.join(ceiling['allowed'])}.")
    if ceiling.get("forbidden"):
        lines.append(
            f"- PROHIBIDO usar o modelar, aunque suene natural: {', '.join(ceiling['forbidden'])}."
        )
    if policy.get("tutor_speech_rate"):
        lines.append(f"- Velocidad de habla: {policy['tutor_speech_rate']}.")
    if policy.get("max_new_lexis_per_session"):
        lines.append(f"- No introduzcas más de {policy['max_new_lexis_per_session']} palabras nuevas por sesión.")
    if policy.get("l1_support"):
        lines.append(f"- Apoyo en español: {policy['l1_support']}")
    if policy.get("correction_hierarchy"):
        lines.append("- Jerarquía de corrección, en este orden de prioridad:")
        lines.extend(f"  {i}. {rule}" for i, rule in enumerate(policy["correction_hierarchy"], start=1))

    return "\n".join(lines)


def _render_module_context(module: Module) -> str:
    lines = [f'Módulo activo: "{module.title}" ({module.title_es or module.title}).']

    if module.communicative_objectives:
        lines.append("Objetivos comunicativos de este módulo:")
        lines.extend(f"- {objective}" for objective in module.communicative_objectives)

    tutor_config = module.tutor_config or {}
    if tutor_config.get("persona"):
        lines.append(f"Personalidad para este módulo: {tutor_config['persona']}")
    if tutor_config.get("speech_rate"):
        lines.append(f"Velocidad de habla de este módulo (sobreescribe la del nivel): {tutor_config['speech_rate']}.")
    if tutor_config.get("correction_policy"):
        lines.append(f"Política de corrección de este módulo: {tutor_config['correction_policy']}")
    if tutor_config.get("scaffolds"):
        lines.append('Ayudas ("scaffolds") que SÍ puedes ofrecer si el alumno se bloquea:')
        lines.extend(f"- {scaffold}" for scaffold in tutor_config["scaffolds"])
    if tutor_config.get("forbidden"):
        lines.append("PROHIBIDO en este módulo:")
        lines.extend(f"- {item}" for item in tutor_config["forbidden"])

    l1_interference = module.l1_interference or []
    if l1_interference:
        lines.append(
            "Errores que un hispanohablante probablemente cometerá en este módulo — "
            "anticípalos y aplica la jerarquía de corrección del nivel según su severidad "
            "(nunca ignores 'critical', prioriza 'high', deja pasar 'low' salvo que rompa "
            "la comunicación):"
        )
        for item in l1_interference:
            note = f" — {item['note']}" if item.get("note") else ""
            lines.append(f"- [{item.get('severity', 'medium')}] \"{item['error']}\" → \"{item['target']}\"{note}")

    return "\n".join(lines)


def _render_active_task(task: dict) -> str:
    lines = [
        "TAREA ACTIVA: el alumno está practicando esta tarea comunicativa concreta "
        "ahora mismo — guía la conversación para que la complete, esto no es charla "
        "libre. Al final se evaluará si la logró.",
        f"- Instrucción: {task['prompt']}",
    ]
    if task.get("success_criteria"):
        lines.append(f"- Se considera lograda si: {task['success_criteria']}")
    if task.get("note"):
        lines.append(f"- Nota pedagógica: {task['note']}")
    return "\n".join(lines)


def build_system_prompt(
    persona: AgentPersona,
    module: Module | None = None,
    active_task: dict | None = None,
    long_term_context: str | None = None,
) -> str:
    parts = [persona.system_prompt]

    level_policy_text = _render_level_policy((persona.level.tutor_policy or {}) if persona.level else {})
    if level_policy_text:
        parts.append(level_policy_text)

    if module is not None:
        parts.append(_render_module_context(module))

    if active_task is not None:
        parts.append(_render_active_task(active_task))

    if long_term_context:
        parts.append(
            "Contexto de sesiones anteriores con este alumno (para dar continuidad, "
            f"no lo menciones explícitamente salvo que encaje natural):\n{long_term_context}"
        )

    return "\n\n".join(parts)
