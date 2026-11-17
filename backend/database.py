"""
Gastro IA Backend - Database Configuration

La conexión se lee SIEMPRE de la variable de entorno DATABASE_URL (archivo
backend/.env). No se deja ninguna contraseña escrita en el código.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError(
        "Falta DATABASE_URL. Copiá backend/.env.example a backend/.env y completá "
        "la conexión a PostgreSQL (postgresql://usuario:clave@localhost:5432/gastro_ia)."
    )


def _forzar_psycopg2(url: str) -> str:
    """SQLAlchemy 2.1 usa `psycopg` (v3) por defecto para el esquema `postgresql`.

    El proyecto usa psycopg2 (también en el ETL y en el importador). Si no se
    fija el driver, la app falla al arrancar con `No module named 'psycopg'`.
    Se respeta una URL que ya venga con driver explícito.
    """
    esquema, separador, resto = url.partition("://")
    if separador and esquema in ("postgres", "postgresql"):
        return "postgresql+psycopg2" + separador + resto
    return url


DATABASE_URL = _forzar_psycopg2(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5") or 5),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10") or 10),
    pool_timeout=float(os.getenv("DB_POOL_TIMEOUT", "15") or 15),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800") or 1800),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
