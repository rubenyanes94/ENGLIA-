"""La plantilla de los correos de Espikin: una sola, para que todos se
reconozcan como nuestros.

Se escribe como un correo, no como una página web. El HTML de un correo
va veinte años por detrás del de un navegador, así que aquí hay cosas que
en la app serían un error y aquí son obligatorias:

- **Tablas para maquetar.** Outlook (motor de Word) ignora flex, grid y
  buena parte de `float`. Una tabla centrada de 600 px es lo único que se
  ve igual en Gmail, Outlook, Apple Mail y el móvil.
- **Estilos en línea.** Gmail recorta el `<style>` del `<head>` en parte
  de sus clientes; lo único seguro es `style="..."` en cada etiqueta. El
  bloque `<style>` de aquí solo lleva el modo oscuro y el ajuste de
  móvil, que son mejoras: si un cliente los tira, el correo sigue bien.
- **Botón "a prueba de balas".** El bloque VML comentado con `<!--[if
  mso]>` es para Outlook, que no pinta `border-radius` ni el relleno de
  un `<a>`: sin eso, el botón se ve como un enlace suelto.
- **Sin imágenes.** El logotipo es una celda violeta con el nombre
  dentro, no un PNG. Casi todos los clientes bloquean las imágenes hasta
  que el lector pulsa "mostrar"; un logotipo que no carga es un cuadro
  roto justo en la cabecera. Además, hoy no tenemos dominio propio donde
  alojarlo. Dibujado con HTML se ve siempre.

Colores y tipografía, los de la marca (frontend/tailwind.config.ts):
violeta brand-600 #6D3BE6 y azul tinta ink-900 #120E3A, con Inter y su
respaldo del sistema — en correo la fuente casi nunca es Inter, así que
la pila de respaldo importa más que en la web.
"""

from dataclasses import dataclass, field
from html import escape

BRAND = "#6D3BE6"
BRAND_DARK = "#5B2CCB"
BRAND_LIGHT = "#F5F2FF"
BRAND_BORDER = "#DCD1FF"
INK = "#120E3A"
TEXT = "#334155"
MUTED = "#94A3B8"
BORDER = "#E8E4F5"
FONT = "'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"

# Solo mejoras: modo oscuro y el ajuste a pantalla estrecha. Va en <style>
# porque son media queries, que no pueden ir en línea.
HEAD_STYLE = """
<style>
  @media (max-width: 620px) {
    .sp-wrap { padding: 16px 12px !important; }
    .sp-card { padding: 28px 22px !important; }
    .sp-title { font-size: 22px !important; }
  }
  @media (prefers-color-scheme: dark) {
    .sp-bg { background: #0A0824 !important; }
    .sp-card { background: #171334 !important; }
    .sp-title, .sp-strong { color: #F5F2FF !important; }
    .sp-text { color: #C9C4E4 !important; }
    .sp-note { background: #241254 !important; border-color: #3D2184 !important; }
    .sp-foot { color: #8C86AE !important; }
  }
</style>
"""


@dataclass
class Button:
    label: str
    url: str


@dataclass
class Note:
    """El recuadro con el dato concreto del correo: la fecha de
    vencimiento, el monto, el motivo de un rechazo."""

    label: str
    value: str


@dataclass
class Email:
    """Un correo de Espikin ya escrito, listo para enviar."""

    subject: str
    # La línea que el cliente de correo enseña junto al asunto en la
    # bandeja de entrada. Es lo que decide si lo abren: se escribe a mano
    # y no se deja que el cliente coja el principio del texto.
    preheader: str
    # La etiqueta pequeña de arriba, en violeta y mayúsculas. Hace que el
    # correo se lea de un vistazo, como el nombre de la app en una
    # notificación del móvil.
    eyebrow: str
    title: str
    paragraphs: list[str]
    button: Button | None = None
    note: Note | None = None
    # Texto pequeño bajo el botón ("Si ya pagaste, no hace falta que
    # hagas nada").
    footnote: str | None = None
    tone: str = "brand"  # "brand" | "alert": el color del botón y la etiqueta
    context: dict = field(default_factory=dict)


ALERT = "#E11D48"
ALERT_LIGHT = "#FFF1F4"
ALERT_BORDER = "#FECDD6"


def _accent(tone: str) -> str:
    return ALERT if tone == "alert" else BRAND


def _button_html(button: Button) -> str:
    # El botón va SIEMPRE en violeta de marca, incluso en un correo de
    # aviso: el titular ya dice que algo va mal, y lo que el botón ofrece
    # ("reportar el pago otra vez") es la salida, no el problema. Un botón
    # rojo ahí se lee como "no toques esto".
    color = BRAND
    url = escape(button.url, quote=True)
    label = escape(button.label)
    # El comentario condicional es para Outlook y solo Outlook: el resto
    # de clientes lo ven como un comentario HTML y lo ignoran.
    return f"""
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0 4px;">
                <tr><td align="center" bgcolor="{color}" style="border-radius:12px;">
                  <!--[if mso]>
                  <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word"
                    href="{url}" style="height:48px;v-text-anchor:middle;width:280px;" arcsize="25%" stroke="f" fillcolor="{color}">
                    <w:anchorlock/><center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">{label}</center>
                  </v:roundrect>
                  <![endif]-->
                  <!--[if !mso]><!-- -->
                  <a href="{url}" style="display:inline-block;padding:15px 34px;font-family:{FONT};font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:12px;background:{color};">{label}</a>
                  <!--<![endif]-->
                </td></tr>
              </table>"""


