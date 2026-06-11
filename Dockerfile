# ============================================================
# QuoteBox API — Dockerfile
# Deploy target: Railway
# ============================================================
FROM python:3.12-slim

# Evita archivos .pyc y bufferiza stdout/stderr para logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# lxml necesita libxml2/libxslt en tiempo de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt1-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app/ ./app/

EXPOSE 8000

# IMPORTANTE: --workers 1 es obligatorio.
# APScheduler corre dentro del proceso FastAPI. Con múltiples workers,
# el scheduler se inicializa N veces y el job se ejecuta N veces en paralelo.
# Si se necesita escalar horizontalmente, mover el scheduler a un servicio separado.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
