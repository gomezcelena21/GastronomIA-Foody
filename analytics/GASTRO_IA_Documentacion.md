# Gastro IA - Documentacion Completa del Proyecto

---

## 1. Nombre y Objetivo del Proyecto

**Nombre:** Gastro IA

**Objetivo:** Desarrollar un asistente gastronomico inteligente para Argentina que utilize inteligencia artificial (Google Gemini) combinada con una base de datos georreferenciada de restaurantes para ayudar a los usuarios a encontrar opciones de comida segun sus necesidades, preferencias y ubicacion.

---

## 2. Problema que Busca Resolver

En Argentina no existe una plataforma centralizada que permita encontrar restaurantes con informacion confiable sobre opciones para personas con restricciones alimentarias (celiaquismo, vegetarianismo, veganismo). Los usuarios deben consultar multiples fuentes y no pueden verificar la veracidad de la informacion.

Gastro IA busca resolver este problema ofreciendo una unica interfaz conversacional que consulta fuentes verificadas y muestra la trazabilidad de cada dato.

---

## 3. Publico Objetivo

- Personas con celiaquia que buscan opciones sin TACC
- Vegetarianos y veganos que buscan restaurantes adaptados
- Personas con intolerancia a la lactosa
- Turistas y locales que quieren descubrir restaurantes
- Personas con presupuesto limitado
- Cualquier persona que busque recomendaciones gastronomicas personalizadas

---

## 4. Funcionamiento General

El sistema funciona mediante una arquitectura de tres capas:

1. **Frontend (React):** Interfaz de usuario con chat y dashboard
2. **Backend (FastAPI):** Logica de negocio y conexion con base de datos
3. **AI (Gemini):** Procesamiento de lenguaje natural y function calling

El usuario escribe un mensaje en el chat. El backend lo envia a Gemini, que decide que funcion ejecutar (buscar restaurantes, obtener detalles, etc.). El backend ejecuta la funcion contra PostgreSQL y devuelve el resultado a Gemini, que genera una respuesta natural para el usuario.

---

## 5. Arquitectura del Sistema

```
+-----------+     +-----------+     +-----------+
|  React    | --> |  FastAPI  | --> |  Gemini   |
| Frontend  |     | Backend   |     |    AI     |
+-----------+     +-----------+     +-----------+
                          |                |
                          v                v
                    +-----------+    +-----------+
                    | PostgreSQL|    |  Tools    |
                    | + PostGIS |    |  (APIs)   |
                    +-----------+    +-----------+
```

---

## 6. Frontend

**Tecnologias utilizadas:**
- React 18 con TypeScript
- Vite como bundler
- react-markdown para renderizar respuestas
- chart.js y react-chartjs-2 para graficos del dashboard
- CSS personalizado con variables de color

El frontend esta compuesto por dos vistas principales:
- **Vista del asistente:** Chat conversacional con filtros laterales
- **Vista del dashboard:** Analitica visual con KPIs y graficos

---

## 7. Backend

**Tecnologias utilizadas:**
- Python 3.14
- FastAPI como framework web
- SQLAlchemy como ORM
- psycopg2 como driver de PostgreSQL
- python-dotenv para variables de entorno

**Endpoints principales:**
- `POST /api/chat` - Envia mensajes al asistente
- `GET /api/restaurants` - Busca restaurantes con filtros
- `GET /api/analytics` - Datos para el dashboard
- `GET /api/stats` - Estadisticas generales
- `GET /api/provinces` - Lista de provincias
- `GET /api/cuisines` - Tipos de cocina disponibles

---

## 8. API de Gemini

Se utiliza Google Gemini (modelo gemini-2.0-flash) como capa de IA. Gemini procesa el lenguaje natural del usuario y decide que funciones ejecutar para obtener datos reales de la base de datos.

La integracion se realiza mediante el paquete google-generativeai. Se configura con un system prompt que define el comportamiento del asistente y las reglas de seguridad (no inventar datos, advertir sobre informacion no verificada, etc.).

---

## 9. Funcionamiento del Asistente

El asistente conversacional funciona de la siguiente manera:

1. El usuario escribe un mensaje
2. El backend envia el mensaje a Gemini junto con el historial de la sesion
3. Gemini analiza la intencion y decide si necesita ejecutar alguna funcion
4. Si necesita datos, Gemini solicita ejecutar un tool (funcion)
5. El backend ejecuta la funcion contra PostgreSQL
6. El resultado se devuelve a Gemini
7. Gemini genera una respuesta natural basada en los datos reales
8. La respuesta se muestra al usuario en el frontend

---

## 10. Function Calling / Tools

**Tools disponibles para Gemini:**

