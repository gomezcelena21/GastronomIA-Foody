#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades comunes de los scripts de datos de GastronomIA.

La conexión se toma de DATABASE_URL (backend/.env o variable de entorno). Si no
está definida, se usan PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE.
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND_ENV = RAIZ / "backend" / ".env"


def _cargar_env() -> None:
    """Carga backend/.env solo si todavía no hay DATABASE_URL en el entorno."""
    if os.getenv("DATABASE_URL"):
        return
    try:
        from dotenv import load_dotenv

        if BACKEND_ENV.exists():
            load_dotenv(BACKEND_ENV)
    except Exception:
        pass


def conectar():
    """Devuelve una conexión psycopg2 o termina con un mensaje claro."""
    _cargar_env()
    try:
        import psycopg2
    except ImportError:
        sys.exit("Falta psycopg2. Instalá: pip install -r backend/requirements.txt")

    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        return psycopg2.connect(url)

    if not os.getenv("PGPASSWORD"):
        sys.exit(
            "Definí DATABASE_URL en backend/.env (recomendado) o PGPASSWORD\n"
            "(y opcionalmente PGHOST, PGPORT, PGUSER, PGDATABASE)."
        )
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "gastro_ia"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD"),
    )


def texto(valor, maximo: int = 400) -> str:
    """Normaliza un valor de CSV: sin espacios extra y recortado."""
    if valor is None:
        return ""
    return str(valor).strip()[:maximo]


def booleano(valor):
    """Convierte si/no/true/false/1/0 en True/False. Vacío o dudoso -> None."""
    v = texto(valor).lower()
    if v in ("si", "sí", "s", "true", "1", "yes", "y"):
        return True
    if v in ("no", "false", "0", "n"):
        return False
    return None


def decimal(valor, maximo: float = 99999999.0):
    """Convierte un precio/nutriente escrito por una persona en float o None."""
    if valor is None:
        return None
    v = str(valor).strip().lower()
    if not v or v in ("-", "sin dato", "sin datos", "n/d", "nd"):
        return None
    v = v.replace("ars", "").replace("$", "").replace(" ", "")
    # Formato argentino: 12.345,50 -> 12345.50 ; 12,50 -> 12.50
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    try:
        n = float(v)
    except ValueError:
        return None
    if n < 0 or n > maximo:
        return None
    return n
