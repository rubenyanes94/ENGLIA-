FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema necesarias para compilar drivers de Postgres, etc.
# "git" no hace falta para correr la API, pero VS Code/Codespaces adjunta
# su terminal a ESTE contenedor (ver .devcontainer/), así que lo instalamos
# para poder usar git desde ahí igual que en el terminal del host.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl git \
    && rm -rf /var/lib/apt/lists/*

# Copiamos primero SOLO requirements.txt para aprovechar la caché de Docker:
# si el código cambia pero las dependencias no, este paso no se repite.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Voz de Piper TTS horneada en la imagen (no descargada en runtime): así
# la narración funciona sin depender de que Hugging Face esté disponible
# cuando arranca el contenedor. Fuera de /app a propósito — en dev
# ./backend:/app se monta encima (ver docker-compose.yml), lo que
# horneemos ahí quedaría oculto por el bind mount del host.
RUN mkdir -p /opt/piper-voices \
    && python -m piper.download_voices en_US-lessac-medium --download-dir /opt/piper-voices

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
