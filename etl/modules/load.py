"""
Gastro IA ETL - Load Module
Loads validated and deduplicated data into PostgreSQL.
"""

import os
import json
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "gastro_ia",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", ""),  # antes: contraseña escrita acá. Usá: set PGPASSWORD=tu_clave
}


def get_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def load_sources(conn):
    """Load source records into sources table."""
    cursor = conn.cursor()
    
    sources = [
        {
            "name": "BA Data - Oferta Gastronomica",
            "url": "https://data.buenosaires.gob.ar/dataset/oferta-establecimientos-gastronomicos",
            "source_type": "government",
            "license": "CC-BY-2.5-AR",
            "update_frequency": "Historico",
            "last_updated": "2019-08-05",
            "reliability": "official",
            "notes": "Datos del Ente de Turismo de CABA. CSV con coordenadas.",
            "fetched_date": "2026-08-22",
        },
        {
            "name": "OpenStreetMap - Overpass API",
            "url": "https://overpass-api.de/api/interpreter",
            "source_type": "osm",
            "license": "ODbL",
            "update_frequency": "Continua",
            "last_updated": None,
            "reliability": "public_source",
            "notes": "Datos de la comunidad OpenStreetMap. Tags de cuisine y diet.",
            "fetched_date": "2026-08-22",
        },
        {
            "name": "Datos Abiertos Mendoza - Gastronomia",
            "url": "https://datosabiertos.mendoza.gov.ar/dataset/gastronomia-en-mendoza",
            "source_type": "government",
            "license": "CC-BY-4.0",
            "update_frequency": "Semestral",
            "last_updated": "2019-07-01",
            "reliability": "official",
            "notes": "Locales gastronomicos de Mendoza. Sin coordenadas.",
            "fetched_date": "2026-08-22",
        },
    ]
    
    source_ids = {}
    
    for src in sources:
        # Check if source already exists
        cursor.execute(
            "SELECT source_id FROM sources WHERE name = %s",
            (src["name"],),
        )
        existing = cursor.fetchone()
        
        if existing:
            source_ids[src["source_type"]] = existing[0]
        else:
            cursor.execute(
                """
                INSERT INTO sources (name, url, source_type, license, update_frequency, 
                                    last_updated, reliability, notes, fetched_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING source_id
                """,
                (
                    src["name"], src["url"], src["source_type"], src["license"],
                    src["update_frequency"], src["last_updated"], src["reliability"],
                    src["notes"], src["fetched_date"],
                ),
            )
            row = cursor.fetchone()
            source_ids[src["source_type"]] = row[0]
    
    conn.commit()
    print(f"  Loaded {len(sources)} sources")
    return source_ids


def load_restaurants(conn, df, source_ids):
    """Load restaurants into database."""
    cursor = conn.cursor()
    
    if df.empty:
        return 0
    
    count = 0
    
    for _, row in df.iterrows():
        try:
            # Get source_id
            source_type = row.get("source_type", "osm")
            source_id = source_ids.get(source_type)
            
            # Build cuisine array
            cuisine = row.get("cuisine_type", [])
            if isinstance(cuisine, str):
                cuisine = [cuisine] if cuisine else []
            
            # Build social media JSON
            social_media = {}
            
            # Insert restaurant
            cursor.execute(
                """
                INSERT INTO restaurants (
                    name, province, city, neighborhood, address,
                    latitude, longitude, geom,
                    cuisine_type, category,
                    phone, email, website, social_media,
                    opening_hours, price_range, rating, review_count,
                    source_id, source_type, confidence_level,
                    data_date, fetched_date
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                RETURNING restaurant_id
                """,
                (
                    row["name"],
                    row["province"],
                    row["city"],
                    row.get("neighborhood"),
                    row.get("address"),
                    row.get("latitude"),
                    row.get("longitude"),
                    row.get("longitude"),
                    row.get("latitude"),
                    cuisine,
                    row.get("category", "restaurant"),
                    row.get("phone"),
                    row.get("email"),
                    row.get("website"),
                    json.dumps(social_media),
                    row.get("opening_hours"),
                    row.get("price_range"),
                    row.get("rating"),
                    row.get("review_count"),
                    source_id,
                    source_type,
                    row.get("confidence_level", "no_verified"),
                    row.get("data_date"),
                    row.get("fetched_date"),
                ),
            )
            
            restaurant_id = cursor.fetchone()[0]
            
            # Insert features
            cursor.execute(
                """
                INSERT INTO restaurant_features (
                    restaurant_id, has_gluten_free_options,
                    has_vegetarian_options, has_vegan_options,
                    has_lactose_free_options, celiac_certified,
                    source_id, confidence_level
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    restaurant_id,
                    row.get("has_gluten_free_options"),
                    row.get("has_vegetarian_options"),
                    row.get("has_vegan_options"),
                    None,  # lactose_free not available
                    False,
                    source_id,
                    row.get("confidence_level", "no_verified"),
                ),
            )
            
            count += 1
            
        except Exception as e:
            print(f"  Error loading row: {e}")
            conn.rollback()
            cursor = conn.cursor()
            continue
    
    conn.commit()
    print(f"  Loaded {count} restaurants")
    return count


def load_all(deduped_data):
    """Load all data into PostgreSQL."""
    print("\n" + "=" * 60)
    print("PHASE 5: LOAD")
    print("=" * 60)
    
    conn = get_connection()
    
    try:
        # Load sources
        print("[LOAD] Loading sources...")
        source_ids = load_sources(conn)
        print(f"  Source IDs: {source_ids}")
        
        # Load restaurants from each source
        total_loaded = 0
        
        source_mapping = {
            "ba_data": "ba_data",
            "osm_caba": "osm",
            "osm_pba": "osm",
            "osm_cordoba": "osm",
            "osm_mendoza_osm": "osm",
            "osm_rosario": "osm",
            "mendoza_official": "mendoza_official",
        }
        
        for source_key, db_source_type in source_mapping.items():
            if source_key in deduped_data and not deduped_data[source_key].empty:
                print(f"\n[LOAD] Loading {source_key}...")
                loaded = load_restaurants(conn, deduped_data[source_key], source_ids)
                total_loaded += loaded
        
        # Summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM restaurants WHERE geom IS NOT NULL")
        with_geom = cursor.fetchone()[0]
        
        cursor.execute("SELECT source_type, COUNT(*) FROM restaurants GROUP BY source_type")
        by_source = cursor.fetchall()
        
        print(f"\n[LOAD] Summary:")
        print(f"  Total active restaurants: {total}")
        print(f"  With valid coordinates: {with_geom}")
        print(f"  By source:")
        for src, cnt in by_source:
            print(f"    {src}: {cnt}")

        # Sin estadísticas el planificador puede elegir planes malos.
        print("\n[LOAD] Actualizando estadísticas (ANALYZE)...")
        for tabla in ("restaurants", "restaurant_features", "sources", "menus"):
            cursor.execute("ANALYZE " + tabla)
        conn.commit()
        print("  Estadísticas actualizadas")

        return total_loaded
        
    finally:
        conn.close()
