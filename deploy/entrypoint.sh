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
# NO usar "*": así uvicorn toma el primer valor de la cabecera, que lo escribe el cliente, y cualquiera
# puede inventarse IPs para saltarse el cupo de invitados.
# Por defecto se confía solo en redes privadas (el balanceador de Render y la red de Docker): uvicorn
# recorre la cabecera de derecha a izquierda y se queda con la primera IP pública, que es la que
# agregó el proxy y no se puede falsear. En docker-compose.yml se restringe aún más (solo Caddy).
PROXIES_PRIVADOS="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-$PROXIES_PRIVADOS}"
