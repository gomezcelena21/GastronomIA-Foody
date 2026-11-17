"""
Gastro IA - Analytics Script
Runs comprehensive data analysis on the PostgreSQL database.
"""

import psycopg2
import json
import os
from pathlib import Path

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "gastro_ia",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", ""),  # antes: contraseña escrita acá. Usá: set PGPASSWORD=tu_clave
}

def run_analysis():
    """Run all analysis queries."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    results = {}
    
    # 1. Total restaurants
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE")
    results['total'] = cur.fetchone()[0]
    
    # 2. By province
    cur.execute("""
        SELECT COALESCE(province, 'Sin especificar') as province, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE 
        GROUP BY province ORDER BY count DESC
    """)
    results['by_province'] = cur.fetchall()
    
    # 3. By city (top 25)
    cur.execute("""
        SELECT COALESCE(city, 'Sin especificar') as city, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE 
        GROUP BY city ORDER BY count DESC LIMIT 25
    """)
    results['by_city'] = cur.fetchall()
    
    # 4. By cuisine type
    cur.execute("""
        SELECT COALESCE(cuisine, 'Sin especificar') as cuisine, COUNT(*) as count 
        FROM restaurants, unnest(cuisine_type) as cuisine
        WHERE is_active = TRUE 
        GROUP BY cuisine ORDER BY count DESC LIMIT 20
    """)
    results['by_cuisine'] = cur.fetchall()
    
    # 5. By category
    cur.execute("""
        SELECT COALESCE(category, 'Sin especificar') as category, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE 
        GROUP BY category ORDER BY count DESC
    """)
    results['by_category'] = cur.fetchall()
    
    # 6. By source_type
    cur.execute("""
        SELECT COALESCE(source_type, 'Sin especificar') as source_type, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE 
        GROUP BY source_type ORDER BY count DESC
    """)
    results['by_source'] = cur.fetchall()
    
    # 7. By confidence_level
    cur.execute("""
        SELECT COALESCE(confidence_level, 'Sin especificar') as confidence_level, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE 
        GROUP BY confidence_level ORDER BY count DESC
    """)
    results['by_confidence'] = cur.fetchall()
    
    # 8. With coordinates
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND geom IS NOT NULL")
    results['with_coords'] = cur.fetchone()[0]
    
    # 9. With phone
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND phone IS NOT NULL")
    results['with_phone'] = cur.fetchone()[0]
    
    # 10. With rating
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND rating IS NOT NULL")
    results['with_rating'] = cur.fetchone()[0]
    
    # 11. With address
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND address IS NOT NULL")
    results['with_address'] = cur.fetchone()[0]
    
    # 12. With email
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND email IS NOT NULL")
    results['with_email'] = cur.fetchone()[0]
    
    # 13. With website
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND website IS NOT NULL")
    results['with_website'] = cur.fetchone()[0]
    
    # 14. With opening_hours
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND opening_hours IS NOT NULL")
    results['with_hours'] = cur.fetchone()[0]
    
    # 15. Price range distribution
    cur.execute("""
        SELECT price_range, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE AND price_range IS NOT NULL 
        GROUP BY price_range ORDER BY price_range
    """)
    results['by_price'] = cur.fetchall()
    
    # 16. Dietary features
    cur.execute("SELECT COUNT(*) FROM restaurant_features WHERE has_gluten_free_options = TRUE")
    results['gf_count'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurant_features WHERE has_vegetarian_options = TRUE")
    results['veg_count'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurant_features WHERE has_vegan_options = TRUE")
    results['vegan_count'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurant_features WHERE has_lactose_free_options = TRUE")
    results['lactose_count'] = cur.fetchone()[0]
    
    # 17. Nulls analysis
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (name IS NULL OR name = '')")
    results['null_name'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (province IS NULL OR province = '')")
    results['null_province'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (city IS NULL OR city = '')")
    results['null_city'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (neighborhood IS NULL OR neighborhood = '')")
    results['null_neighborhood'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (address IS NULL OR address = '')")
    results['null_address'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (phone IS NULL OR phone = '')")
    results['null_phone'] = cur.fetchone()[0]
    
    # 18. Duplicates (by name within same province)
    cur.execute("""
        SELECT name, province, COUNT(*) as cnt 
        FROM restaurants WHERE is_active = TRUE 
        GROUP BY name, province HAVING COUNT(*) > 1 
        ORDER BY cnt DESC LIMIT 15
    """)
    results['duplicates'] = cur.fetchall()
    
    # 19. Province with most/least
    cur.execute("""
        SELECT province, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE AND province IS NOT NULL
        GROUP BY province ORDER BY count DESC LIMIT 1
    """)
    results['max_province'] = cur.fetchone()
    cur.execute("""
        SELECT province, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE AND province IS NOT NULL
        GROUP BY province ORDER BY count ASC LIMIT 1
    """)
    results['min_province'] = cur.fetchone()
    
    # 20. City with most/least
    cur.execute("""
        SELECT city, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE AND city IS NOT NULL
        GROUP BY city ORDER BY count DESC LIMIT 1
    """)
    results['max_city'] = cur.fetchone()
    cur.execute("""
        SELECT city, COUNT(*) as count 
        FROM restaurants WHERE is_active = TRUE AND city IS NOT NULL
        GROUP BY city ORDER BY count ASC LIMIT 1
    """)
    results['min_city'] = cur.fetchone()
    
    # 21. Rating distribution
    cur.execute("""
        SELECT 
            CASE 
                WHEN rating >= 4.5 THEN '4.5-5.0'
                WHEN rating >= 4.0 THEN '4.0-4.4'
                WHEN rating >= 3.5 THEN '3.5-3.9'
                WHEN rating >= 3.0 THEN '3.0-3.4'
                WHEN rating >= 2.0 THEN '2.0-2.9'
                ELSE '0-1.9'
            END as rating_range,
            COUNT(*) as count
        FROM restaurants WHERE is_active = TRUE AND rating IS NOT NULL
        GROUP BY rating_range ORDER BY rating_range DESC
    """)
    results['by_rating'] = cur.fetchall()
    
    # 22. Sources info
    cur.execute("""
        SELECT s.name, s.source_type, s.reliability, COUNT(r.restaurant_id) as count
        FROM sources s
        LEFT JOIN restaurants r ON s.source_id = r.source_id AND r.is_active = TRUE
        GROUP BY s.source_id, s.name, s.source_type, s.reliability
        ORDER BY count DESC
    """)
    results['sources_detail'] = cur.fetchall()
    
    # 23. Avg rating by province
    cur.execute("""
        SELECT province, ROUND(AVG(rating)::numeric, 2) as avg_rating, COUNT(*) as count
        FROM restaurants WHERE is_active = TRUE AND rating IS NOT NULL AND province IS NOT NULL
        GROUP BY province HAVING COUNT(*) >= 5
        ORDER BY avg_rating DESC
    """)
    results['avg_rating_by_province'] = cur.fetchall()
    
    # 24. Cuisine by province (top 5 provinces)
    cur.execute("""
        SELECT province, cuisine, count
        FROM (
            SELECT province, unnest(cuisine_type) as cuisine, COUNT(*) as count,
                   ROW_NUMBER() OVER (PARTITION BY province ORDER BY COUNT(*) DESC) as rn
            FROM restaurants 
            WHERE is_active = TRUE AND province IS NOT NULL AND cuisine_type IS NOT NULL
            GROUP BY province, cuisine
        ) sub
        WHERE rn <= 3
        ORDER BY province, count DESC
    """)
    results['cuisine_by_province'] = cur.fetchall()
    
    # Save results
    analytics_dir = Path(__file__).parent / "analytics"
    analytics_dir.mkdir(exist_ok=True)
    
    with open(analytics_dir / "analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print("Analysis complete! Results saved to analytics/analysis_results.json")
    
    # Print summary
    print("\n" + "="*60)
    print("ANALISIS EXPLORATORIO DE DATOS - RESUMEN")
    print("="*60)
    print(f"\nTotal de restaurantes: {results['total']}")
    print(f"\nPor provincia:")
    for p, c in results['by_province']:
        print(f"  {p}: {c}")
    print(f"\nTop 5 ciudades:")
    for city, c in results['by_city'][:5]:
        print(f"  {city}: {c}")
    print(f"\nTop 5 tipos de cocina:")
    for cuisine, c in results['by_cuisine'][:5]:
        print(f"  {cuisine}: {c}")
    print(f"\nCategorias:")
    for cat, c in results['by_category']:
        print(f"  {cat}: {c}")
    print(f"\nFuentes de datos:")
    for src, c in results['by_source']:
        print(f"  {src}: {c}")
    print(f"\nNivel de confianza:")
    for conf, c in results['by_confidence']:
        print(f"  {conf}: {c}")
    print(f"\nDisponibilidad de datos:")
    print(f"  Con coordenadas: {results['with_coords']} ({results['with_coords']*100//results['total']}%)")
    print(f"  Con telefono: {results['with_phone']} ({results['with_phone']*100//results['total']}%)")
    print(f"  Con rating: {results['with_rating']} ({results['with_rating']*100//results['total']}%)")
    print(f"  Con direccion: {results['with_address']} ({results['with_address']*100//results['total']}%)")
    print(f"\nCaracteristicas dietarias:")
    print(f"  Sin TACC: {results['gf_count']}")
    print(f"  Vegetariano: {results['veg_count']}")
    print(f"  Vegano: {results['vegan_count']}")
    print(f"\nProvincia con mas registros: {results['max_province']}")
    print(f"Provincia con menos registros: {results['min_province']}")
    print(f"Ciudad con mas registros: {results['max_city']}")
    print(f"Ciudad con menos registros: {results['min_city']}")
    
    cur.close()
    conn.close()
    
    return results


if __name__ == "__main__":
    run_analysis()
