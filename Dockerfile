# GastronomIA - imagen del backend (FastAPI + PostGIS vía DATABASE_URL)
# Se construye desde la raíz del proyecto:
#   docker compose build
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl se usa para el healthcheck; el resto son dependencias mínimas.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# requirements.lock fija las versiones exactas (incluidas las transitivas).
# Si falta el lock, se usa requirements.txt como respaldo.
COPY backend/requirements.txt backend/requirements.lock /app/backend/
RUN if [ -f /app/backend/requirements.lock ]; then \
        pip install --no-cache-dir -r /app/backend/requirements.lock; \
    else \
        pip install --no-cache-dir -r /app/backend/requirements.txt; \
    fi

# Código, esquema, analytics y el dataset para poder importarlo dentro del contenedor.
COPY backend /app/backend
COPY database /app/database
COPY analytics /app/analytics
COPY data /app/data
COPY scripts /app/scripts
COPY deploy/entrypoint.sh /app/entrypoint.sh

# sed: por si el script llegó con finales de línea de Windows (CRLF), que impiden arrancar el contenedor.
RUN useradd --create-home --uid 10001 gastronomia \
    && sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh \
    && chown -R gastronomia:gastronomia /app
USER gastronomia

WORKDIR /app/backend
EXPOSE 8000

# Usa el puerto real (en Render lo define la variable PORT) y /ping, que no toca la base.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/ping" || exit 1

# El entrypoint espera a la base y arranca uvicorn con proxy headers.
ENTRYPOINT ["/app/entrypoint.sh"]
