-- =====================================================
-- GASTRONOMIA - Mantenimiento de la base
-- Ejecutar después de cargar datos y cuando la base esté lenta:
--   psql "$DATABASE_URL" -f database/maintenance.sql
-- El backend también aplica lo esencial al iniciar (OPTIMIZAR_AL_INICIAR=1).
-- =====================================================

-- Estadísticas del planificador: sin esto PostgreSQL no sabe cuántas filas hay.
ANALYZE restaurants;
ANALYZE restaurant_features;
ANALYZE sources;
ANALYZE menus;

-- Búsquedas por texto con ILIKE '%...%': los índices B-Tree no sirven,
-- trigram sí.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_restaurants_city_trgm
    ON restaurants USING GIN (city gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_restaurants_province_trgm
    ON restaurants USING GIN (province gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_restaurants_name_trgm
    ON restaurants USING GIN (name gin_trgm_ops);

-- Orden por rating (hoy casi todo NULL, pero el índice queda listo).
CREATE INDEX IF NOT EXISTS idx_restaurants_rating_act
    ON restaurants (rating DESC NULLS LAST) WHERE is_active;

-- Filtros alimentarios: índice parcial por cada bandera.
CREATE INDEX IF NOT EXISTS idx_features_gluten_act
    ON restaurant_features (restaurant_id) WHERE has_gluten_free_options IS TRUE;
CREATE INDEX IF NOT EXISTS idx_features_vegetariano_act
    ON restaurant_features (restaurant_id) WHERE has_vegetarian_options IS TRUE;
CREATE INDEX IF NOT EXISTS idx_features_vegano_act
    ON restaurant_features (restaurant_id) WHERE has_vegan_options IS TRUE;

-- Cercanía: GiST sobre geom (ya existe en schema.sql; se repite por si acaso).
CREATE INDEX IF NOT EXISTS idx_restaurants_geom
    ON restaurants USING GIST (geom);
