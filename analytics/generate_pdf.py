"""
Gastro IA - PDF Documentation Generator
Generates a comprehensive PDF document explaining the entire project.
"""

from fpdf import FPDF
from pathlib import Path
import json

class GastroIADocumentation(FPDF):
    """Custom PDF class for Gastro IA documentation."""
    
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(122, 139, 111)  # olive
        self.cell(0, 8, 'Gastro IA - Documentacion del Proyecto', 0, 1, 'R')
        self.set_draw_color(232, 221, 211)  # beige
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(139, 126, 116)  # muted
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}}', 0, 0, 'C')
    
    def chapter_title(self, num, title):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(61, 50, 41)  # text
        self.cell(0, 12, f'{num}. {title}', 0, 1, 'L')
        self.set_draw_color(196, 129, 90)  # terracotta
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(5)
    
    def section_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(122, 139, 111)  # olive
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)
    
    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(61, 50, 41)
        self.set_x(10)
        self.multi_cell(190, 6, text)
        self.ln(3)
    
    def code_text(self, text):
        self.set_font('Courier', '', 9)
        self.set_fill_color(253, 246, 236)  # cream
        self.set_x(10)
        self.multi_cell(190, 5, text, fill=True)
        self.ln(3)
    
    def bullet_list(self, items):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(61, 50, 41)
        for item in items:
            self.set_x(10)
            self.multi_cell(190, 6, f'  - {item}')
        self.ln(3)


