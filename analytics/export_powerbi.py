"""
Gastro IA - Power BI Data Export
Generates CSV and XLSX files for Power BI analysis.
"""

import os
import psycopg2
import csv
import json
from pathlib import Path

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "gastro_ia",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", ""),  # antes: contraseña escrita acá. Usá: set PGPASSWORD=tu_clave
}

def export_data():
    """Export all data to CSV and XLSX files."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    analytics_dir = Path(__file__).parent
    csv_dir = analytics_dir / "csv"
    csv_dir.mkdir(exist_ok=True)
    
    # 1. Export restaurants table
    cur.execute("""
        SELECT 
            r.restaurant_id,
            r.name,
            r.province,
            r.city,
            r.neighborhood,
            r.address,
            r.latitude,
            r.longitude,
            r.cuisine_type,
            r.category,
            r.phone,
            r.email,
            r.website,
            r.opening_hours,
            r.price_range,
            r.rating,
            r.review_count,
            r.source_type,
            r.confidence_level,
            r.data_date,
            r.fetched_date,
            rf.has_gluten_free_options,
            rf.has_vegetarian_options,
            rf.has_vegan_options,
            rf.has_lactose_free_options,
            rf.celiac_certified,
            s.name as source_name
        FROM restaurants r
        LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
        LEFT JOIN sources s ON r.source_id = s.source_id
        WHERE r.is_active = TRUE
        ORDER BY r.province, r.city, r.name
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "restaurants.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} restaurants to restaurants.csv")
    
    # 2. Export restaurant features
    cur.execute("""
        SELECT 
            rf.restaurant_id,
            r.name,
            r.province,
            r.city,
            rf.has_gluten_free_options,
            rf.has_vegetarian_options,
            rf.has_vegan_options,
            rf.has_lactose_free_options,
            rf.celiac_certified
        FROM restaurant_features rf
        JOIN restaurants r ON rf.restaurant_id = r.restaurant_id
        WHERE r.is_active = TRUE
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "restaurant_features.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} features to restaurant_features.csv")
    
    # 3. Export sources
    cur.execute("SELECT * FROM sources ORDER BY source_id")
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "sources.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} sources to sources.csv")
    
    # 4. Export aggregated data: by province
    cur.execute("""
        SELECT 
            province,
            COUNT(*) as total_restaurants,
            COUNT(CASE WHEN geom IS NOT NULL THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN phone IS NOT NULL THEN 1 END) as with_phone,
            COUNT(CASE WHEN rating IS NOT NULL THEN 1 END) as with_rating,
            ROUND(AVG(price_range)::numeric, 1) as avg_price,
            ROUND(AVG(rating)::numeric, 2) as avg_rating
        FROM restaurants 
        WHERE is_active = TRUE
        GROUP BY province
        ORDER BY total_restaurants DESC
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "by_province.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} provinces to by_province.csv")
    
    # 5. Export aggregated data: by city
    cur.execute("""
        SELECT 
            province,
            city,
            COUNT(*) as total_restaurants,
            COUNT(CASE WHEN geom IS NOT NULL THEN 1 END) as with_coordinates,
            ROUND(AVG(price_range)::numeric, 1) as avg_price
        FROM restaurants 
        WHERE is_active = TRUE AND city IS NOT NULL
        GROUP BY province, city
        ORDER BY total_restaurants DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "by_city.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} cities to by_city.csv")
    
    # 6. Export aggregated data: by cuisine
    cur.execute("""
        SELECT 
            unnest(cuisine_type) as cuisine,
            COUNT(*) as total_restaurants,
            COUNT(DISTINCT r.province) as provinces
        FROM restaurants r
        WHERE is_active = TRUE AND cuisine_type IS NOT NULL
        GROUP BY cuisine
        ORDER BY total_restaurants DESC
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "by_cuisine.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} cuisines to by_cuisine.csv")
    
    # 7. Export aggregated data: by category
    cur.execute("""
        SELECT 
            category,
            COUNT(*) as total_restaurants,
            ROUND(AVG(price_range)::numeric, 1) as avg_price
        FROM restaurants 
        WHERE is_active = TRUE AND category IS NOT NULL
        GROUP BY category
        ORDER BY total_restaurants DESC
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "by_category.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} categories to by_category.csv")
    
    # 8. Export dietary features summary
    cur.execute("""
        SELECT 
            r.province,
            COUNT(CASE WHEN rf.has_gluten_free_options = TRUE THEN 1 END) as gluten_free,
            COUNT(CASE WHEN rf.has_vegetarian_options = TRUE THEN 1 END) as vegetarian,
            COUNT(CASE WHEN rf.has_vegan_options = TRUE THEN 1 END) as vegan,
            COUNT(CASE WHEN rf.has_lactose_free_options = TRUE THEN 1 END) as lactose_free,
            COUNT(*) as total
        FROM restaurants r
        LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
        WHERE r.is_active = TRUE
        GROUP BY r.province
        ORDER BY total DESC
    """)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    
    with open(csv_dir / "dietary_by_province.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Exported {len(rows)} rows to dietary_by_province.csv")
    
    cur.close()
    conn.close()
    
    print("\nAll CSV files exported to analytics/csv/")


if __name__ == "__main__":
    export_data()
