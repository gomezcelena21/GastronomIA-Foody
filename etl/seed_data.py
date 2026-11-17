"""
Gastro IA - Seed Data Script (SQL-based)
Populates the database with sample restaurants for testing.
"""

import sys
import os
import psycopg2

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "gastro_ia",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", ""),  # antes: contraseña escrita acá. Usá: set PGPASSWORD=tu_clave
}


SEED_DATA = [
    # Buenos Aires - CABA
    ("La Cabrera", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Palermo", "José Antonio Cabrera 5099", -34.5789, -58.4305, ["argentina", "parrilla"], "restaurante", "+54 11 4831-7008", 4, 4.5, "public_source", True, True, False),
    ("Don Julio", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Palermo", "Guatemala 4699", -34.5753, -58.4273, ["argentina", "parrilla", "bodegón"], "restaurante", "+54 11 4832-6010", 4, 4.7, "community", True, True, False),
    ("Sarkis", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Palermo", "Thames 1830", -34.5748, -58.4212, ["árabe", "medio oriente"], "restaurante", "+54 11 4832-3874", 3, 4.3, "community", False, True, True),
    ("i Latina", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "San Telmo", "Lamadrid 675", -34.6221, -58.3715, ["latina", "fusión"], "restaurante", "+54 11 4300-1112", 4, 4.6, "public_source", True, True, True),
    ("El Sanjuanino", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Recoleta", "Guatemala 4902", -34.5757, -58.4276, ["argentina", "empanadas"], "restaurante", "+54 11 4832-6840", 2, 4.2, "community", False, True, False),
    ("Narda Compañía", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Palermo", "Av. Córdoba 5601", -34.5853, -58.4303, ["argentina", "moderna"], "restaurante", "+54 11 5252-2525", 4, 4.4, "public_source", True, True, True),
    ("Café San Juan", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "San Telmo", "Av. San Juan 450", -34.6235, -58.3715, ["argentina", "café"], "café", "+54 11 4300-8498", 2, 4.1, "community", False, True, False),
    ("Proper", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Palermo", "Av. Dorrego 1742", -34.5765, -58.4198, ["argentina", "moderna"], "restaurante", None, 4, 4.5, "public_source", True, True, True),
    ("El Desnivel", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "San Telmo", "Defensa 855", -34.6232, -58.3721, ["argentina", "parrilla"], "restaurante", "+54 11 4300-9096", 3, 4.0, "community", False, True, False),
    ("Risotto", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Belgrano", "Av. Cabildo 2264", -34.5612, -58.4532, ["italiana"], "restaurante", "+54 11 4783-1234", 3, 4.2, "community", True, True, False),

    # Córdoba
    ("La Parrillita de Peña", "Córdoba", "Córdoba", "Nueva Córdoba", "Av. General Paz 550", -31.4201, -64.1828, ["argentina", "parrilla"], "restaurante", "+54 351 422-3456", 3, 4.3, "community", False, True, False),
    ("El Gigante", "Córdoba", "Córdoba", "Güemes", "Av. Haya de la Torre 123", -31.4185, -64.1790, ["argentina", "parrilla", "pizza"], "restaurante", "+54 351 433-4567", 3, 4.1, "community", True, True, False),
    ("Siete Fuegos", "Córdoba", "Villa Carlos Paz", None, "Av. San Martín 890", -31.4245, -64.4967, ["argentina", "parrilla"], "restaurante", "+54 351 461-7890", 4, 4.5, "community", True, False, False),
    ("La Otra Parrilla", "Córdoba", "Córdoba", "Alta Córdoba", "Av. Rivera Indarte 1200", -31.3950, -64.1850, ["argentina", "parrilla"], "restaurante", "+54 351 412-3456", 2, 4.0, "community", False, True, False),

    # Mendoza
    ("Anotador", "Mendoza", "Mendoza", "Ciudad", "Av. San Martín 1250", -32.8908, -68.8272, ["argentina", "moderna"], "restaurante", "+54 261 423-5678", 4, 4.6, "community", True, True, True),
    ("Bodega Zuccardi", "Mendoza", "Maipú", None, "Ruta Panamericana Km 11.5", -32.9550, -68.7830, ["argentina", "bodega"], "restaurante", "+54 261 496-0011", 4, 4.7, "community", True, True, False),
    ("El Asador", "Mendoza", "Mendoza", "Ciudad", "Av. Antartida Argentina 900", -32.8885, -68.8350, ["argentina", "parrilla"], "restaurante", "+54 261 425-1234", 3, 4.2, "community", False, True, False),
    ("La Fonte", "Mendoza", "Mendoza", "Ciudad", "Belgrano 1234", -32.8950, -68.8290, ["italiana"], "restaurante", "+54 261 420-5678", 3, 4.3, "community", True, True, False),

    # Santa Fe - Rosario
    ("La Ribera", "Santa Fe", "Rosario", "Centro", "Córdoba 1234", -32.9468, -60.6506, ["argentina", "parrilla"], "restaurante", "+54 341 423-5678", 3, 4.1, "community", False, True, False),
    ("El Mangrullo", "Santa Fe", "Rosario", "Pichincha", "Córdoba 1500", -32.9490, -60.6480, ["argentina", "parrilla", "mariscos"], "restaurante", "+54 341 420-9012", 3, 4.3, "community", True, True, False),
    ("El Turista", "Santa Fe", "Rosario", "Centro", "Maipú 850", -32.9485, -60.6520, ["argentina"], "restaurante", "+54 341 422-3456", 2, 4.0, "community", False, True, False),

    # Provincia de Buenos Aires
    ("El Preferido", "Buenos Aires", "La Plata", "Centro", "Calle 7 1234", -34.9214, -57.9545, ["argentina"], "restaurante", "+54 221 423-5678", 2, 4.0, "community", False, True, False),
    ("Lo de Tano", "Buenos Aires", "Mar del Plata", "Centro", "San Martín 1500", -38.0055, -57.5426, ["argentina", "parrilla", "mariscos"], "restaurante", "+54 223 420-9012", 3, 4.2, "community", True, False, False),
]


def seed_database():
    """Insert seed data into the database."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Check if data already exists
        cur.execute("SELECT COUNT(*) FROM restaurants")
        count = cur.fetchone()[0]
        
        if count > 0:
            print(f"Database already has {count} restaurants. Skipping seed.")
            return
        
        # Get or create default source
        cur.execute("SELECT source_id FROM sources WHERE name = 'Seed Data'")
        row = cur.fetchone()
        
        if not row:
            cur.execute("""
                INSERT INTO sources (name, source_type, url, license, reliability, is_active)
                VALUES ('Seed Data', 'community', NULL, 'unknown', 'community', TRUE)
                RETURNING source_id
            """)
            source_id = cur.fetchone()[0]
        else:
            source_id = row[0]
        
        # Insert restaurants
        for data in SEED_DATA:
            (name, province, city, neighborhood, address, lat, lon, cuisine, category,
             phone, price_range, rating, confidence, gf, veg, vegan) = data
            
            # Build geom
            geom = f"SRID=4326;POINT({lon} {lat})" if lat and lon else None
            
            # Insert restaurant
            cur.execute("""
                INSERT INTO restaurants (
                    name, province, city, neighborhood, address,
                    latitude, longitude, geom, cuisine_type, category,
                    phone, price_range, rating,
                    source_id, source_type, confidence_level,
                    is_active, fetched_date
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, ST_GeomFromText(%s, 4326), %s, %s,
                    %s, %s, %s,
                    %s, 'osm', %s,
                    TRUE, NOW()
                )
                RETURNING restaurant_id
            """, (name, province, city, neighborhood, address,
                  lat, lon, geom, cuisine, category,
                  phone, price_range, rating,
                  source_id, confidence))
            
            rest_id = cur.fetchone()[0]
            
            # Insert features
            cur.execute("""
                INSERT INTO restaurant_features (
                    restaurant_id, has_gluten_free_options, has_vegetarian_options,
                    has_vegan_options, has_lactose_free_options
                ) VALUES (%s, %s, %s, %s, FALSE)
            """, (rest_id, gf, veg, vegan))
        
        conn.commit()
        print(f"Successfully seeded {len(SEED_DATA)} restaurants!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error seeding database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    seed_database()
