"""
Carga las tablas del diseño a partir de los datos que ya tenés en PostgreSQL:
  - restricciones_alimentarias (catálogo base)
  - establecimiento_restriccion (desde restaurant_features, con nivel_informacion)
  - establecimiento_fuente      (desde restaurants.source_id)
Es seguro correrlo más de una vez (no duplica filas).

Uso (desde la carpeta del proyecto):
    python scripts/poblar_diseno.py
Necesita backend/.env con DATABASE_URL.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

from dotenv import load_dotenv
load_dotenv(RAIZ / "backend" / ".env")

from sqlalchemy import text
from database import SessionLocal, engine
from models_diseno import crear_tablas_diseno, sembrar_restricciones

# (columna de restaurant_features, nombre de la restricción)
MAPA = [
    ("has_gluten_free_options", "Celíaco (sin TACC)"),
    ("has_vegetarian_options", "Vegetariano"),
    ("has_vegan_options", "Vegano"),
    ("has_lactose_free_options", "Sin lactosa"),
]


def main():
    crear_tablas_diseno(engine)
    db = SessionLocal()
    try:
        sembrar_restricciones(db)
        for col, nombre in MAPA:
            # 'declarado' solo si la fuente marca certificación; si no, 'inferido' o 'no_verificado'.
            # Nunca se trata como garantía absoluta.
            db.execute(text("""
                INSERT INTO establecimiento_restriccion (id_establecimiento, id_restriccion, nivel_informacion)
                SELECT rf.restaurant_id, rr.id_restriccion,
                       CASE WHEN :es_celiaco AND rf.celiac_certified IS TRUE THEN 'declarado'
                            WHEN rf.confidence_level IS NULL OR rf.confidence_level = 'no_verified' THEN 'no_verificado'
                            ELSE 'inferido' END
                FROM restaurant_features rf
                JOIN restaurants r ON r.restaurant_id = rf.restaurant_id
                JOIN restricciones_alimentarias rr ON rr.nombre = :nombre
                WHERE rf.%s IS TRUE
                ON CONFLICT DO NOTHING
            """ % col), {"nombre": nombre, "es_celiaco": col == "has_gluten_free_options"})   # `col` sale de la lista MAPA de arriba, no de un usuario
        db.execute(text("""
            INSERT INTO establecimiento_fuente (id_establecimiento, id_fuente)
            SELECT restaurant_id, source_id FROM restaurants WHERE source_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """))
        db.commit()
        for tabla in ("restricciones_alimentarias", "establecimiento_restriccion", "establecimiento_fuente"):
            n = db.execute(text("SELECT COUNT(*) FROM " + tabla)).scalar()   # nombres fijos
            print("%-32s %d filas" % (tabla, n))
    finally:
        db.close()


if __name__ == "__main__":
    main()
