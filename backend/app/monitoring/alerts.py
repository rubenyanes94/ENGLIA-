"""Reglas que convierten cifras en avisos para el panel de gerencia → Sistema.

Los umbrales están aquí, juntos y a la vista, para poder discutirlos. Son
deliberadamente conservadores: un aviso que salta por cualquier cosa se
acaba ignorando, y entonces tampoco se mira el día que importa.

Cada regla exige un volumen mínimo antes de hablar de porcentajes: con 3
llamadas, que falle 1 es un 33 % que no significa nada.
"""

# Llamadas a Nemotron (última hora)
MIN_CALLS = 5
FAILED_CALLS_WARNING = 0.05
FAILED_CALLS_CRITICAL = 0.20
RETRIED_CALLS_WARNING = 0.10
TUTOR_P95_WARNING_MS = 8_000
QUEUE_P95_WARNING_MS = 2_000

# API HTTP (última hora)
MIN_REQUESTS = 20
SERVER_ERRORS_CRITICAL = 0.05
HTTP_P95_WARNING_MS = 5_000

# Respuestas cortadas por max_tokens (últimas 24 h)
TRUNCATED_WARNING = 0.02


def _pct(fraction: float) -> str:
    """Formato del panel (español): "9 %", "2,9 %". Con un decimal por
    debajo del 10 %, igual que components/charts/format.ts."""
    value = fraction * 100
    text = f"{value:.1f}" if value < 10 else f"{value:.0f}"
    return f"{text.replace('.', ',')} %"


def _secs(ms: float) -> str:
    return f"{ms / 1000:.1f}".replace(".", ",") + " s"


def _alert(severity: str, title: str, detail: str, hint: str | None = None, source: str = "metrics") -> dict:
    return {"severity": severity, "title": title, "detail": detail, "hint": hint, "source": source}


def from_checks(checks: list[dict]) -> list[dict]:
    alerts = []
    for c in checks:
        if c["status"] in ("warning", "critical", "unknown"):
            alerts.append(_alert(
                "critical" if c["status"] == "critical" else "warning",
                c["label"], c["detail"], c.get("hint"), source="check",
            ))
    return alerts


def from_metrics(llm_1h: dict, http_1h: dict, llm_24h: dict, client_errors_24h: int) -> list[dict]:
    alerts = []

    calls = llm_1h["calls"]
    if calls >= MIN_CALLS:
        failed = llm_1h["failed_calls"] / calls
        if failed >= FAILED_CALLS_WARNING:
            alerts.append(_alert(
                "critical" if failed >= FAILED_CALLS_CRITICAL else "warning",
                "Fallan llamadas a Nemotron",
                f"{_pct(failed)} de las llamadas de la última hora fallaron incluso tras reintentar ({llm_1h['failed_calls']} de {calls}).",
                "Al alumno le llega un error o una respuesta sin corregir. Ver 'Fallos recientes' para el tipo de error.",
            ))
        retried = llm_1h["retried_calls"] / calls
        if retried >= RETRIED_CALLS_WARNING:
            alerts.append(_alert(
                "warning", "NVIDIA responde con saturación",
                f"{_pct(retried)} de las llamadas de la última hora necesitaron reintento.",
                "Se recuperan solas, pero cada reintento suma segundos de espera. Si persiste, valorar un plan con más capacidad.",
            ))

    if (llm_1h["tutor_p95_ms"] or 0) > TUTOR_P95_WARNING_MS:
        alerts.append(_alert(
            "warning", "El tutor tarda en responder",
            f"El 5 % más lento de las respuestas de la última hora tardó más de {_secs(llm_1h['tutor_p95_ms'])}.",
            "Por encima de ~8 s la conversación deja de sentirse fluida.",
        ))
    if (llm_1h["queue_p95_ms"] or 0) > QUEUE_P95_WARNING_MS:
        alerts.append(_alert(
            "warning", "Llamadas esperando turno",
            f"Algunas llamadas esperaron {_secs(llm_1h['queue_p95_ms'])} antes de salir hacia NVIDIA.",
            "El límite es nuestro, no de NVIDIA: subir LLM_MAX_CONCURRENCY si el plan lo permite.",
        ))

    if http_1h["server_errors"]:
        rate = http_1h["server_errors"] / http_1h["requests"] if http_1h["requests"] else 1
        alerts.append(_alert(
            "critical" if http_1h["requests"] >= MIN_REQUESTS and rate >= SERVER_ERRORS_CRITICAL else "warning",
            "Errores del servidor",
            f"{http_1h['server_errors']} peticiones con error 5xx en la última hora ({_pct(rate)}).",
            "Cada 5xx es algo que falló en la app. Ver 'Fallos recientes' para la ruta y el error.",
        ))
    if http_1h["requests"] >= MIN_REQUESTS and (http_1h["p95_ms"] or 0) > HTTP_P95_WARNING_MS:
        alerts.append(_alert(
            "warning", "La API va lenta",
            f"El 5 % más lento de las peticiones de la última hora tardó más de {_secs(http_1h['p95_ms'])}.",
            "Ver en 'Rutas más lentas' cuál es.",
        ))

    if llm_24h["chat_ok"] and llm_24h["truncated"] / llm_24h["chat_ok"] >= TRUNCATED_WARNING:
        alerts.append(_alert(
            "warning", "Respuestas cortadas",
            f"{llm_24h['truncated']} respuestas de las últimas 24 h se cortaron por el límite de tokens.",
            "El alumno ve una frase a medias. Subir max_tokens de esa función (ver 'Por función').",
        ))
    if client_errors_24h:
        alerts.append(_alert(
            "warning", "Errores en el navegador",
            f"{client_errors_24h} errores de JavaScript en navegadores de usuarios en las últimas 24 h.",
            "El servidor no los ve: pueden ser pantallas que no cargan. Ver 'Fallos recientes'.",
        ))
    return alerts


def overall(alerts: list[dict]) -> str:
    if any(a["severity"] == "critical" for a in alerts):
        return "critical"
    if alerts:
        return "warning"
    return "ok"
