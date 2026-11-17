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
# "*" (por defecto) solo es seguro si el puerto 8000 NO es público, como en el docker-compose.yml
# de este proyecto, donde únicamente Caddy llega al backend. Si algún día exponés el backend
# directo a internet, poné acá la IP del proxy (no "*"): los límites por IP dependen de esto.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