- `buscar_restaurantes` - Busca restaurantes por provincia, ciudad, tipo de cocina, presupuesto, necesidades dietarias
- `obtener_detalle_restaurante` - Obtiene informacion detallada de un restaurante especifico
- `buscar_por_cercania` - Encuentra restaurantes cercanos a unas coordenadas usando PostGIS
- `obtener_fuentes` - Devuelve informacion de trazabilidad de un restaurante

Cada tool esta definido con su esquema de parametros en formato JSON Schema. Gemini decide automaticamente cual tool usar segun la pregunta del usuario.

---

## 11. PostgreSQL

Se utiliza PostgreSQL 17 como motor de base de datos. La base de datos se llama "gastro_ia" y contiene las siguientes tablas principales:

- `restaurants` - Tabla principal con 6,187 restaurantes
- `restaurant_features` - Caracteristicas dietarias por restaurante
- `sources` - Fuentes de datos utilizadas
- `query_logs` - Registro de consultas (pendiente)

---

## 12. PostGIS

PostGIS 3.6.2 esta instalado como extension de PostgreSQL. Permite realizar consultas geoespaciales como:

- Encontrar restaurantes cercanos a unas coordenadas
- Calcular distancias entre puntos
- Filtrar por radio de busqueda

La columna "geom" de tipo GEOMETRY esta indexada con un indice GiST para consultas espaciales eficientes.

---

## 13. Estructura de la Base de Datos

```
gastro_ia (PostgreSQL 17 + PostGIS 3.6.2)
|
+-- restaurants (6,187 registros)
|   +-- restaurant_id (PK)
|   +-- name, province, city, neighborhood, address
|   +-- latitude, longitude, geom (PostGIS)
|   +-- cuisine_type[], category, phone, email
|   +-- website, opening_hours, price_range, rating
|   +-- source_id (FK), confidence_level
|
+-- restaurant_features (6,187 registros)
|   +-- restaurant_id (FK)
|   +-- has_gluten_free_options, has_vegetarian_options
|   +-- has_vegan_options, has_lactose_free_options
|
+-- sources (3 registros)
    +-- source_id (PK)
    +-- name, source_type, url, license, reliability
```

---

## 14. Tablas y Campos Principales

### Tabla restaurants

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| restaurant_id | INTEGER | Identificador unico |
| name | TEXT | Nombre del restaurante |
| province | TEXT | Provincia argentina |
| city | TEXT | Ciudad o localidad |
| neighborhood | TEXT | Barrio (opcional) |
| address | TEXT | Direccion completa |
| latitude | FLOAT | Latitud WGS84 |
| longitude | FLOAT | Longitud WGS84 |
| geom | GEOMETRY | Geometria PostGIS |
| cuisine_type | TEXT[] | Tipos de cocina |
| category | TEXT | Categoria gastronomica |
| phone | TEXT | Telefono de contacto |
| price_range | INTEGER | Rango de precios 1-4 |
| rating | FLOAT | Calificacion 0-5 |
| source_id | INTEGER | FK a sources |
| confidence_level | TEXT | Nivel de confianza |

### Tabla restaurant_features

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| restaurant_id | INTEGER | FK a restaurants |
| has_gluten_free_options | BOOLEAN | Opciones sin TACC |
| has_vegetarian_options | BOOLEAN | Opciones vegetarianas |
| has_vegan_options | BOOLEAN | Opciones veganas |
| has_lactose_free_options | BOOLEAN | Opciones sin lactosa |

### Tabla sources

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| source_id | INTEGER | Identificador unico |
| name | TEXT | Nombre de la fuente |
| source_type | TEXT | Tipo de fuente |
| url | TEXT | URL de la fuente |
| reliability | TEXT | Confiabilidad |

---

## 15. Proceso ETL

El proceso ETL (Extract, Transform, Load) se ejecuta desde la carpeta `/etl` y consta de las siguientes fases:

1. **Extract:** Descarga datos de BA Data, OpenStreetMap (Overpass API) y CSV de Mendoza
2. **Transform:** Normaliza tipos de cocina, limpia telefonos, estandariza direcciones
3. **Validate:** Verifica coordenadas, nombres, provincias
4. **Dedup:** Elimina duplicados por nombre dentro de cada fuente
5. **Load:** Carga los datos en PostgreSQL con source_id y timestamp

---

## 16. Origen y Tratamiento de los Datos

**Fuentes de datos utilizadas:**

| Fuente | Registros | Tipo |
|--------|-----------|------|
| BA Data (Buenos Aires) | 2,549 | Oficial |
| OpenStreetMap Overpass API | 2,729 | Comunidad |
| Mendoza Official | 909 | Oficial |
| **Total** | **6,187** | |

