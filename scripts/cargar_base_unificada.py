#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carga la base unificada (CSV generado por scripts/convertir_base_unificada.py) en PostgreSQL, EN BLOQUES (rápido, también
para una base en la nube como Neon: decenas de miles de filas en pocos minutos, a diferencia de un INSERT por fila).

    set "DATABASE_URL=postgresql://usuario:clave@host/base?sslmode=require"
    python scripts\\cargar_base_unificada.py
    python scripts\\cargar_base_unificada.py --csv data\\dataset_unificado_CABA_GBA.csv --forzar

SEGURIDAD: si la base ya tiene restaurantes, se detiene (los comercios aprobados viven en esa tabla). Con --forzar borra SOLO los
que vienen de la base unificada y de las fuentes abiertas; los comercios registrados (source_type = registro_comercio) se conservan.
Antes tiene que existir el esquema (database/schema.sql): scripts/cargar_base_nube.py lo aplica y llama a este script.
"""
import csv
import os
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSV_POR_DEFECTO = RAIZ / "data" / "dataset_unificado_ARGENTINA.csv"
LOTE = 1000

# tipo de fuente -> (nombre, url, licencia, fiabilidad, notas)
FUENTES = {
    "overture": ("Overture Maps Foundation (release 2026-10-21.0)", "https://overturemaps.org", "CDLA-Permissive-2.0", "public_source",
                 "Atribución obligatoria a Overture Maps Foundation. Lugares sin verificar con el local."),
    "osm": ("OpenStreetMap contributors", "https://www.openstreetmap.org/copyright", "ODbL", "public_source",
            "© OpenStreetMap contributors, licencia ODbL."),
    "ba_data": ("BA Data (Gobierno de la Ciudad de Buenos Aires)", "https://data.buenosaires.gob.ar", "CC-BY-2.5-AR", "official",
                "Las coordenadas de esta fuente no son confiables: se descartan."),
    "guia_kosher": ("Guía kosher (Jabad Argentina)", "", None, "community_guide", "Listado público de lugares kosher."),
    "guia_celiacos": ("Guía de celíacos (sitio web)", "", None, "community_guide", "Listado público de lugares para celíacos."),
    "google_places": ("Google Places (solo identificación y restricciones)", "https://developers.google.com/maps/documentation/places",
                      "Términos de Google Maps Platform", "public_source",
                      "No se guardan calificaciones, reseñas, horarios ni teléfonos. Ver aviso en docs/analisis_dataset.md."),
}


def _bool(v):
    return {"t": True, "f": False}.get((v or "").strip().lower())


def _numero(v):
    try:
        return float(v) if (v or "").strip() else None
    except ValueError:
        return None


def valores_restaurante(r: dict, source_id: int, hoy: date):
    """Tupla en el orden de la sentencia INSERT de restaurants."""
    return (
        r["nombre"][:300], (r["provincia"] or "Buenos Aires")[:100], (r["ciudad"] or "Sin confirmar")[:200],
        (r["barrio"] or None) and r["barrio"][:200], (r["direccion"] or None) and r["direccion"][:500],
        _numero(r["latitud"]), _numero(r["longitud"]),
        [t for t in (r["cocina"] or "").split(";") if t], r["categoria"] or "restaurant",
        (r["telefono"] or None) and r["telefono"][:50], (r["website"] or None) and r["website"][:300],
        source_id, r["fuente"], "no_verified", (r["fecha_dato"] or None), hoy,
        (r.get("region") or None) and r["region"][:20], (r.get("partido") or None) and r["partido"][:100],
        (r.get("zona") or None) and r["zona"][:50],
    )


def valores_features(restaurant_id: int, r: dict, source_id: int):
    """Tupla en el orden de la sentencia INSERT de restaurant_features. NULL = sin datos (no significa que no lo ofrezca)."""
    return (restaurant_id, _bool(r["sin_tacc"]), _bool(r["vegetariano"]), _bool(r["vegano"]), _bool(r["sin_lactosa"]),
            False, source_id, "inferred" if _bool(r["dato_inferido"]) else "no_verified")


def conectar():
    import psycopg2
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _db import conectar as _c            # usa PGHOST/PGUSER/... o backend/.env
    return _c()


def asegurar_fuentes(cur, tipos):
    ids = {}
    for tipo in tipos:
        nombre, url, licencia, fiabilidad, notas = FUENTES[tipo]
        cur.execute("SELECT source_id FROM sources WHERE source_type = %s ORDER BY source_id LIMIT 1", (tipo,))
        fila = cur.fetchone()
        if fila:
            cur.execute("UPDATE sources SET name=%s, url=%s, license=%s, reliability=%s, notes=%s WHERE source_id=%s",
                        (nombre, url, licencia, fiabilidad, notas, fila[0]))
            ids[tipo] = fila[0]
        else:
            cur.execute("INSERT INTO sources (name, url, source_type, license, reliability, notes, fetched_date) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING source_id",
                        (nombre, url, tipo, licencia, fiabilidad, notas, date.today()))
            ids[tipo] = cur.fetchone()[0]
    return ids


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    forzar = "--forzar" in argv
    ruta = Path(argv[argv.index("--csv") + 1]) if "--csv" in argv else CSV_POR_DEFECTO
    if not ruta.exists():
        print("No encuentro %s. Generalo con scripts/convertir_base_unificada.py" % ruta)
        return 1
    try:
        from psycopg2.extras import execute_values
    except ImportError:
        print("Falta psycopg2: pip install -r backend/requirements.txt")
        return 1
    with open(ruta, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    print("CSV: %d filas (%s)" % (len(filas), ruta.name))

    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM restaurants")
    existentes = cur.fetchone()[0]
    if existentes and not forzar:
        print("La base ya tiene %d restaurantes. Me detengo para no borrarlos (los comercios aprobados están ahí). "
              "Si querés recargar la base unificada conservando los comercios: --forzar" % existentes)
        conn.close()
        return 1
    if existentes:
        cur.execute("DELETE FROM restaurants WHERE source_type IS DISTINCT FROM 'registro_comercio'")
        print("Borrados %d restaurantes de fuentes abiertas (los comercios registrados se conservan)." % cur.rowcount)

    ids = asegurar_fuentes(cur, sorted({r["fuente"] for r in filas}))
    conn.commit()
    hoy = date.today()
    total = 0
    for i in range(0, len(filas), LOTE):
        lote = filas[i:i + LOTE]
        valores = [valores_restaurante(r, ids[r["fuente"]], hoy) for r in lote]
        nuevos = execute_values(
            cur,
            "INSERT INTO restaurants (name, province, city, neighborhood, address, latitude, longitude, cuisine_type, category, "
            "phone, website, source_id, source_type, confidence_level, data_date, fetched_date, region, district, zone_macro) VALUES %s RETURNING restaurant_id",
            valores, template="(%s,%s,%s,%s,%s,%s,%s,%s::text[],%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", fetch=True)
        execute_values(
            cur,
            "INSERT INTO restaurant_features (restaurant_id, has_gluten_free_options, has_vegetarian_options, has_vegan_options, "
            "has_lactose_free_options, celiac_certified, source_id, confidence_level) VALUES %s",
            [valores_features(nid[0], r, ids[r["fuente"]]) for nid, r in zip(nuevos, lote)])
        conn.commit()
        total += len(lote)
        print("  %d / %d" % (total, len(filas)), end="\r")
    cur.execute("UPDATE restaurants SET geom = ST_SetSRID(ST_MakePoint(longitude::float8, latitude::float8), 4326) "
                "WHERE geom IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL")
    conn.commit()
    conn.autocommit = True
    cur.execute("ANALYZE restaurants")
    cur.execute("SELECT source_type, count(*) FROM restaurants GROUP BY 1 ORDER BY 2 DESC")
    print("\nCargados %d lugares. Por fuente: %s" % (total, dict(cur.fetchall())))
    cur.execute("SELECT count(*) FROM restaurant_features WHERE has_gluten_free_options IS TRUE")
    sin_tacc = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM restaurants WHERE geom IS NOT NULL")
    print("Con sin TACC: %d | con ubicación en el mapa: %d" % (sin_tacc, cur.fetchone()[0]))
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
