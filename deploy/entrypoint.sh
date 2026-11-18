#!/bin/sh
# Espera a que PostgreSQL/PostGIS acepte conexiones y arranca la API.
# Sirve tanto para el PostGIS del compose como para Neon/Supabase.
set -e

python - <<'PY'
import os
import time

url = os.environ.get("DATABASE_URL")
if url:
    try:
        import psycopg2
    except Exception as e:
        print("No pude importar psycopg2:", e, flush=True)
    else:
        for intento in range(1, 61):
            try:
                psycopg2.connect(url, connect_timeout=3).close()
                print("Base de datos disponible.", flush=True)
                break
            except Exception as e:
                print("Esperando la base (%d/60): %s" % (intento, e), flush=True)
                time.sleep(2)
        else:
            print("La base no respondió; arranco igual (el healthcheck fallará).", flush=True)
PY

# FORWARDED_ALLOW_IPS: de qué IPs se acepta la cabecera X-Forwarded-For (la IP real del visitante).
# Con "*" uvicorn toma el PRIMER valor de la cabecera, que lo elige el cliente: sirve en Render
# (donde el proxy es la única entrada) pero permite inventar la IP. En docker-compose.yml se fija
# la subred 172.28.0.0/16 y solo se confía en Caddy, que está adentro de esa red.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