Los datos pasan por un proceso de validacion y deduplicacion antes de ser cargados. Se asigna un nivel de confianza (official, public_source, community) segun la fuente.

---

## 17. Como el Asistente Consulta los Datos

Cuando el usuario pregunta "Que restaurantes sin TACC hay en Palermo?", el flujo es:

1. Gemini recibe el mensaje
2. Decide usar el tool `buscar_restaurantes`
3. Pasa los parametros: `{ciudad: "Palermo", requiere_sin_tacc: true}`
4. El backend ejecuta una consulta SQL con filtros
5. Devuelve los restaurantes que coinciden
6. Gemini genera una respuesta natural con los datos

---

## 18. Flujo Completo

```
USUARIO
  |
  v
[React Frontend]
  | POST /api/chat
  v
[FastAPI Backend]
  | send_message()
  v
[Gemini API]
  | function_call: buscar_restaurantes()
  v
[Chat Service]
  | SELECT * FROM restaurants
  | WHERE province = 'Buenos Aires'
  | AND has_gluten_free_options = TRUE
  v
[PostgreSQL + PostGIS]
  | Resultado: [restaurante1, restaurante2, ...]
  v
[Gemini API]
  | Genera respuesta natural
  v
[FastAPI Backend]
  | Devuelve JSON
  v
[React Frontend]
  | Muestra respuesta en chat
  v
USUARIO
```

---

## 19. Variables de Entorno

Las variables de entorno se configuran en el archivo `backend/.env`:

```
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-2.0-flash
```

El archivo `.env` NO debe subirse a repositorios publicos. Debe incluirse en `.gitignore`.

---

## 20. Configuracion de GEMINI_API_KEY

Para obtener una API key de Gemini:

1. Ir a https://aistudio.google.com/apikey
2. Crear una API key
3. Copiarla en el archivo `backend/.env`
4. Reiniciar el backend

---

## 21. Como Iniciar el Proyecto Localmente

### Requisitos Previos

- Python 3.14 o superior
- Node.js 18 o superior
- PostgreSQL 17 con PostGIS 3.6.2
- Una API key de Google Gemini

### Pasos de Instalacion

```bash
# 1. Ir a la carpeta del proyecto
cd "C:\Users\Usuario\Documents\Default Project\gastro_ia"

# 2. Instalar dependencias del frontend
cd frontend
npm install
cd ..

# 3. Configurar API key
echo GEMINI_API_KEY=tu_key > backend\.env

# 4. Iniciar el proyecto
.\restart.bat
```

### URLs de Acceso

- **Frontend:** http://localhost:5173
- **Backend API:** http://127.0.0.1:8001
- **Documentacion API:** http://127.0.0.1:8001/docs

---

## 22. Dashboard y Analisis

El dashboard analitico esta disponible en la interfaz del frontend, accesible desde el boton "Dashboard" en el header. Incluye:

- **KPIs principales:** total de restaurantes, provincias, ciudades, tipos de cocina
- **Grafico de barras:** Restaurantes por provincia
- **Grafico de dona:** Distribucion por tipo de cocina
- **Grafico de barras horizontales:** Distribucion por categoria
- **Grafico circular:** Distribucion por fuente de datos
- **Indicadores de calidad:** completitud, coordenadas, telefonos
- **Pestanas:** Resumen, Geografia, Calidad

---

## 23. Preparacion para Power BI

Se han generado archivos CSV y XLSX en la carpeta `/analytics/csv/` listos para importar a Power BI Desktop:

| Archivo | Registros | Descripcion |
|---------|-----------|-------------|
| restaurants.csv | 6,187 | Todos los restaurantes |
| restaurant_features.csv | 6,187 | Caracteristicas dietarias |
| sources.csv | 3 | Fuentes de datos |
| by_province.csv | 4 | Resumen por provincia |
| by_city.csv | 50 | Resumen por ciudad |
| by_cuisine.csv | 145 | Resumen por tipo de cocina |
| by_category.csv | 11 | Resumen por categoria |
| GastroIA_PowerBI.xlsx | - | Archivo Excel consolidado |

Ver `analytics/README.md` para instrucciones detalladas de importacion y diccionario de datos.

---

## 24. Calidad de Datos

### Fortalezas

- 100% de registros con nombre, provincia, ciudad y direccion
- 100% de registros con telefono
- 85% de registros con coordenadas geograficas
- 55% de registros con nivel de confianza oficial

### Debilidades

- 0% de registros con rating o calificacion
- 0% de registros con horarios de apertura
- 0% de registros con email o website
- 0.1% de registros con informacion sin TACC
- 1.1% de registros con opciones vegetarianas
- 0.7% de registros con opciones veganas

---

## 25. Limitaciones Actuales

