-- =====================================================
-- GASTRO IA - Database Schema
-- PostgreSQL + PostGIS
-- =====================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =====================================================
-- TABLA: sources
-- =====================================================
CREATE TABLE IF NOT EXISTS sources (
    source_id       SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    url             VARCHAR(500),
    source_type     VARCHAR(50) NOT NULL,
    license         VARCHAR(100),
    update_frequency VARCHAR(50),
    last_updated    DATE,
    reliability     VARCHAR(30) NOT NULL,
    notes           TEXT,
    fetched_date    DATE NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TABLA: restaurants
-- =====================================================
CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id   SERIAL PRIMARY KEY,
    name            VARCHAR(300) NOT NULL,
    province        VARCHAR(100) NOT NULL,
    city            VARCHAR(200) NOT NULL,
    neighborhood    VARCHAR(200),
    region          VARCHAR(20),     -- CABA, GBA o Sin confirmar
    district        VARCHAR(100),    -- partido de GBA (ej.: Lomas de Zamora)
    zone_macro      VARCHAR(50),     -- CABA, GBA Norte, GBA Oeste, GBA Sur
    address         VARCHAR(500),
    latitude        DECIMAL(10, 8),
    longitude       DECIMAL(11, 8),
    geom            GEOMETRY(Point, 4326),
    cuisine_type    TEXT[],
    category        VARCHAR(50),
    phone           VARCHAR(50),
    email           VARCHAR(300),
    website         VARCHAR(300),
    social_media    JSONB,
    opening_hours   TEXT,
    price_range     SMALLINT CHECK (price_range BETWEEN 1 AND 4),
    rating          DECIMAL(2, 1),
    review_count    INTEGER,
    source_id       INTEGER REFERENCES sources(source_id),
    source_type     VARCHAR(50),
    confidence_level VARCHAR(30) NOT NULL DEFAULT 'no_verified',
    data_date       DATE,
    fetched_date    DATE NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_restaurants_geom ON restaurants USING GIST(geom);
CREATE INDEX idx_restaurants_province ON restaurants(province);
CREATE INDEX idx_restaurants_city ON restaurants(city);

-- Jerarquía Región > Partido > Zona (si la tabla ya existía de antes, se agregan las columnas)
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS region     VARCHAR(20);
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS district   VARCHAR(100);
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS zone_macro VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_restaurants_zone ON restaurants(zone_macro);
CREATE INDEX IF NOT EXISTS idx_restaurants_district ON restaurants(district);
CREATE INDEX idx_restaurants_cuisine ON restaurants USING GIN(cuisine_type);
CREATE INDEX idx_restaurants_price ON restaurants(price_range);
CREATE INDEX idx_restaurants_rating ON restaurants(rating);
CREATE INDEX idx_restaurants_name_trgm ON restaurants USING GIN(name gin_trgm_ops);
CREATE INDEX idx_restaurants_city_trgm ON restaurants USING GIN(city gin_trgm_ops);
CREATE INDEX idx_restaurants_province_trgm ON restaurants USING GIN(province gin_trgm_ops);
CREATE INDEX idx_restaurants_source ON restaurants(source_id);
CREATE INDEX idx_restaurants_confidence ON restaurants(confidence_level);
CREATE INDEX idx_restaurants_active ON restaurants(is_active);
CREATE INDEX idx_restaurants_rating_act ON restaurants (rating DESC NULLS LAST) WHERE is_active;

-- =====================================================
-- TABLA: restaurant_features
-- =====================================================
CREATE TABLE IF NOT EXISTS restaurant_features (
    id                      SERIAL PRIMARY KEY,
    restaurant_id           INTEGER REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    has_gluten_free_options BOOLEAN,
    has_vegetarian_options  BOOLEAN,
    has_vegan_options       BOOLEAN,
    has_lactose_free_options BOOLEAN,
    celiac_certified        BOOLEAN DEFAULT FALSE,
    source_id               INTEGER REFERENCES sources(source_id),
    confidence_level        VARCHAR(30) DEFAULT 'no_verified',
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rest_features_restaurant ON restaurant_features(restaurant_id);
CREATE INDEX idx_features_gluten_act ON restaurant_features(restaurant_id) WHERE has_gluten_free_options IS TRUE;
CREATE INDEX idx_features_vegetariano_act ON restaurant_features(restaurant_id) WHERE has_vegetarian_options IS TRUE;
CREATE INDEX idx_features_vegano_act ON restaurant_features(restaurant_id) WHERE has_vegan_options IS TRUE;

-- =====================================================
-- TABLA: menus
-- =====================================================
CREATE TABLE IF NOT EXISTS menus (
    menu_id         SERIAL PRIMARY KEY,
    restaurant_id   INTEGER REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    dish_name       VARCHAR(300) NOT NULL,
    category        VARCHAR(100),
    description     TEXT,
    price           DECIMAL(10, 2),
    currency        VARCHAR(3) DEFAULT 'ARS',
    ingredients     TEXT[],
    source_id       INTEGER REFERENCES sources(source_id),
    confidence_level VARCHAR(30) DEFAULT 'no_verified',
    data_date       DATE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_menus_restaurant ON menus(restaurant_id);
CREATE INDEX idx_menus_price ON menus(price);

-- =====================================================
-- TABLA: dish_features
-- =====================================================
CREATE TABLE IF NOT EXISTS dish_features (
    feature_id      SERIAL PRIMARY KEY,
    menu_id         INTEGER REFERENCES menus(menu_id) ON DELETE CASCADE,
    gluten_free     BOOLEAN,
    vegetarian      BOOLEAN,
    vegan           BOOLEAN,
    lactose_free    BOOLEAN,
    low_carb        BOOLEAN,
    contains_gluten BOOLEAN,
    contains_lactose BOOLEAN,
    contains_egg    BOOLEAN,
    contains_nuts   BOOLEAN,
    carbohydrates   DECIMAL(5, 2),
    sugars          DECIMAL(5, 2),
    fiber           DECIMAL(5, 2),
    proteins        DECIMAL(5, 2),
    fats            DECIMAL(5, 2),
    portion_size    VARCHAR(50),
    source_id       INTEGER REFERENCES sources(source_id),
    confidence_level VARCHAR(30) DEFAULT 'no_verified',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dish_features_menu ON dish_features(menu_id);

-- =====================================================
-- TABLA: query_logs
-- =====================================================
CREATE TABLE IF NOT EXISTS query_logs (
    log_id              SERIAL PRIMARY KEY,
    session_id          VARCHAR(100),
    user_query          TEXT,
    parsed_params       JSONB,
    restaurants_found   INTEGER,
    restaurants_recommended INTEGER,
    tools_called        JSONB,
    response_time_ms    INTEGER,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TRIGGERS
-- =====================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_restaurants_updated
    BEFORE UPDATE ON restaurants
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_menus_updated
    BEFORE UPDATE ON menus
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- =====================================================
-- VISTAS
-- =====================================================
CREATE OR REPLACE VIEW v_restaurants_with_features AS
SELECT 
    r.*,
    rf.has_gluten_free_options,
    rf.has_vegetarian_options,
    rf.has_vegan_options,
    rf.has_lactose_free_options,
    rf.celiac_certified,
    s.name as source_name,
    s.url as source_url,
    s.reliability as source_reliability
FROM restaurants r
LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
LEFT JOIN sources s ON r.source_id = s.source_id
WHERE r.is_active = TRUE;

CREATE OR REPLACE VIEW v_source_stats AS
SELECT 
    s.source_id,
    s.name as source_name,
    s.source_type,
    s.reliability,
    COUNT(r.restaurant_id) as restaurant_count,
    COUNT(m.menu_id) as menu_count,
    AVG(r.rating) as avg_rating
FROM sources s
LEFT JOIN restaurants r ON s.source_id = r.source_id
LEFT JOIN menus m ON r.restaurant_id = m.restaurant_id
GROUP BY s.source_id, s.name, s.source_type, s.reliability;

-- =====================================================
-- ESTADÍSTICAS
-- =====================================================
ANALYZE restaurants;
ANALYZE restaurant_features;
ANALYZE sources;
ANALYZE menus;