def generate_pdf():
    """Generate the complete documentation PDF."""
    pdf = GastroIADocumentation()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Title page
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(122, 139, 111)
    pdf.cell(0, 15, 'Gastro IA', 0, 1, 'C')
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(139, 126, 116)
    pdf.cell(0, 10, 'Asistente Gastronomico para Argentina', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(61, 50, 41)
    pdf.cell(0, 8, 'Documentacion Completa del Proyecto', 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.cell(0, 8, 'Version 1.0 - Agosto 2026', 0, 1, 'C')
    pdf.cell(0, 8, 'Proyecto Academico', 0, 1, 'C')
    
    # Table of contents
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(61, 50, 41)
    pdf.cell(0, 12, 'Indice', 0, 1, 'L')
    pdf.ln(5)
    
    toc_items = [
        '1. Nombre y objetivo del proyecto',
        '2. Problema que busca resolver',
        '3. Publico objetivo',
        '4. Funcionamiento general',
        '5. Arquitectura del sistema',
        '6. Frontend',
        '7. Backend',
        '8. API de Gemini',
        '9. Funcionamiento del asistente',
        '10. Function Calling / Tools',
        '11. PostgreSQL',
        '12. PostGIS',
        '13. Estructura de la base de datos',
        '14. Tablas y campos principales',
        '15. Proceso ETL',
        '16. Origen y tratamiento de los datos',
        '17. Como el asistente consulta los datos',
        '18. Flujo completo',
        '19. Variables de entorno',
        '20. Configuracion de GEMINI_API_KEY',
        '21. Como iniciar el proyecto localmente',
        '22. Dashboard y analisis',
        '23. Preparacion para Power BI',
        '24. Calidad de datos',
        '25. Limitaciones actuales',
        '26. Seguridad',
        '27. Que deberia hacerse antes de publicar',
        '28. Posibles mejoras futuras',
        '29. Conclusiones',
        '30. Que hace cada carpeta y archivo',
    ]
    
    pdf.set_font('Helvetica', '', 10)
    for item in toc_items:
        pdf.cell(0, 6, item, 0, 1)
    
    # Chapter 1
    pdf.add_page()
    pdf.chapter_title(1, 'Nombre y objetivo del proyecto')
    pdf.body_text(
        'Gastro IA es un asistente gastronomico inteligente para Argentina que utiliza '
        'inteligencia artificial (Google Gemini) combinada con una base de datos georreferenciada '
        'de restaurantes para ayudar a los usuarios a encontrar opciones de comida segun sus '
        'necesidades, preferencias y ubicacion.'
    )
    pdf.body_text(
        'El sistema esta disenado para funcionar como un chat conversacional donde el usuario '
        'puede hacer preguntas en lenguaje natural y recibir recomendaciones personalizadas '
        'de restaurantes, con informacion verificada y trazable.'
    )
    
    # Chapter 2
    pdf.chapter_title(2, 'Problema que busca resolver')
    pdf.body_text(
        'En Argentina no existe una plataforma centralizada que permita encontrar restaurantes '
        'con informacion confiable sobre opciones para personas con restricciones alimentarias '
        '(celiaquismo, vegetarianismo, veganismo). Los usuarios deben consultar multiples '
        'fuentes y no pueden verificar la veracidad de la informacion.'
    )
    pdf.body_text(
        'Gastro IA busca resolver este problema ofreciendo una unica interfaz conversacional '
        'que consulta fuentes verificadas y muestra la trazabilidad de cada dato.'
    )
    
    # Chapter 3
    pdf.chapter_title(3, 'Publico objetivo')
    pdf.bullet_list([
        'Personas con celiaquia que buscan opciones sin TACC',
        'Vegetarianos y veganos que buscan restaurantes adaptados',
        'Personas con intolerancia a la lactosa',
        'Turistas y locales que quieren descubrir restaurantes',
        'Personas con presupuesto limitado',
        'Cualquier persona que busque recomendaciones gastronomicas personalizadas',
    ])
    
    # Chapter 4
    pdf.chapter_title(4, 'Funcionamiento general')
    pdf.body_text(
        'El sistema funciona mediante una arquitectura de tres capas:\n'
        '1. Frontend (React): Interfaz de usuario con chat y dashboard\n'
        '2. Backend (FastAPI): Logica de negocio y conexion con base de datos\n'
        '3. AI (Gemini): Procesamiento de lenguaje natural y function calling'
    )
    pdf.body_text(
        'El usuario escribe un mensaje en el chat. El backend lo envia a Gemini, que decide '
        'que funcion ejecutar (buscar restaurantes, obtener detalles, etc.). El backend '
        'ejecuta la funcion contra PostgreSQL y devuelve el resultado a Gemini, que genera '
        'una respuesta natural para el usuario.'
    )
    
    # Chapter 5
    pdf.chapter_title(5, 'Arquitectura del sistema')
    pdf.code_text(
        '+-----------+     +-----------+     +-----------+\n'
        '|  React    | --> |  FastAPI  | --> |  Gemini   |\n'
        '| Frontend  |     | Backend   |     |    AI     |\n'
        '+-----------+     +-----------+     +-----------+\n'
        '                          |                |\n'
        '                          v                v\n'
        '                    +-----------+    +-----------+\n'
        '                    | PostgreSQL|    |  Tools    |\n'
        '                    | + PostGIS |    |  (APIs)   |\n'
        '                    +-----------+    +-----------+'
    )
    
    # Chapter 6
    pdf.add_page()
    pdf.chapter_title(6, 'Frontend')
    pdf.body_text('Tecnologias utilizadas:')
    pdf.bullet_list([
        'React 18 con TypeScript',
        'Vite como bundler',
        'react-markdown para renderizar respuestas',
        'chart.js y react-chartjs-2 para graficos del dashboard',
        'CSS personalizado con variables de color',
    ])
    pdf.body_text(
        'El frontend esta compuesto por dos vistas principales:\n'
        '- Vista del asistente: Chat conversacional con filtros laterales\n'
        '- Vista del dashboard: Analitica visual con KPIs y graficos'
    )
    
    # Chapter 7
    pdf.chapter_title(7, 'Backend')
    pdf.body_text('Tecnologias utilizadas:')
    pdf.bullet_list([
        'Python 3.14',
        'FastAPI como framework web',
        'SQLAlchemy como ORM',
        'psycopg2 como driver de PostgreSQL',
        'python-dotenv para variables de entorno',
    ])
    pdf.body_text(
        'El backend expone los siguientes endpoints principales:\n'
        '- POST /api/chat: Envia mensajes al asistente\n'
        '- GET /api/restaurants: Busca restaurantes con filtros\n'
        '- GET /api/analytics: Datos para el dashboard\n'
        '- GET /api/stats: Estadisticas generales\n'
        '- GET /api/provinces: Lista de provincias\n'
        '- GET /api/cuisines: Tipos de cocina disponibles'
    )
    
    # Chapter 8
    pdf.chapter_title(8, 'API de Gemini')
    pdf.body_text(
        'Se utiliza Google Gemini (modelo gemini-2.0-flash) como capa de IA. '
        'Gemini procesa el lenguaje natural del usuario y decide que funciones '
        'ejecutar para obtener datos reales de la base de datos.'
    )
    pdf.body_text(
        'La integracion se realiza mediante el paquete google-generativeai. '
        'Se configura con un system prompt que define el comportamiento del asistente '
        'y las reglas de seguridad (no inventar datos, advertir sobre información no verificada, etc.).'
    )
    
    # Chapter 9
    pdf.chapter_title(9, 'Funcionamiento del asistente')
    pdf.body_text(
        'El asistente conversacional funciona de la siguiente manera:\n'
        '1. El usuario escribe un mensaje\n'
        '2. El backend envia el mensaje a Gemini junto con el historial de la sesion\n'
        '3. Gemini analiza la intencion y decide si necesita ejecutar alguna funcion\n'
        '4. Si necesita datos, Gemini solicita ejecutar un tool (funcion)\n'
        '5. El backend ejecuta la funcion contra PostgreSQL\n'
        '6. El resultado se devuelve a Gemini\n'
        '7. Gemini genera una respuesta natural basada en los datos reales\n'
        '8. La respuesta se muestra al usuario en el frontend'
    )
    
    # Chapter 10
    pdf.add_page()
    pdf.chapter_title(10, 'Function Calling / Tools')
    pdf.body_text('Tools disponibles para Gemini:')
    pdf.bullet_list([
        'buscar_restaurantes: Busca restaurantes por provincia, ciudad, tipo de cocina, presupuesto, necesidades dietarias',
        'obtener_detalle_restaurante: Obtiene informacion detallada de un restaurante especifico',
        'buscar_por_cercania: Encuentra restaurantes cercanos a unas coordenadas usando PostGIS',
        'obtener_fuentes: Devuelve informacion de trazabilidad de un restaurante',
    ])
    pdf.body_text(
        'Cada tool esta definido con su esquema de parametros en formato JSON Schema. '
        'Gemini decide automaticamente cual tool usar segun la pregunta del usuario.'
    )
    
    # Chapter 11
    pdf.chapter_title(11, 'PostgreSQL')
    pdf.body_text(
        'Se utiliza PostgreSQL 17 como motor de base de datos. '
        'La base de datos se llama "gastro_ia" y contiene las siguientes tablas principales:'
    )
    pdf.bullet_list([
        'restaurants: Tabla principal con 6,187 restaurantes',
        'restaurant_features: Caracteristicas dietarias por restaurante',
        'sources: Fuentes de datos utilizadas',
        'query_logs: Registro de consultas (pendiente)',
    ])
    
    # Chapter 12
    pdf.chapter_title(12, 'PostGIS')
    pdf.body_text(
        'PostGIS 3.6.2 esta instalado como extension de PostgreSQL. '
        'Permite realizar consultas geoespaciales como:'
    )
    pdf.bullet_list([
        'Encontrar restaurantes cercanos a unas coordenadas',
        'Calcular distancias entre puntos',
        'Filtrar por radio de busqueda',
    ])
    pdf.body_text(
        'La columna "geom" de tipo GEOMETRY esta indexada con un indice GiST '
        'para consultas espaciales eficientes.'
    )
    
    # Chapter 13
    pdf.add_page()
    pdf.chapter_title(13, 'Estructura de la base de datos')
    pdf.code_text(
        'gastro_ia (PostgreSQL 17 + PostGIS 3.6.2)\n'
        '|\n'
        '+-- restaurants (6,187 registros)\n'
        '|   +-- restaurant_id (PK)\n'
        '|   +-- name, province, city, neighborhood, address\n'
        '|   +-- latitude, longitude, geom (PostGIS)\n'
        '|   +-- cuisine_type[], category, phone, email\n'
        '|   +-- website, opening_hours, price_range, rating\n'
        '|   +-- source_id (FK), confidence_level\n'
        '|\n'
        '+-- restaurant_features (6,187 registros)\n'
        '|   +-- restaurant_id (FK)\n'
        '|   +-- has_gluten_free_options, has_vegetarian_options\n'
        '|   +-- has_vegan_options, has_lactose_free_options\n'
        '|\n'
        '+-- sources (3 registros)\n'
        '    +-- source_id (PK)\n'
        '    +-- name, source_type, url, license, reliability'
    )
    
    # Chapter 14
    pdf.chapter_title(14, 'Tablas y campos principales')
    pdf.body_text('Tabla restaurants:')
    pdf.bullet_list([
        'restaurant_id: Identificador unico (entero)',
        'name: Nombre del restaurante (texto)',
        'province: Provincia argentina (texto)',
        'city: Ciudad o localidad (texto)',
        'neighborhood: Barrio (texto, opcional)',
        'address: Direccion completa (texto)',
        'latitude/longitude: Coordenadas WGS84 (decimal)',
        'geom: Geometria PostGIS (POINT)',
        'cuisine_type: Tipos de cocina (array de texto)',
        'category: Categoria gastronomica (texto)',
        'phone: Telefono de contacto (texto)',
        'price_range: Rango de precios 1-4 (entero)',
        'rating: Calificacion 0-5 (decimal)',
        'source_id: Fuente de datos (FK)',
        'confidence_level: Nivel de confianza (texto)',
    ])
    
    # Chapter 15
    pdf.add_page()
    pdf.chapter_title(15, 'Proceso ETL')
    pdf.body_text(
        'El proceso ETL (Extract, Transform, Load) se ejecuta desde la carpeta /etl '
        'y consta de las siguientes fases:'
    )
    pdf.bullet_list([
        'Extract: Descarga datos de BA Data, OpenStreetMap (Overpass API) y CSV de Mendoza',
        'Transform: Normaliza tipos de cocina, limpia telefonos, estandariza direcciones',
        'Validate: Verifica coordenadas, nombres, provincias',
        'Dedup: Elimina duplicados por nombre dentro de cada fuente',
        'Load: Carga los datos en PostgreSQL con source_id y timestamp',
    ])
    
    # Chapter 16
    pdf.chapter_title(16, 'Origen y tratamiento de los datos')
    pdf.body_text('Fuentes de datos utilizadas:')
    pdf.bullet_list([
        'BA Data (Buenos Aires): Oferta gastronomica oficial de CABA - 2,549 registros',
        'OpenStreetMap Overpass API: Datos de la comunidad - 2,729 registros',
        'Mendoza Official: Datos oficiales de la provincia - 909 registros',
    ])
    pdf.body_text(
        'Los datos pasan por un proceso de validacion y deduplicacion antes de ser cargados. '
        'Se asigna un nivel de confianza (official, public_source, community) segun la fuente.'
    )
    
    # Chapter 17
    pdf.chapter_title(17, 'Como el asistente consulta los datos')
    pdf.body_text(
        'Cuando el usuario pregunta "Que restaurantes sin TACC hay en Palermo?", '
        'el flujo es:\n'
        '1. Gemini recibe el mensaje\n'
        '2. Decide usar el tool "buscar_restaurantes"\n'
        '3. Pasa los parametros: {ciudad: "Palermo", requiere_sin_tacc: true}\n'
        '4. El backend ejecuta una consulta SQL con filtros\n'
        '5. Devuelve los restaurantes que coinciden\n'
        '6. Gemini genera una respuesta natural con los datos'
    )
    
    # Chapter 18
    pdf.add_page()
    pdf.chapter_title(18, 'Flujo completo')
    pdf.code_text(
        'USUARIO\n'
        '  |\n'
        '  v\n'
        '[React Frontend]\n'
        '  | POST /api/chat\n'
        '  v\n'
        '[FastAPI Backend]\n'
        '  | send_message()\n'
        '  v\n'
        '[Gemini API]\n'
        '  | function_call: buscar_restaurantes()\n'
        '  v\n'
        '[Chat Service]\n'
        '  | SELECT * FROM restaurants\n'
        '  | WHERE province = \'Buenos Aires\'\n'
        '  | AND has_gluten_free_options = TRUE\n'
        '  v\n'
        '[PostgreSQL + PostGIS]\n'
        '  | Resultado: [restaurante1, restaurante2, ...]\n'
        '  v\n'
        '[Gemini API]\n'
        '  | Genera respuesta natural\n'
        '  v\n'
        '[FastAPI Backend]\n'
        '  | Devuelve JSON\n'
        '  v\n'
        '[React Frontend]\n'
        '  | Muestra respuesta en chat\n'
        '  v\n'
        'USUARIO'
    )
    
    # Chapter 19
    pdf.chapter_title(19, 'Variables de entorno')
    pdf.body_text('Las variables de entorno se configuran en el archivo backend/.env:')
    pdf.code_text(
        'GEMINI_API_KEY=tu_api_key_aqui\n'
        'GEMINI_MODEL=gemini-2.0-flash'
    )
    pdf.body_text(
        'El archivo .env NO debe subirse a repositorios publicos. '
        'Debe incluirse en .gitignore.'
    )
    
    # Chapter 20
    pdf.chapter_title(20, 'Configuracion de GEMINI_API_KEY')
    pdf.body_text(
        'Para obtener una API key de Gemini:\n'
        '1. Ir a https://aistudio.google.com/apikey\n'
        '2. Crear una API key\n'
        '3. Copiarla en el archivo backend/.env\n'
        '4. Reiniciar el backend'
    )
    
    # Chapter 21
    pdf.add_page()
    pdf.chapter_title(21, 'Como iniciar el proyecto localmente')
    pdf.section_title('Requisitos previos')
    pdf.bullet_list([
        'Python 3.14 o superior',
        'Node.js 18 o superior',
        'PostgreSQL 17 con PostGIS 3.6.2',
        'Una API key de Google Gemini',
    ])
    pdf.section_title('Pasos de instalacion')
    pdf.code_text(
        '# 1. Clonar el repositorio\n'
        'cd "C:\\Users\\Usuario\\Documents\\Default Project"\n'
        '\n'
        '# 2. Instalar dependencias del frontend\n'
        'cd gastro_ia\\frontend\n'
        'npm install\n'
        '\n'
        '# 3. Configurar API key\n'
        'echo GEMINI_API_KEY=tu_key > backend\\.env\n'
        '\n'
        '# 4. Iniciar el proyecto\n'
        'cd ..\n'
        '.\\restart.bat'
    )
    pdf.section_title('URLs de acceso')
    pdf.bullet_list([
        'Frontend: http://localhost:5173',
        'Backend API: http://127.0.0.1:8001',
        'Documentacion API: http://127.0.0.1:8001/docs',
    ])
    
    # Chapter 22
    pdf.chapter_title(22, 'Dashboard y analisis')
    pdf.body_text(
        'El dashboard analitico esta disponible en la interfaz del frontend, '
        'accesible desde el boton "Dashboard" en el header. Incluye:'
    )
    pdf.bullet_list([
        'KPIs principales: total de restaurantes, provincias, ciudades, tipos de cocina',
        'Grafico de barras: Restaurantes por provincia',
        'Grafico de dona: Distribucion por tipo de cocina',
        'Grafico de barras horizontales: Distribucion por categoria',
        'Grafico circular: Distribucion por fuente de datos',
        'Indicadores de calidad: completitud, coordenadas, telefonos',
        'Pestanas: Resumen, Geografia, Calidad',
    ])
    
    # Chapter 23
    pdf.chapter_title(23, 'Preparacion para Power BI')
    pdf.body_text(
        'Se han generado archivos CSV y XLSX en la carpeta /analytics/csv/ '
        'listos para importar a Power BI Desktop:'
    )
    pdf.bullet_list([
        'restaurants.csv: Todos los restaurantes (6,187 registros)',
        'restaurant_features.csv: Caracteristicas dietarias',
        'sources.csv: Fuentes de datos',
        'by_province.csv: Resumen por provincia',
        'by_city.csv: Resumen por ciudad (top 50)',
        'by_cuisine.csv: Resumen por tipo de cocina',
        'by_category.csv: Resumen por categoria',
        'GastroIA_PowerBI.xlsx: Archivo Excel con todas las hojas',
    ])
    pdf.body_text(
        'Ver analytics/README.md para instrucciones detalladas de importacion '
        'y diccionario de datos.'
    )
    
    # Chapter 24
    pdf.add_page()
    pdf.chapter_title(24, 'Calidad de datos')
    pdf.section_title('Fortalezas')
    pdf.bullet_list([
        '100% de registros con nombre, provincia, ciudad y direccion',
        '100% de registros con telefono',
        '85% de registros con coordenadas geograficas',
        '55% de registros con nivel de confianza oficial',
    ])
    pdf.section_title('Debilidades')
    pdf.bullet_list([
        '0% de registros con rating o calificacion',
        '0% de registros con horarios de apertura',
        '0% de registros con email o website',
        '0.1% de registros con informacion sin TACC',
        '1.1% de registros con opciones vegetarianas',
        '0.7% de registros con opciones veganas',
    ])
    
    # Chapter 25
    pdf.chapter_title(25, 'Limitaciones actuales')
    pdf.bullet_list([
        'Solo 4 de 24 provincias argentinas tienen datos',
        'No hay ratings ni resenas de usuarios',
        'No hay informacion de menus ni precios especificos',
        'No se puede verificar disponibilidad sin horarios',
        'La informacion para celiacos es insuficiente (7 registros)',
        'No hay fotos de restaurantes',
        'No hay sistema de reservas',
        'No hay informacion de delivery',
    ])
    
    # Chapter 26
    pdf.chapter_title(26, 'Seguridad')
    pdf.bullet_list([
        'PostgreSQL configurado en modo trust solo para localhost',
        'La API key de Gemini se almacena en .env (no en codigo)',
        'El backend no esta expuesto a Internet',
        'No hay autenticacion de usuarios (pendiente)',
        'No hay rate limiting (pendiente)',
        'No hay HTTPS (pendiente para produccion)',
    ])
    
    # Chapter 27
    pdf.add_page()
    pdf.chapter_title(27, 'Que deberia hacerse antes de publicar')
    pdf.bullet_list([
        'Configurar autenticacion de usuarios',
        'Agregar rate limiting al API',
        'Configurar HTTPS',
        'Cambiar PostgreSQL de trust a password/md5',
        'Agregar validacion de entrada (sanitization)',
        'Implementar logging y monitoreo',
        'Configurar CORS para dominio especifico',
        'Agregar tests automatizados',
        'Realizar prueba de penetracion',
        'Configurar backups automaticos de la base de datos',
    ])
    
    # Chapter 28
    pdf.chapter_title(28, 'Posibles mejoras futuras')
    pdf.bullet_list([
        'Expandir a todas las provincias argentinas',
        'Integrar fuentes con ratings (Google Maps, Yelp)',
        'Agregar informacion de menus y precios en tiempo real',
        'Implementar sistema de resenas de usuarios',
        'Agregar fotos de restaurantes',
        'Mejorar informacion de alergenos',
        'Implementar sistema de reservas',
        'Agregar informacion de delivery',
        'Desarrollar app mobile nativa',
        'Implementar notificaciones push',
        'Agregar comparator de restaurantes',
        'Implementar favoritos y historial',
    ])
    
    # Chapter 29
    pdf.chapter_title(29, 'Conclusiones')
    pdf.body_text(
        'Gastro IA demuestra la viabilidad de combinar IA conversacional con bases de datos '
        'georreferenciadas para crear asistentes inteligentes especializados. '
        'El prototipo actual permite buscar restaurantes, filtrar por necesidades alimentarias '
        'y obtener informacion trazable.'
    )
    pdf.body_text(
        'Los principales desafios pendientes son:\n'
        '- Expandir la cobertura geografica a todo el pais\n'
        '- Enriquecer la informacion con ratings, menus y horarios\n'
        '- Implementar seguridad para produccion\n'
        '- Validar el sistema con usuarios reales'
    )
    pdf.body_text(
        'El proyecto sienta las bases para un sistema de recomendacion gastronomica '
        'confiable y transparente para Argentina.'
    )
    
    # Chapter 30
    pdf.add_page()
    pdf.chapter_title(30, 'Que hace cada carpeta y archivo')
    
    pdf.section_title('/gastro_ia/')
    pdf.bullet_list([
        'start.bat: Inicia backend y frontend juntos',
        'restart.bat: Mata procesos existentes y reinicia todo',
        'backend.bat: Inicia solo el backend',
        'frontend.bat: Inicia solo el frontend',
        'run_backend.py: Script Python para iniciar el backend',
    ])
    
    pdf.section_title('/backend/')
    pdf.bullet_list([
        'main.py: Aplicacion FastAPI con todos los endpoints',
        'database.py: Configuracion de SQLAlchemy y conexion a PostgreSQL',
        'models.py: Modelos ORM de SQLAlchemy',
        'schemas.py: Esquemas de respuesta Pydantic',
        'gemini_service.py: Integracion con Google Gemini API',
        'chat_service.py: Orquestador de conversacion y tools',
        'recommendation.py: Motor de recomendacion multi-criterio',
        'run.py: Punto de entrada para el servidor',
        '.env: Variables de entorno (API key)',
    ])
    
    pdf.section_title('/frontend/')
    pdf.bullet_list([
        'src/App.tsx: Componente principal con interfaz de chat',
        'src/App.css: Estilos del asistente',
        'src/Dashboard.tsx: Componente del dashboard analitico',
        'src/Dashboard.css: Estilos del dashboard',
        'package.json: Dependencias del frontend',
    ])
    
    pdf.section_title('/etl/')
    pdf.bullet_list([
        'modules/extract.py: Extraccion de datos de fuentes externas',
        'modules/transform.py: Transformacion y normalizacion',
        'modules/validate.py: Validacion de datos',
        'modules/dedup.py: Eliminacion de duplicados',
        'modules/load.py: Carga en PostgreSQL',
        'run_etl.py: Orquestador del proceso ETL',
    ])
    
    pdf.section_title('/analytics/')
    pdf.bullet_list([
        'csv/: Archivos CSV para Power BI',
        'GastroIA_PowerBI.xlsx: Archivo Excel consolidado',
        'README.md: Instrucciones para Power BI',
        'ANALISIS_EJECUTIVO.md: Informe de analisis',
        'analysis_results.json: Resultados del analisis',
    ])
    
    pdf.section_title('/database/')
    pdf.bullet_list([
        'schema.sql: Esquema completo de PostgreSQL',
    ])
    
    # Save PDF
    analytics_dir = Path(__file__).parent / "analytics"
    pdf.output(str(analytics_dir / "GASTRO_IA_Documentacion.pdf"))
    print("PDF generated: analytics/GASTRO_IA_Documentacion.pdf")


if __name__ == "__main__":
    generate_pdf()