- Solo 4 de 24 provincias argentinas tienen datos
- No hay ratings ni resenas de usuarios
- No hay informacion de menus ni precios especificos
- No se puede verificar disponibilidad sin horarios
- La informacion para celiacos es insuficiente (7 registros)
- No hay fotos de restaurantes
- No hay sistema de reservas
- No hay informacion de delivery

---

## 26. Seguridad

- PostgreSQL configurado en modo trust solo para localhost
- La API key de Gemini se almacena en .env (no en codigo)
- El backend no esta expuesto a Internet
- No hay autenticacion de usuarios (pendiente)
- No hay rate limiting (pendiente)
- No hay HTTPS (pendiente para produccion)

---

## 27. Que Deberia Hacerse Antes de Publicar

- Configurar autenticacion de usuarios
- Agregar rate limiting al API
- Configurar HTTPS
- Cambiar PostgreSQL de trust a password/md5
- Agregar validacion de entrada (sanitization)
- Implementar logging y monitoreo
- Configurar CORS para dominio especifico
- Agregar tests automatizados
- Realizar prueba de penetracion
- Configurar backups automaticos de la base de datos

---

## 28. Posibles Mejoras Futuras

- Expandir a todas las provincias argentinas
- Integcar fuentes con ratings (Google Maps, Yelp)
- Agregar informacion de menus y precios en tiempo real
- Implementar sistema de resenas de usuarios
- Agregar fotos de restaurantes
- Mejorar informacion de alergenos
- Implementar sistema de reservas
- Agregar informacion de delivery
- Desarrollar app mobile nativa
- Implementar notificaciones push
- Agregar comparator de restaurantes
- Implementar favoritos y historial

---

## 29. Conclusiones

Gastro IA demuestra la viabilidad de combinar IA conversacional con bases de datos georreferenciadas para crear asistentes inteligentes especializados. El prototipo actual permite buscar restaurantes, filtrar por necesidades alimentarias y obtener informacion trazable.

Los principales desafios pendientes son:
- Expandir la cobertura geografica a todo el pais
- Enriquecer la informacion con ratings, menus y horarios
- Implementar seguridad para produccion
- Validar el sistema con usuarios reales

El proyecto sienta las bases para un sistema de recomendacion gastronomica confiable y transparente para Argentina.

---

## 30. Que Hace Cada Carpeta y Archivo

### `/gastro_ia/`

| Archivo | Descripcion |
|---------|-------------|
| start.bat | Inicia backend y frontend juntos |
| restart.bat | Mata procesos existentes y reinicia todo |
| backend.bat | Inicia solo el backend |
| frontend.bat | Inicia solo el frontend |
| run_backend.py | Script Python para iniciar el backend |

### `/backend/`

| Archivo | Descripcion |
|---------|-------------|
| main.py | Aplicacion FastAPI con todos los endpoints |
| database.py | Configuracion de SQLAlchemy y conexion a PostgreSQL |
| models.py | Modelos ORM de SQLAlchemy |
| schemas.py | Esquemas de respuesta Pydantic |
| gemini_service.py | Integracion con Google Gemini API |
| chat_service.py | Orquestador de conversacion y tools |
| recommendation.py | Motor de recomendacion multi-criterio |
| .env | Variables de entorno (API key) |

### `/frontend/`

| Archivo | Descripcion |
|---------|-------------|
| src/App.tsx | Componente principal con interfaz de chat |
| src/App.css | Estilos del asistente |
| src/Dashboard.tsx | Componente del dashboard analitico |
| src/Dashboard.css | Estilos del dashboard |
| package.json | Dependencias del frontend |

### `/etl/`

| Archivo | Descripcion |
|---------|-------------|
| modules/extract.py | Extraccion de datos de fuentes externas |
| modules/transform.py | Transformacion y normalizacion |
| modules/validate.py | Validacion de datos |
| modules/dedup.py | Eliminacion de duplicados |
| modules/load.py | Carga en PostgreSQL |
| run_etl.py | Orquestador del proceso ETL |

### `/analytics/`

| Archivo | Descripcion |
|---------|-------------|
| csv/ | Archivos CSV para Power BI |
| GastroIA_PowerBI.xlsx | Archivo Excel consolidado |
| GASTRO_IA_Documentacion.pdf | Este documento |
| README.md | Instrucciones para Power BI |
| ANALISIS_EJECUTIVO.md | Informe de analisis |
| analysis_results.json | Resultados del analisis |

### `/database/`

| Archivo | Descripcion |
|---------|-------------|
| schema.sql | Esquema completo de PostgreSQL |

---

*Documento generado el 23 de agosto de 2026*
*Gastro IA - Proyecto Academico*
