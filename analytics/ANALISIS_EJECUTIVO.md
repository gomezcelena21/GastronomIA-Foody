# Gastro IA - Análisis Ejecutivo

## Resumen Ejecutivo

El presente informe analiza la base de datos del proyecto Gastro IA, un asistente gastronómico para Argentina. El análisis se basa exclusivamente en los datos reales almacenados en PostgreSQL.

---

## 1. Cantidad Total de Restaurantes

**Total: 6,187 restaurantes activos**

Esta cantidad representa una base de datos de tamaño moderado, suficiente para un MVP (Producto Mínimo Viable) pero limitada para un sistema de recomendación a nivel nacional.

---

## 2. Distribución por Provincia

| Provincia | Cantidad | Porcentaje |
|-----------|----------|------------|
| Buenos Aires | 4,690 | 75.8% |
| Mendoza | 1,188 | 19.2% |
| Santa Fe | 179 | 2.9% |
| Córdoba | 130 | 2.1% |

**Observaciones:**
- Buenos Aires domina con el 75.8% de los registros
- Solo 4 provincias están representadas de las 24 existentes en Argentina
- Existe un desbalance significativo entre regiones

---

## 3. Distribución por Ciudad (Top 10)

| Ciudad | Cantidad |
|--------|----------|
| Ciudad Autónoma de Buenos Aires | 2,549 |
| CABA | 1,851 |
| Ciudad (Mendoza) | 550 |
| Provincia Buenos Aires | 290 |
| Mendoza Capital | 279 |

**Observaciones:**
- La gran mayoría de datos corresponden al área metropolitana de Buenos Aires
- Mendoza tiene buena cobertura en la capital provincial
- Faltan datos de ciudades intermedias

---

## 4. Distribución por Tipo de Cocina (Top 10)

| Tipo de Cocina | Cantidad |
|----------------|----------|
| Comida rápida | 674 |
| Italiana | 452 |
| Internacional | 415 |
| Tradicional | 273 |
| Parrilla | 268 |

**Observaciones:**
- Hay 145 tipos de cocina diferentes registrados
- Predomina la comida rápida e italiana
- La parrilla (típica argentina) tiene representación menor de lo esperado

---

## 5. Distribución por Categoría

| Categoría | Cantidad | Porcentaje |
|-----------|----------|------------|
| Restaurant | 5,270 | 85.2% |
| Café | 431 | 7.0% |
| Bar | 277 | 4.5% |
| Confitería | 70 | 1.1% |
| Heladería | 52 | 0.8% |

**Observaciones:**
- El 85% son restaurantes formales
- Los cafés y bares tienen representación secundaria
- Faltan datos de pizzerías, rotiserías y otros formatos

---

## 6. Fuentes de Datos

| Fuente | Cantidad | Tipo |
|--------|----------|------|
| OpenStreetMap | 2,729 | Comunidad |
| BA Data | 2,549 | Pública |
| Mendoza Oficial | 909 | Oficial |

**Observaciones:**
- Las 3 fuentes tienen buena representación
- OpenStreetMap es la fuente más extensa
- Mendoza Oficial tiene alta confiabilidad

---

## 7. Nivel de Confianza

| Nivel | Cantidad | Porcentaje |
|-------|----------|------------|
| Oficial | 3,458 | 55.9% |
| Fuente pública | 2,729 | 44.1% |

**Observaciones:**
- Más del 55% de los datos provienen de fuentes oficiales
- El 44% restante es de fuentes públicas verificables
- No hay datos de nivel "community" o "inferred"

---

## 8. Disponibilidad de Información

| Campo | Con Datos | Porcentaje |
|-------|-----------|------------|
| Nombre | 6,187 | 100% |
| Provincia | 6,187 | 100% |
| Ciudad | 6,187 | 100% |
| Dirección | 6,187 | 100% |
| Teléfono | 6,187 | 100% |
| Coordenadas | 5,278 | 85.3% |
| Rating | 0 | 0% |
| Email | 0 | 0% |
| Website | 0 | 0% |
| Horarios | 0 | 0% |

**Problemas Identificados:**
1. **Sin ratings**: No hay calificaciones de usuarios
2. **Sin email**: No hay información de contacto por email
3. **Sin websites**: No hay enlaces a sitios web
4. **Sin horarios**: No hay información de horarios de apertura
5. **15% sin coordenadas**: Algunos registros no tienen ubicación geográfica

---

## 9. Características Dietarias

| Característica | Cantidad | Porcentaje |
|----------------|----------|------------|
| Sin TACC | 7 | 0.1% |
| Vegetariano | 70 | 1.1% |
| Vegano | 43 | 0.7% |
| Sin lactosa | 0 | 0% |

**Problemas Identificados:**
- La información dietaria es extremadamente escasa
- Solo 0.1% tiene información sobre opciones sin TACC
- Esto limita significativamente las recomendaciones para celíacos

---

## 10. Problemas de Calidad de Datos

### 10.1 Valores Nulos
| Campo | Nulos | Porcentaje |
|-------|-------|------------|
| Nombre | 0 | 0% |
| Provincia | 0 | 0% |
| Ciudad | 0 | 0% |
| Dirección | 0 | 0% |
| Teléfono | 0 | 0% |
| Coordenadas | 909 | 14.7% |

### 10.2 Duplicados
Se identificaron duplicados potenciales por nombre dentro de la misma provincia. Ejemplo:
- "Pizza Vegana San Telmo" aparece múltiples veces en Buenos Aires

### 10.3 Inconsistencias
- Nombres de ciudades inconsistentes: "Ciudad Autónoma de Buenos Aires" vs "CABA"
- Formatos de teléfono variables

---

## 11. Provincias con Mayor y Menor Representación

| Mayor Representación | Menor Representación |
|---------------------|---------------------|
| Buenos Aires (4,690) | Córdoba (130) |
| Mendoza (1,188) | Santa Fe (179) |

---

## 12. Conclusiones

### Lo que los datos muestran:
1. El proyecto tiene una base sólida de 6,187 restaurantes
2. Buenos Aires y Mendoza están bien representadas
3. Las fuentes de datos son confiables (55% oficiales)
4. La información básica (nombre, dirección, teléfono) está completa

### Lo que los datos NO muestran:
1. No hay ratings ni reseñas de usuarios
2. No hay información de menús ni precios específicos
3. No hay horarios de apertura
4. No hay información de contacto digital (email, web)
5. La información dietaria es prácticamente inexistente

### Limitaciones actuales:
1. Solo 4 de 24 provincias tienen datos
2. No se pueden hacer recomendaciones personalizadas sin ratings
3. No se puede verificar disponibilidad sin horarios
4. La información para celíacos es insuficiente

### Datos que sería conveniente incorporar:
1. Ratings y reseñas de usuarios
2. Menús y precios específicos
3. Horarios de apertura
4. Información de contacto completa
5. Fotos de restaurantes
6. Datos de alergenos más detallados
7. Información de delivery
8. Reservas online

---

## 13. Recomendaciones

### A Corto Plazo:
1. Completar coordenadas faltantes (909 registros)
2. Estandarizar nombres de ciudades
3. Eliminar duplicados identificados

### A Mediano Plazo:
1. Integrar fuentes de datos con ratings (Google Maps, Yelp)
2. Agregar información de horarios
3. Enriquecer datos dietarios

### A Largo Plazo:
1. Expandir a todas las provincias argentinas
2. Incorporar sistema de reseñas de usuarios
3. Agregar información de menús en tiempo real

---

*Informe generado el 23 de agosto de 2026*
*Basado exclusivamente en datos reales de PostgreSQL*
