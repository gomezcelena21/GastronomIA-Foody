#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GastronomIA - Carga la base de datos en un PostgreSQL de la nube (Neon, Supabase, etc.).

Qué hace, en orden:
  1. Se conecta a la base indicada en DATABASE_URL.
  2. Muestra a qué servidor se va a conectar (sin mostrar la clave) y pide confirmación.
  3. Aplica database/schema.sql (extensiones PostGIS y pg_trgm + tablas).
  4. Carga data/dataset_unificado_ARGENTINA.csv (71.343 lugares de todo el país, en bloques) con scripts/cargar_base_unificada.py.
     Si ese CSV no existe, usa data/dataset_unificado_CABA_GBA.csv (27.064 lugares).
     Si tampoco existe, SE DETIENE: primero hay que generarlo con scripts/convertir_base_unificada.py.
     El dataset original (8.181 registros) solo se carga si pedís --legado a propósito.

SEGURIDAD: la recarga reemplaza los restaurantes de fuentes abiertas y los comercios aprobados viven en esa
tabla. Por eso, si la base ya tiene restaurantes, este script se detiene salvo que agregues --forzar.

Uso (Windows, en la carpeta del proyecto):
    set "DATABASE_URL=postgresql://usuario:clave@host/base?sslmode=require"
    python scripts\\cargar_base_nube.py
    python scripts\\cargar_base_nube.py --forzar     # recarga la base unificada conservando los comercios
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA = RAIZ / "database" / "schema.sql"


def _servidor_legible(url: str) -> str:
    """Host y base de la URL, sin usuario ni clave."""
    p = urlparse(url)
    return "%s / %s" % (p.hostname or "?", (p.path or "/").lstrip("/") or "?")


def main() -> int:
    forzar = "--forzar" in sys.argv
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        print("Falta DATABASE_URL. En Windows:\n  set \"DATABASE_URL=postgresql://usuario:clave@host/base?sslmode=require\"")
        return 1
    if not SCHEMA.exists():
        print("No encuentro %s. Ejecutalo desde la carpeta del proyecto." % SCHEMA)
        return 1
    try:
        import psycopg2
    except ImportError:
        print("Falta psycopg2. Instalá: pip install -r backend/requirements.txt")
        return 1

    print("Servidor de destino: %s" % _servidor_legible(url))
    if (urlparse(url).hostname or "") in ("localhost", "127.0.0.1"):
        print("Aviso: es una base LOCAL, no la de la nube.")
    if input("Escribí SI para continuar: ").strip().upper() != "SI":
        print("Cancelado. No se tocó nada.")
        return 1

    conn = psycopg2.connect(url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT to_regclass('public.restaurants')")
    if cur.fetchone()[0] is not None:
        cur.execute("SELECT count(*) FROM restaurants")
        existentes = cur.fetchone()[0]
        if existentes and not forzar:
            print("La base ya tiene %d restaurantes. Me detengo para no borrarlos "
                  "(los comercios aprobados están ahí). Si de verdad querés recargar todo: --forzar" % existentes)
            conn.close()
            return 1

    print("Aplicando el esquema (database/schema.sql)...")
    cur.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.close()
    print("Esquema listo. Importando el dataset (puede tardar unos minutos)...")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    nacional = RAIZ / "data" / "dataset_unificado_ARGENTINA.csv"
    unificado = nacional if nacional.exists() else RAIZ / "data" / "dataset_unificado_CABA_GBA.csv"
    if unificado.exists():
        # Base unificada nacional (o CABA/GBA si todavía no está el CSV nacional): carga en bloques
        import cargar_base_unificada
        if cargar_base_unificada.main(["--forzar"] if forzar else []) != 0:
            return 1
    else:
        if "--legado" not in sys.argv:
            print("No encuentro %s (la base unificada nacional) ni data\\dataset_unificado_CABA_GBA.csv.\n"
                  "Generala con: python scripts\\convertir_base_unificada.py \"C:\\ruta\\Base_Unificada_Restricciones_Argentina.xlsx\" --alcance argentina\n"
                  "Si de verdad querés cargar el dataset viejo de 8.181 lugares: agregá --legado")
            return 1
        print("Aviso: cargando el dataset ORIGINAL de 8.181 lugares (--legado). La base va a quedar más chica que la unificada.")
        import import_actual_to_postgres  # usa DATABASE_URL si está definida
        import_actual_to_postgres.main()
    print("\nListo. Probá el backend con /health: debería decir \"database\": \"connected\".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
