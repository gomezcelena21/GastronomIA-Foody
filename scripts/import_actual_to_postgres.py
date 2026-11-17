#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPRECADO: importa el dataset original dataset_gastronomia_CABA_GBA.csv (8.181) al Postgres de gastro_ia.
La base del sistema es la unificada de 71.343 lugares: usá scripts/cargar_base_unificada.py (o scripts/cargar_base_nube.py).
Este script TRUNCATEA las tablas y deja la base más chica: solo para el dataset de prueba del CI o por pedido explícito.
Mantiene el dataset actual pero usa el formato/backend que te funciona (FastAPI + Postgres + Dashboard)
"""
import os
import csv
import psycopg2
import json
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "dataset_gastronomia_CABA_GBA.csv"
# Also check etl/raw path for fallback
if not CSV_PATH.exists():
    CSV_PATH = Path(__file__).parent.parent / "etl" / "raw" / "dataset_gastronomia_CABA_GBA.csv"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "gastro_ia",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", ""),  # antes: contraseña escrita acá. Usá: set PGPASSWORD=tu_clave
}

def parse_bool(v):
    v = (v or "").strip().lower()
    if "apto" in v:
        return True
    if "no disponible" in v:
        return False
    return None

def clean_lat_lon(lat_raw, lon_raw):
    """Convierte las coordenadas del CSV a grados y descarta las inválidas.

    Las fuentes traen enteros escalados por 1e7 (ej. -346088690 = -34.6088690).
    Algunos registros perdieron ceros finales (ej. -3461369), por eso se
    completa la escala hasta que la coordenada caiga en Argentina. Antes, esos
    casos quedaban como -3.46 / -0.34 y el local aparecía en el océano.
    """
    def a_grados(valor, referencia):
        try:
            texto = str(valor).strip().replace(",", ".")
            if not texto:
                return None
            if "." in texto:
                grados = float(texto)
            else:
                entero = int(texto)
                # Los placeholders de BA Data son -350 / -580, sin escala real.
                if abs(entero) < 1000:
                    return None
                grados = entero / 1e7
            for _ in range(6):
                if abs(grados) >= referencia:
                    break
                grados *= 10
            return round(grados, 7)
        except (TypeError, ValueError):
            return None

    lat = a_grados(lat_raw, 30)   # en Argentina la latitud es <= -30
    lon = a_grados(lon_raw, 50)   # en Argentina la longitud es <= -50
    if lat is None or lon is None:
        return None, None
    if not (-55 <= lat <= -21 and -74 <= lon <= -53):
        return None, None
    return lat, lon

def map_province_city(barrio):
    b = (barrio or "").strip().lower()
    caba_barrios = {"palermo","recoleta","belgrano","balvanera","san nicolas","monserrat","caballito","retiro","colegiales","flores","san telmo","almagro","puerto madero","saavedra","villa crespo","boedo","nuñez","nunez","olivos","vicente lopez","martinez","san isidro","lanus","avellaneda"}
    # Simple: if barrio is "Ciudad Autónoma de Buenos Aires" -> CABA, else if in list -> CABA else Buenos Aires
    if b == "ciudad autónoma de buenos aires" or b in caba_barrios:
        return "CABA", barrio
    if b == "no especificado" or not b:
        return "Buenos Aires", "CABA"
    # For GBA localities like Olivos, Vicente Lopez -> Buenos Aires province
    gba = {"olivos","vicente lopez","martinez","san isidro","lanus","avellaneda","banfield","quilmes","san martin","tigre","san fernando"}
    if b in gba:
        return "Buenos Aires", barrio
    return "Buenos Aires", barrio

def normalize_cuisine(raw):
    if not raw or raw.strip().lower() in ("no especificado",""):
        return []
    parts = [p.strip().lower() for p in raw.split(";") if p.strip()]
    # Keep lower, old transform will further normalize
    return parts

# Map tipo_establecimiento raw to category
def map_category(t):
    t = (t or "").strip().lower()
    if not t: return "restaurant"
    mapping = {"restaurant":"restaurant","restaurante":"restaurant","cafe":"cafe","bar":"bar","pub":"pub","fast_food":"restaurant","confiteria":"cafe","vineria":"restaurant","public_bookcase":"otros","internet_cafe":"otros"}
    return mapping.get(t, "restaurant")

def main():
    print("AVISO: importador LEGADO del dataset original (8.181). La base del sistema es la unificada de 71.343 "
          "(scripts/cargar_base_unificada.py). Este proceso TRUNCATEA restaurants y restaurant_features.")
    if not CSV_PATH.exists():
        print(f"CSV no encontrado: {CSV_PATH}")
        return
    conn = psycopg2.connect(os.environ["DATABASE_URL"]) if os.getenv("DATABASE_URL") else psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    # Ensure sources exist
    cur.execute("SELECT source_id, source_type FROM sources")
    sources = {row[1]: row[0] for row in cur.fetchall()}
    # Create sources if missing (should exist from schema)
    if not sources:
        print("Sources table empty, creating...")
        cur.execute("INSERT INTO sources (name, url, source_type, reliability, fetched_date) VALUES ('BA Data','', 'ba_data','official','2026-09-09') RETURNING source_id")
        sources['ba_data'] = cur.fetchone()[0]
        cur.execute("INSERT INTO sources (name, url, source_type, reliability, fetched_date) VALUES ('OSM','', 'osm','public_source','2026-09-09') RETURNING source_id")
        sources['osm'] = cur.fetchone()[0]
        conn.commit()
    print(f"Sources: {sources}")

    # Clear existing restaurants from actual dataset import? We will insert with is_active true, but keep old data? For TPI we want only current dataset, so truncate first
    print("Limpiando restaurants previos (solo para usar dataset actual)...")
    cur.execute("TRUNCATE restaurant_features, restaurants RESTART IDENTITY CASCADE")
    conn.commit()

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"CSV filas: {len(rows)}")
    inserted = 0
    for r in rows:
        try:
            lat, lon = clean_lat_lon(r.get("latitud",""), r.get("longitud",""))
            province, city = map_province_city(r.get("barrio_localidad",""))
            # Use barrio as city, neighborhood = barrio
            neighborhood = r.get("barrio_localidad","") if r.get("barrio_localidad","") != "No especificado" else None
            cuisine = normalize_cuisine(r.get("cocina",""))
            category = map_category(r.get("tipo_establecimiento",""))
            source_type = "ba_data" if r.get("fuente_dato","").startswith("BA Data") else "osm"
            source_id = sources.get(source_type, list(sources.values())[0])
            # confidence: if any diet is Apto then verified? else no_verified
            confidence = "no_verified"
            # phone/website (truncar a 50/300)
            phone = r.get("telefono","").strip() or None
            if phone and len(phone) > 50:
                phone = phone[:50]
            website = r.get("website","").strip() or None
            if website and len(website) > 300:
                website = website[:300]
            # Insert restaurant (sin geom, luego se actualiza si tiene coords)
            cur.execute("""
                INSERT INTO restaurants (name, province, city, neighborhood, address, latitude, longitude, cuisine_type, category, phone, website, source_id, source_type, confidence_level, data_date, fetched_date, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING restaurant_id
            """, (
                r.get("nombre","").strip()[:300],
                province[:100],
                city[:200],
                neighborhood[:200] if neighborhood else None,
                r.get("direccion","").strip()[:500] or None,
                lat, lon,
                cuisine,
                category,
                phone,
                website,
                source_id,
                source_type,
                confidence,
                "2026-09-09",
                "2026-09-09",
                True
            ))
            rid = cur.fetchone()[0]
            if lat is not None and lon is not None:
                cur.execute("UPDATE restaurants SET geom = ST_SetSRID(ST_MakePoint(%s,%s),4326) WHERE restaurant_id = %s", (lon, lat, rid))
            conn.commit()
            # Features
            cur.execute("""
                INSERT INTO restaurant_features (restaurant_id, has_gluten_free_options, has_vegetarian_options, has_vegan_options, source_id, confidence_level)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                rid,
                parse_bool(r.get("es_sin_tacc","")),
                parse_bool(r.get("es_vegetariano","")),
                parse_bool(r.get("es_vegano","")),
                source_id,
                confidence
            ))
            inserted += 1
        except Exception as e:
            print(f"Error fila {r.get('id_origen')}: {e}")
            try:
                conn.rollback()
            except:
                pass
            cur = conn.cursor()
            continue
    # commit ya hecho por fila, solo asegurar
    try:
        conn.commit()
    except:
        pass
    cur.execute("SELECT COUNT(*) FROM restaurants")
    print(f"Insertados {inserted}, total en DB: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE geom IS NOT NULL")
    print(f"Con geom: {cur.fetchone()[0]}")
    # Estadísticas para que el planificador use bien los índices.
    for tabla in ("restaurants", "restaurant_features", "sources", "menus"):
        cur.execute("ANALYZE " + tabla)
    conn.commit()
    print("Estadísticas actualizadas (ANALYZE).")
    conn.close()
    print("Import actual dataset OK — usa formato viejo que sí responde, con datos del CSV actual.")

if __name__ == "__main__":
    main()
