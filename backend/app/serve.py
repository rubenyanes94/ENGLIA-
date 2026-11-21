"""Arranque de producción de la API escuchando en IPv4 E IPv6 a la vez.

Uso (lo llama start.sh):
    python -m app.serve

Por qué no basta con `uvicorn --host ::`: la red privada de Railway (por
donde el frontend llama a la API) es IPv6, así que hace falta escuchar en
"::". Pero uvicorn abre ese socket con asyncio, y asyncio le pone
IPV6_V6ONLY=1: queda SOLO IPv6. El healthcheck de Railway llega por IPv4,
no encontraba a nadie, y el despliegue se marcaba como caído aunque la app
estuviera viva ("1/1 replicas never became healthy!").

Con `--host 0.0.0.0` pasaría al revés: healthcheck bien, frontend sin
backend. La salida es abrir el socket a mano con IPV6_V6ONLY=0 — un único
socket "dual stack" que atiende las dos familias — y dárselo a uvicorn.
"""

import os
import socket

import uvicorn


def dual_stack_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(("::", port))
    return sock


def main() -> None:
    # $PORT lo inyecta Railway; el 8000 es para correr la imagen a mano.
    port = int(os.environ.get("PORT", "8000"))
    config = uvicorn.Config(
        "app.main:app",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    print(f"→ API en el puerto {port} (IPv4 + IPv6)", flush=True)
    uvicorn.Server(config).run(sockets=[dual_stack_socket(port)])


if __name__ == "__main__":
    main()
