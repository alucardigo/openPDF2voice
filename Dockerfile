# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models \
    KOKORO_CACHE_DIR=/models

# Dependências do sistema necessárias para Tkinter e PortAudio
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-tk \
        libportaudio2 \
        libasound2 \
        libgomp1 \
        build-essential \
        git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Pré-download do modelo para facilitar o uso offline
RUN python scripts/download_models.py --model hexgrad/Kokoro-82M --cache-dir /models

VOLUME ["/models"]

EXPOSE 7860

CMD ["python", "web_app.py", "--host", "0.0.0.0", "--port", "7860"]
