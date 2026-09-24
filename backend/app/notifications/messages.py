"""Qué dice cada correo. El catálogo entero, en un solo archivo, para
poder leer de corrido todo lo que Espikin le escribe a un alumno.

Se escriben como una notificación del móvil y no como una circular: una
idea por correo, el asunto ya dice todo lo que pasa, y un solo botón. Si
el alumno solo lee el asunto y la primera línea, tiene que haberse
enterado igual.

Los *asteriscos* de los títulos pintan esa parte en violeta (ver
layout._rich). No es un adorno: el titular de la portada también lleva
media frase en color, y es lo que hace que un correo se lea como
nuestro de un vistazo. Va en lo que importa — los días que quedan, el
"ya está activo" —, nunca en la frase entera.

Dos familias, y la diferencia importa:

- **Transaccionales** (bienvenida, pago aprobado, pago rechazado): son la
  respuesta a algo que el alumno acaba de hacer. Se envían siempre,
  aunque se haya dado de baja de los recordatorios, y no llevan enlace de
  baja: nadie debería poder dejar de enterarse de qué pasó con su dinero.
- **De retención** (vence pronto, último día, venció, te echamos de
  menos): los comerciales. Respetan la preferencia del alumno
  (`notifications_enabled`), llevan enlace para darse de baja y se pueden
  apagar todos de golpe con MARKETING_EMAILS_ENABLED.
"""

from app.notifications.layout import Button, Email, Note

# Los comerciales: los de retención y las campañas escritas a mano desde
# gerencia. El resto se envía pase lo que pase.
#
# "campana" no tiene texto aquí a propósito: el suyo lo escribe una
# persona en el panel y vive en la base de datos (app/notifications/
# campaigns.py). Sí está en esta lista porque es publicidad, y por tanto
# respeta la baja y lleva enlace para darse de baja como el resto.
MARKETING_KINDS = {"vence_pronto", "ultimo_dia", "vencio", "te_echamos_de_menos", "campana"}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(value) -> str:
    """date/datetime → "23 de octubre de 2026". A mano y no con strftime
    porque el contenedor no tiene instalada la configuración regional en
    español: %B daría "October"."""
    return f"{value.day} de {MESES[value.month - 1]} de {value.year}"


def nombre_corto(full_name: str) -> str:
    """"Rubén Yánez" → "Rubén". En un asunto, el nombre completo suena a
    carta del banco."""
    return (full_name or "").strip().split(" ")[0] or "hola"


