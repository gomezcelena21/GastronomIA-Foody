# Gastro IA - Analytics y Power BI

## Archivos Disponibles

### CSV (para importar a Power BI)
| Archivo | Descripción | Registros |
|---------|-------------|-----------|
| `csv/restaurants.csv` | Todos los restaurantes con todas sus columnas | 6,187 |
| `csv/restaurant_features.csv` | Características dietarias por restaurante | 6,187 |
| `csv/sources.csv` | Fuentes de datos utilizadas | 3 |
| `csv/by_province.csv` | Resumen agregado por provincia | 4 |
| `csv/by_city.csv` | Resumen agregado por ciudad | 50 |
| `csv/by_cuisine.csv` | Resumen agregado por tipo de cocina | 145 |
| `csv/by_category.csv` | Resumen agregado por categoría | 11 |
| `csv/dietary_by_province.csv` | Características dietarias por provincia | 4 |

### Excel (para importar a Power BI)
| Archivo | Descripción |
|---------|-------------|
| `GastroIA_PowerBI.xlsx` | Archivo único con todas las hojas |

### Hojas del Excel
1. **Restaurantes** - Tabla principal con todos los campos
2. **Por Provincia** - KPIs agregados por provincia
3. **Por Tipo Cocina** - Conteo por tipo de cocina
4. **Por Categoria** - Conteo por categoría gastronómica
5. **Caracteristicas Dietarias** - Opciones sin TACC, vegetarianas, veganas
6. **Fuentes** - Información de las fuentes de datos

## Cómo Importar a Power BI Desktop

### Opción 1: Importar CSV
1. Abrir Power BI Desktop
2. Hacer clic en "Obtener datos" → "Texto/CSV"
3. Seleccionar el archivo CSV deseado
4. Hacer clic en "Cargar"

### Opción 2: Importar Excel
1. Abrir Power BI Desktop
2. Hacer clic en "Obtener datos" → "Libro de Excel"
3. Seleccionar `GastroIA_PowerBI.xlsx`
4. Seleccionar las hojas que se deseen importar
5. Hacer clic en "Cargar"

## Relaciones entre Tablas

```
restaurants.restaurant_id → restaurant_features.restaurant_id
restaurants.source_id → sources.source_id
```

## Diccionario de Datos

### Tabla: restaurants
| Campo | Tipo | Descripción |
|-------|------|-------------|
| restaurant_id | INTEGER | ID único del restaurante |
| name | TEXT | Nombre del restaurante |
| province | TEXT | Provincia argentina |
| city | TEXT | Ciudad o localidad |
| neighborhood | TEXT | Barrio |
| address | TEXT | Dirección completa |
| latitude | FLOAT | Latitud (WGS84) |
| longitude | FLOAT | Longitud (WGS84) |
| cuisine_type | TEXT[] | Tipos de cocina (array) |
| category | TEXT | Categoría (restaurante, café, bar, etc.) |
| phone | TEXT | Teléfono de contacto |
| email | TEXT | Email de contacto |
| website | TEXT | Sitio web |
| opening_hours | TEXT | Horarios de apertura |
| price_range | INTEGER | Rango de precios (1-4) |
| rating | FLOAT | Calificación (0-5) |
| review_count | INTEGER | Cantidad de reseñas |
| source_type | TEXT | Tipo de fuente (osm, ba_data, etc.) |
| confidence_level | TEXT | Nivel de confianza (official, public_source, community) |
| data_date | DATE | Fecha de los datos originales |
| fetched_date | TIMESTAMP | Fecha de obtención de los datos |

### Tabla: restaurant_features
| Campo | Tipo | Descripción |
|-------|------|-------------|
| restaurant_id | INTEGER | FK → restaurants.restaurant_id |
| has_gluten_free_options | BOOLEAN | Tiene opciones sin TACC |
| has_vegetarian_options | BOOLEAN | Tiene opciones vegetarianas |
| has_vegan_options | BOOLEAN | Tiene opciones veganas |
| has_lactose_free_options | BOOLEAN | Tiene opciones sin lactosa |
| celiac_certified | BOOLEAN | Certificado para celíacos |

### Tabla: sources
| Campo | Tipo | Descripción |
|-------|------|-------------|
| source_id | INTEGER | ID único de la fuente |
| name | TEXT | Nombre de la fuente |
| source_type | TEXT | Tipo (api, scraping, manual, etc.) |
| url | TEXT | URL de la fuente |
| license | TEXT | Licencia de los datos |
| reliability | TEXT | Confiabilidad (official, public, community) |
| last_updated | DATE | Última actualización |

## Métricas/KPIs Recomendadas para Power BI

### KPIs Principales
1. **Total de Restaurantes**: 6,187
2. **Provincias Cubiertas**: 4
3. **Ciudades Cubiertas**: ~50
4. **Con Coordenadas**: 85%
5. **Tipos de Cocina**: 145

### Métricas por Provincia
- Restaurantes por provincia
- Promedio de precios por provincia
- Cobertura geográfica (% con coordenadas)

### Métricas de Calidad
- % de registros con información completa
- % de registros con coordenadas
- Distribución por nivel de confianza

### Métricas de Contenido
- Top 10 tipos de cocina
- Distribución por categoría
- Características dietarias disponibles

## Notas
- Los archivos CSV están codificados en UTF-8
- Los valores nulos aparecen como cadenas vacías
- Las coordenadas están en formato WGS84 (EPSG:4326)
- Los tipos de cocina están en formato array (separados por comas en CSV)
