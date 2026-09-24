"""Escribe en disco los correos de Espikin, ya renderizados, para verlos.

    python -m app.scripts.preview_emails [carpeta]

Existe porque un correo no se puede "recargar en caliente": el ciclo de
cambiar una palabra, enviarlo y abrirlo en el móvil es de minutos, y así
es de segundos. Además deja ver de un tirón los siete juntos, que es la
única forma de notar si uno se ha quedado desalineado del resto.

No envía nada ni toca la base de datos: solo la plantilla y los textos.
"""

import shutil
import sys
from datetime import date
from pathlib import Path

from app.notifications.layout import LOGO_FILE, render_html, render_text
from app.notifications.messages import MARKETING_KINDS, build, fecha_larga

APP = "https://espikin.example/app"
BAJA = "https://espikin.example/app/api/notifications/baja?token=ejemplo"

EJEMPLOS = {
    "bienvenida": {},
    "pago_aprobado": {"hasta": fecha_larga(date(2026, 10, 23))},
    "pago_rechazado": {"motivo": "No aparece en el estado de cuenta"},
    "vence_pronto": {"hasta": fecha_larga(date(2026, 10, 23)), "dias": 3},
    "ultimo_dia": {"hasta": fecha_larga(date(2026, 10, 23))},
    "vencio": {},
    "te_echamos_de_menos": {"dias": 9},
}


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/correos-espikin")
    out.mkdir(parents=True, exist_ok=True)
    # En el correo el logotipo va adjunto con un Content-ID, que un
    # navegador no sabe resolver: para mirarlo aquí se copia al lado.
    shutil.copy(LOGO_FILE, out / LOGO_FILE.name)

    enlaces = []
    for kind, context in EJEMPLOS.items():
        email = build(kind, full_name="Rubén Yánez", app_url=APP, context=context)
        baja = BAJA if kind in MARKETING_KINDS else None
        (out / f"{kind}.html").write_text(render_html(email, baja, logo_url=LOGO_FILE.name), encoding="utf-8")
        (out / f"{kind}.txt").write_text(render_text(email, baja), encoding="utf-8")
        enlaces.append((kind, email.subject, email.preheader))
        print(f"  {kind:22} {email.subject}")

    # Una portada con los siete en línea, para revisarlos de una pasada.
    tarjetas = "".join(
        f'<figure style="margin:0"><figcaption style="font:600 13px/1.5 Inter,sans-serif;color:#120E3A;padding:10px 4px">'
        f'<span style="color:#6D3BE6">{k}</span><br>{s}<br><span style="color:#94A3B8;font-weight:400">{p}</span></figcaption>'
        f'<iframe src="{k}.html" style="width:100%;height:760px;border:1px solid #E8E4F5;border-radius:16px;background:#fff"></iframe></figure>'
        for k, s, p in enlaces
    )
    (out / "index.html").write_text(
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Correos de Espikin</title></head>'
        '<body style="margin:0;background:#F1F0F7;font-family:Inter,sans-serif">'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:24px;padding:24px">'
        f"{tarjetas}</div></body></html>",
        encoding="utf-8",
    )
    print(f"\nAbre: {out / 'index.html'}")


if __name__ == "__main__":
    main()