def build(kind: str, *, full_name: str, app_url: str, context: dict) -> Email:
    """Arma el correo `kind` ya personalizado. `context` trae lo que hace
    falta según el tipo (la fecha de vencimiento, el motivo del rechazo)
    y se guarda tal cual en email_messages para poder reconstruirlo."""
    nombre = nombre_corto(full_name)
    aula = f"{app_url}/dashboard"
    pagar = f"{app_url}/suscripcion"

    if kind == "bienvenida":
        return Email(
            subject=f"Bienvenido a Espikin, {nombre}",
            preheader="Tu primera conversación en inglés te espera. Cinco minutos bastan para empezar.",
            eyebrow="Bienvenida",
            title=f"Ya eres parte de *Espikin*, {nombre}",
            paragraphs=[
                "Tus tutores ya están listos para hablar contigo. No son clases grabadas: conversas, te corrigen al momento y avanzas a tu ritmo.",
                "El mejor primer paso son <strong>cinco minutos de conversación</strong>. Con eso ya sabemos por dónde empezar contigo.",
            ],
            button=Button("Empezar mi primera clase", aula),
            context=context,
        )

    if kind == "pago_aprobado":
        return Email(
            subject="Pago confirmado: ya tienes acceso completo",
            preheader="Verificamos tu pago. Tu acceso a Espikin está activo.",
            eyebrow="Pago confirmado",
            title=f"Listo, {nombre}. *Ya está todo activo*",
            paragraphs=["Verificamos tu pago y tu acceso quedó abierto. Puedes entrar a practicar ahora mismo."],
            note=Note("Tu acceso llega hasta el", context["hasta"]),
            button=Button("Entrar a mi aula", aula),
            footnote="Te avisaremos unos días antes de que termine, para que no se te pase.",
            context=context,
        )

    if kind == "pago_rechazado":
        return Email(
            subject="No pudimos confirmar tu pago",
            preheader="Revisa los datos y repórtalo otra vez: es cuestión de un minuto.",
            eyebrow="Revisión de pago",
            title=f"*No pudimos confirmar* tu pago, {nombre}",
            paragraphs=[
                "Revisamos el pago que reportaste y no logramos encontrarlo. No te preocupes: se arregla reportándolo de nuevo con los datos correctos.",
            ],
            note=Note("Lo que vimos", context["motivo"]),
            button=Button("Reportar el pago otra vez", pagar),
            footnote="Si estás seguro de que el pago salió, responde a este correo con la captura y lo revisamos a mano.",
            tone="alert",
            context=context,
        )

    if kind == "vence_pronto":
        # Los días vienen del contexto y no escritos en el texto: el aviso
        # se manda con AVISO_PREVIO_DIAS días de antelación (lifecycle.py)
        # y si ese número cambia, el correo no puede seguir diciendo "3".
        dias = context.get("dias", 3)
        return Email(
            subject=f"Te quedan {dias} días de Espikin",
            preheader=f"Tu acceso termina el {context['hasta']}. Renovar toma un minuto.",
            eyebrow="Tu suscripción",
            title=f"Quedan *{dias} días*, {nombre}",
            paragraphs=[
                "Tu mes con Espikin está por terminar. Renovando ahora no pierdes el hilo de lo que vienes trabajando con tus tutores.",
            ],
            note=Note("Tu acceso termina el", context["hasta"]),
            button=Button("Renovar ahora", pagar),
            footnote="Si ya pagaste, no hace falta que hagas nada: en cuanto lo verifiquemos se renueva solo.",
            context=context,
        )

    if kind == "ultimo_dia":
        return Email(
            subject="Hoy es tu último día de acceso",
            preheader="Mañana tu cuenta queda sin acceso. Renovar toma un minuto.",
            eyebrow="Tu suscripción",
            title=f"Hoy es *tu último día*, {nombre}",
            paragraphs=[
                "A partir de mañana tu cuenta queda sin acceso a las clases. Tu progreso no se borra, pero sí se detiene.",
                "Renovar toma un minuto y sigues justo donde lo dejaste.",
            ],
            note=Note("Tu acceso termina el", context["hasta"]),
            button=Button("Renovar ahora", pagar),
            context=context,
        )

    if kind == "vencio":
        return Email(
            subject="Tu acceso a Espikin terminó",
            preheader="Tu progreso sigue guardado. Puedes volver cuando quieras.",
            eyebrow="Tu suscripción",
            title=f"*Tu acceso terminó*, {nombre}",
            paragraphs=[
                "Tu mes con Espikin llegó a su fin. Tu cuenta, tu nivel y todo tu progreso siguen guardados exactamente como los dejaste.",
                "Cuando quieras retomar, solo tienes que activar de nuevo tu acceso.",
            ],
            button=Button("Volver a activar mi acceso", pagar),
            footnote="¿Lo dejas por algo que podamos mejorar? Responde a este correo: lo leemos todos.",
            context=context,
        )

    if kind == "te_echamos_de_menos":
        dias = context.get("dias", 7)
        return Email(
            subject=f"Llevas {dias} días sin practicar",
            preheader="Diez minutos hoy valen más que dos horas el domingo.",
            eyebrow="Tu práctica",
            title=f"*Tu inglés te espera*, {nombre}",
            paragraphs=[
                f"Hace {dias} días que no pasas por el aula. Lo decimos sin regaño: aprender un idioma va de constancia, no de maratones.",
                "<strong>Diez minutos hoy</strong> valen más que dos horas el domingo. Tu tutor retoma la conversación donde la dejaron.",
            ],
            button=Button("Retomar hoy", aula),
            context=context,
        )

    raise ValueError(f"Tipo de correo desconocido: {kind!r}")