def _note_html(note: Note, tone: str) -> str:
    fondo, borde = (ALERT_LIGHT, ALERT_BORDER) if tone == "alert" else (BRAND_LIGHT, BRAND_BORDER)
    return f"""
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0 4px;">
                <tr><td class="sp-note" style="background:{fondo};border:1px solid {borde};border-radius:14px;padding:16px 20px;">
                  <p style="margin:0;font-family:{FONT};font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:{_accent(tone)};">{escape(note.label)}</p>
                  <p class="sp-strong" style="margin:6px 0 0;font-family:{FONT};font-size:19px;font-weight:700;color:{INK};">{escape(note.value)}</p>
                </td></tr>
              </table>"""


def render_html(email: Email, unsubscribe_url: str | None = None) -> str:
    """El correo completo. `unsubscribe_url` solo se pasa en los correos
    comerciales: en uno transaccional (un pago rechazado) ofrecer "no
    quiero recibir más" sería ofrecerle dejar de enterarse de su dinero."""
    accent = _accent(email.tone)
    paragraphs = "".join(
        f'<p class="sp-text" style="margin:0 0 14px;font-family:{FONT};font-size:16px;line-height:1.65;color:{TEXT};">{p}</p>'
        for p in email.paragraphs
    )
    button = _button_html(email.button) if email.button else ""
    note = _note_html(email.note, email.tone) if email.note else ""
    footnote = (
        f'<p class="sp-foot" style="margin:14px 0 0;font-family:{FONT};font-size:13px;line-height:1.6;color:{MUTED};">{email.footnote}</p>'
        if email.footnote
        else ""
    )
    baja = (
        f'<br><a href="{escape(unsubscribe_url, quote=True)}" style="color:{MUTED};text-decoration:underline;">No quiero recibir estos recordatorios</a>'
        if unsubscribe_url
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{escape(email.subject)}</title>
{HEAD_STYLE}</head>
<body class="sp-bg" style="margin:0;padding:0;background:#F1F0F7;">
  <!-- Preheader: lo que se lee junto al asunto en la bandeja. Oculto en el
       cuerpo; los espacios de después evitan que el cliente rellene con el
       principio del texto. -->
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(email.preheader)}
    &#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="sp-bg" style="background:#F1F0F7;">
    <tr><td class="sp-wrap" align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">

        <!-- Marca -->
        <tr><td align="center" style="padding-bottom:22px;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="background:{BRAND};border-radius:11px;width:34px;height:34px;text-align:center;vertical-align:middle;font-family:{FONT};font-size:19px;font-weight:800;color:#ffffff;line-height:34px;">e</td>
              <td style="padding-left:11px;font-family:{FONT};font-size:19px;font-weight:700;letter-spacing:-.01em;color:{INK};">Espikin</td>
            </tr>
          </table>
        </td></tr>

        <!-- Mensaje -->
        <tr><td class="sp-card" style="background:#ffffff;border:1px solid {BORDER};border-radius:20px;padding:36px 34px;">
          <p style="margin:0 0 10px;font-family:{FONT};font-size:12px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:{accent};">{escape(email.eyebrow)}</p>
          <h1 class="sp-title" style="margin:0 0 16px;font-family:{FONT};font-size:26px;line-height:1.25;font-weight:800;letter-spacing:-.02em;color:{INK};">{escape(email.title)}</h1>
          {paragraphs}
          {note}
          {button}
          {footnote}
        </td></tr>

        <!-- Pie -->
        <tr><td align="center" style="padding:22px 12px 0;">
          <p class="sp-foot" style="margin:0;font-family:{FONT};font-size:12px;line-height:1.7;color:{MUTED};">
            Espikin · Tu academia de inglés con tutores de inteligencia artificial<br>
            Recibes este correo porque tienes una cuenta en Espikin.{baja}
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body></html>"""


def render_text(email: Email, unsubscribe_url: str | None = None) -> str:
    """Versión en texto plano. No es opcional: un correo solo-HTML puntúa
    peor en los filtros de spam, y algunos clientes (relojes, lectores de
    pantalla, avisos del móvil) enseñan esto y no el HTML."""
    lines = [email.title, "", *[_strip_tags(p) for p in email.paragraphs]]
    if email.note:
        lines += ["", f"{email.note.label}: {email.note.value}"]
    if email.button:
        lines += ["", f"{email.button.label}: {email.button.url}"]
    if email.footnote:
        lines += ["", _strip_tags(email.footnote)]
    lines += ["", "—", "Espikin · Tu academia de inglés con tutores de inteligencia artificial"]
    if unsubscribe_url:
        lines += [f"Para no recibir estos recordatorios: {unsubscribe_url}"]
    return "\n".join(lines)


def _strip_tags(html: str) -> str:
    """Los párrafos llevan algún <strong> o <a> suelto; en texto plano
    sobra la etiqueta pero no lo que hay dentro."""
    import re

    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("&nbsp;", " ").strip()
