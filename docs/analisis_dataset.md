# Base unificada de lugares (16/11/2026)

**Archivo de origen:** `Base_Unificada_Restricciones_Argentina.xlsx` (95.815 lugares de todo el país). **Lo que carga el sistema hoy:** `data/dataset_unificado_ARGENTINA.csv`, con **71.343 lugares de todo el país** (8,7 veces los 8.181 originales). La conversión se hace con `scripts/convertir_base_unificada.py --alcance argentina` y la carga con `scripts/cargar_base_unificada.py --csv data\dataset_unificado_ARGENTINA.csv`. Los 24.472 lugares restantes del Excel se descartan por confianza baja del dato (se pueden incluir con `--incluir-baja`).

| Fuente | Lugares cargados | Licencia |
|---|---|---|
| Overture Maps Foundation (release 2026-10-21.0) | 62.880 | CDLA-Permissive-2.0 (atribución obligatoria) |
| OpenStreetMap contributors | 5.431 | ODbL |
| BA Data (Gobierno de la Ciudad de Buenos Aires) | 2.721 | CC-BY-2.5-AR |
| Guías kosher y de celíacos | 9 | listados públicos |
| Google Places | 302 | términos de Google Maps Platform (ver aviso) |

## Decisiones de calidad

1. **Alcance nacional.** La base, la validación (HU-03), el prompt de Gemini y los textos cubren toda la Argentina. Las consultas por lugares de otros países se rechazan con un mensaje explícito y no consultan la base. El buscador filtra por provincia, ciudad/localidad y partido (GBA).
2. **Se excluyen 24.472 lugares de confianza baja**, salvo los que traen dato de restricción. Se pueden incluir con `--incluir-baja` (la base quedaría cerca de los 95.815 del Excel).
3. **«Sin datos» no es «no».** Casi todos los lugares (más del 99 %) no tienen dato de restricción alimentaria: en la base quedan vacíos (NULL) y el sistema los muestra como «no confirmado». Solo 432 lugares tienen dato de sin TACC, ~203 de vegano y ~420 de vegetariano, y **ninguno está verificado con el local**. Lo «inferido» (por el nombre del lugar) queda marcado como inferido.
4. **Tipos de cocina traducidos al vocabulario del sistema.** La base original usaba `pizza` mientras el buscador pedía `pizzeria`; ahora cada lugar trae ambos (y los equivalentes de hamburguesa, café, parrilla, sushi, etc.).
5. **Coordenadas inválidas o imprecisas se descartan** (el lugar queda sin ubicación en el mapa pero se puede encontrar por zona).
6. **Zonas para el modo sin IA:** 1.587 barrios, localidades, ciudades y partidos de todo el país salen de la base (`backend/zonas_dataset.py`, generado); el intérprete reconoce 1.598 al sumar la lista básica. Los partidos de GBA sin locales (por ejemplo Presidente Perón) se avisan en lugar de mostrar otra zona.

## Aviso sobre Google Places

La hoja «Notas y criterios» del Excel recuerda que los términos de la Places API limitan guardar datos de Google fuera de su mapa: solo el `place_id` puede guardarse sin límite de tiempo. Por eso **de los 92 lugares que vienen de Google no se guardan calificación, reseñas, horarios ni teléfono**. Aun así, el nombre, la dirección, las coordenadas y la clasificación de restricciones de esos 92 lugares sí se cargan. Si querés **cero riesgo**, convertí con `--sin-google` (se pierden esos 92 lugares). Es una decisión del equipo; consultala con el docente si vas a publicar el sistema. Esto no es asesoramiento legal.

## Atribución obligatoria

La portada, los Términos y este documento incluyen: © OpenStreetMap contributors (ODbL), BA Data (CC-BY-2.5-AR) y Overture Maps Foundation (CDLA-Permissive-2.0).

## Cómo regenerar

```
pip install pandas openpyxl
python scripts\convertir_base_unificada.py Base_Unificada_Restricciones_Argentina.xlsx --alcance argentina
set "DATABASE_URL=..."
python scripts\cargar_base_unificada.py --csv data\dataset_unificado_ARGENTINA.csv   (agregar --forzar para recargar conservando los comercios)
```

> `--alcance caba-gba` sigue disponible y genera el recorte de 27.064 lugares en `data/dataset_unificado_CABA_GBA.csv`.

---

# Dataset original (09/09/2026, 8.181 registros)

# GastronomIA — Informe Inicial de Análisis del Dataset 

**Fecha:** 2026-09-09  
**Dataset:** `data/dataset_gastronomia_CABA_GBA.csv` (copia fiel del adjunto, 1.825.691 bytes, UTF-8-SIG)  
**Registros:** 8.181 | **Columnas:** 14 | **Fuentes:** OpenStreetMap (5.441) + BA Data GCBA (2.740)

---

## 1. Esquema real verificado

| # | Columna | Ejemplo | Tipo inferido | Vacios "" | Valores distintos | Observacion |
|---|---------|---------|---------------|-----------|-------------------|-------------|
|1|`id_origen`|247463215|TEXT PK candidato, numerico sin duplicados|0|8181|PK valido. 0 duplicados. Usar como PK.|
|2|`nombre`|Restaurant Museo Evita|TEXT NOT NULL|0|7551 nombres unicos, 630 repetidos (ej Las Violetas, Los Inmortales)|Normalizar busqueda case-insensitive. No usar como PK.|
|3|`tipo_establecimiento`|restaurant / RESTAURANTE / cafe / fast_food / bar / pub ...|TEXT nullable|114 vacios|17 valores distintos: restaurant 2635, RESTAURANTE 1933, cafe 1232, fast_food 970, bar 443, CAFE 324, BAR 239, pub 133, PUB 53, CONFITERIA 50, VINERIA 21, internet_cafe 21, public_bookcase 5, etc.|**Inconsistencia critica:** case duplicado y espanol/ingles. Requiere normalizacion.|
|4|`cocina`|pizza / italian / sushi / No especificado|TEXT nullable|344 vacios + 3749 'No especificado' = 50% sin cocina|201 tokens split por ;|Valores multi-valor con `;`. Ej `peruvian;chinese`, `burger;pizza;empanada`. Mayusculas/minusculas mezcladas. Normalizar lowercase.|
|5|`direccion`|Juan Maria Gutierrez 3926 / Cerviño / vacio|TEXT nullable|2211 vacios (27%)|5970 con dato|BA Data suele vacia cuando barrio No especificado. No fiable para geocoding.|
|6|`barrio_localidad`|Palermo / Ciudad Autonoma de Buenos Aires / No especificado|TEXT NOT NULL|0 vacios pero 2889 'No especificado' (35%)|~80 barrios distintos|Palermo 879, San Nicolas 438, Recoleta 316. 1527 como 'Ciudad Autonoma de Buenos Aires' (generico, poco util para filtro fino).|
|7|`telefono`|+54 11 4342 4328 / vacio|TEXT nullable|5219 vacios (63.8%)|2962 con dato|Formato heterogeneo, algunos multiples con `;`.|
|8|`website`|https://... / vacio|TEXT nullable|7181 vacios (87.8%)|1000 con dato|URLs a validar.|
|9|`es_vegano`|Sin datos (Confirmar con el local) / Apto / Con opciones|TEXT NOT NULL categórico|0 vacios formales|Sin datos 8118 (99.23%), Apto 58, Apto (Inferido) 3, No disponible 2|**Campo casi vacio.** Solo 0.7% confirmado vegano.|
|10|`es_vegetariano`|Sin datos...|TEXT|0|Sin datos 8077 (98.7%), Apto 92, Inferido 8, No disponible 4|Solo 1.2% confirmado.|
|11|`es_sin_tacc`|Sin datos...|TEXT|0|Sin datos 8172 (99.89%), Apto 8, Inferido 1|**Solo 9 registros confirmados sin TACC (0.11%).** Riesgo celiaquia alto si se infiere.|
|12|`latitud`|-345805799 / -350|TEXT numerico entero|0|Debe dividirse /1e7 => -34.5805799. 2740 con valor -350 (placeholder BA Data)||
|13|`longitud`|-584149412 / -580|TEXT|0|/1e7 => -58.4149412. 2740 con -580 placeholder||
|14|`fuente_dato`|OpenStreetMap / BA Data (Gobierno CABA)|TEXT|0|2 valores|OSM trae coords reales. BA Data trae coords placeholder -350/-580 inutilizables.|

### Hallazgos de encoding
- Archivo es UTF-8-SIG. Al leer como cp1252 aparecen `Mar�a`. Leyendo UTF-8 correcto se ve bien (`María`, `Gutiérrez`). Mantener UTF-8 en toda la pipeline.
- Algunos nombres con emoji `ð™¿ð™¸ðš‰ðš‰ð™´ðšÍA` requieren utf8mb4 si se migra a DB.

---

## 2. Valores faltantes e inconsistencias

1. **Coordenadas rotas:** 33.5% del dataset (2.740 BA Data) tiene lat=-350, lon=-580. No sirven para calculo de distancia. Solo 5.441 (66.5%) tienen coords reales divisibles por 1e7.
2. **tipo_establecimiento duplicado por case:** `restaurant` vs `RESTAURANTE` son mismo concepto. Solucion: normalizar a lowercase y mapear a 6 categorias: restaurant, cafe, bar, pub, fast_food, otros.
3. **cocina 50% vacia/No especificado.** Solo 4.088 registros tienen cocina util. De esos, 194 tokens distintos normalizados. Top utiles: pizza 385, internacional 440, minutas 717, tradicional 293.
4. **barrio 35% No especificado + 18% CABA generico = 53% sin barrio filtrable fino.** Solo Palermo, Recoleta, Belgrano etc tienen volumen para filtro.
5. **Direccion 27% vacia**, correlacionada con barrio No especificado (722 de 2889 sin barrio aun tienen direccion, resto sin direccion ni barrio => imposible ubicar).
6. **Dietetico casi nulo:** vegano 0.7%, vegetariano 1.2%, sin_tacc 0.11%. NO se puede asumir `Sin datos = No`. Debe tratarse como `null / No confirmado`.
7. **Telefono y website muy dispersos:** solo 36% y 12% con dato, no sirven como filtro primario, solo display.
8. **Duplicados de nombre:** 630 nombres repetidos (ej 3 sucursales de Los Inmortales con distinto id_origen y direccion). No deduplicar, son locales distintos.

---

## 3. Campos utilizables

### Para FILTROS (implementables reales)
- **cocina** (con normalizacion y busqueda LIKE): si. Permitir multi-select y busqueda `ilike '%sushi%'`.
- **tipo_establecimiento** (normalizado): si. Filtro por 5 tipos principales.
- **barrio_localidad** (normalizado): si, pero advertir que 35% no filtra. Incluir opcion "Sin barrio especificado".
- **es_vegano / es_vegetariano / es_sin_tacc**: si, como boolean tri-estado (true solo si `Apto*`, false si `No disponible`, null si `Sin datos`). Filtro `vegano=true` debe devolver solo 61; no 8000.
- **texto libre nombre**: si, busqueda por substring.
- **direccion**: busqueda substring, no filtro exacto.
- **coordenadas + distancia**: solo para 5441 con coords validas. Implementar Haversine y filtrar si usuario da barrio o lat/lon. Si pide distancia y el registro tiene placeholder, excluirlo o indicar "sin coords".
- **fuente_dato**: no para usuario final, pero util para debug y decidir confianza de coords.

### NO utilizables como filtro fiable
- Precio, horario, rating, delivery, accesibilidad: **no existen**. Responder "No tengo ese dato.".
- Telefono/website: no filtrar, solo mostrar.

### Para RECOMENDACION
Sin scores. La recomendacion debe basarse en **matching score**: cantidad de filtros coincidentes. Ej sushi+Palermo+vegetariano => score 3 es top. Desempatar por completitud de datos (tiene website/tel/direccion) o aleatorio estable. No inventar ranking.

### Para COMPARACION (tabla atributo x local)
Atributos comparables reales: nombre, tipo, cocina, barrio, direccion, telefono, website (presente/ausente), vegano, vegetariano, sin_tacc, coords (si validas), fuente. No agregar columnas ficticias.

---

## 4. Problemas detectados (riesgos)

- **Riesgo celiaquia:** solo 9 sin_tacc confirmados. Si Gemini infiere apto, peligro sanitario. Requiere validacion anti-alucinacion y disclaimer.
- **Baja cobertura dietetica:** usuario que pida vegano en Palermo recibe solo 19 resultados. Sistema debe explicar que son pocos confirmados y sugerir verificar con local.
- **Coords placeholder:** si el backend no filtra -350/-580, calculos de distancia daran resultados absurdos (-35 vs -350). Filtrar.
- **Cocina con 194 variantes:** muchas sinonimas (`american` vs `AMERICANA` vs `argentinian` vs `ARGENTINA`). Requiere diccionario de sinonimos para Gemini parser.
- **Barrio CABA generico:** busqueda "Palermo" no debe match "Ciudad Autonoma de Buenos Aires". Normalizar busqueda exacta o con FTS.

---

## 5. Qué se hizo con estos hallazgos
La base final es **PostgreSQL + PostGIS** (`database/schema.sql`), cargada con `scripts/cargar_base_unificada.py` desde `data/dataset_unificado_ARGENTINA.csv` (71.343 lugares de todo el país). `scripts/import_actual_to_postgres.py` quedó como importador legado del dataset original de 8.181 y solo debe usarse a propósito (`--legado`). La arquitectura vigente y el diseño del sistema están en `docs/arquitectura/arquitectura.md` y `docs/diseno_sistema_seccion5.md`.


## Jerarquía región > partido > zona (16/11/2026)
Cada lugar del CSV y de la tabla `restaurants` trae tres columnas, tomadas de la hoja «Lugares» del Excel unificado: `region` (CABA, GBA, Interior o Sin confirmar), `partido` / `district` (partido de GBA) y `zona` / `zone_macro` (CABA; GBA Norte, GBA Oeste o GBA Sur; en el interior, el nombre de la provincia). La `provincia` sale del Excel y `ciudad` es la localidad (en GBA incluye el partido entre paréntesis).

| Región | Zona | Lugares |
|---|---|---|
| CABA | CABA | 13.936 |
| GBA | GBA Norte | 3.477 |
| GBA | GBA Oeste | 3.757 |
| GBA | GBA Sur | 3.881 |
| GBA | GBA (sin partido) | 96 |
| Interior | Buenos Aires interior | 11.373 |
| Interior | Córdoba | 6.701 |
| Interior | Santa Fe | 4.733 |
| Interior | Mendoza | 3.394 |
| Interior | Resto de las provincias | 18.078 |
| Sin confirmar | Sin confirmar | 1.917 |

- GBA tiene 26 partidos y 11.115 lugares con partido asignado. La zona del Excel se llama «GBA Sur» (no «sureste»).
- El interior son 44.279 lugares de las 23 provincias y de la provincia de Buenos Aires fuera del GBA.
- Los 1.917 «Sin confirmar» son lugares que el Excel marca «CABA/GBA (confirmar)»: no se sabe si son de CABA o de GBA.
- Las columnas son nuevas: `scripts/convertir_base_unificada.py` las genera, `database/schema.sql` las crea (y las agrega con `ALTER TABLE` si la tabla ya existía) y `scripts/cargar_base_unificada.py` las carga.
- La búsqueda filtra por `province`, `city` y `neighborhood` (ILIKE) y, desde el 16/11/2026, también por `region`, `district` y `zone` (zona macro). El chat sigue usando provincia y ciudad; el frontend usa provincia y barrio/localidad.

## Solo Argentina: descarte y auditoría (16/11/2026)
La base no contiene lugares de otros países. La regla se aplica en tres barreras, todas offline:

1. **Conversión** (`scripts/convertir_base_unificada.py`): antes de mapear una fila se descarta si la provincia del Excel no es argentina o si sus coordenadas válidas caen fuera del recuadro del país (`-55,5..-21` de latitud, `-74..-53` de longitud). Los valores de relleno (`-350/-580`) se siguen descartando por calidad, no por país. Una calle con nombre extranjero («Montevideo 1480» en CABA) **no** es motivo de descarte.
2. **Carga** (`scripts/cargar_base_unificada.py`): segunda barrera; no inserta filas sin provincia argentina ni con coordenadas fuera del recuadro, y normaliza la provincia al nombre canónico.
3. **Validación** (`scripts/validar_base_argentina.py`): revisa el CSV y la tabla `restaurants`, informa provincia, región y coordenadas, y con `--limpiar-csv` / `--desactivar` corrige sin borrar comercios registrados.

Las 24 jurisdicciones, los alias y los lugares del exterior viven en `backend/geografia.py`, que comparten el backend, la conversión, la carga y la auditoría. La validación del chat es estricta con la provincia y con lugares del exterior inequívocos; no rechaza localidades argentinas que comparten nombre con ciudades extranjeras (`Concepción del Uruguay`, `La Paz`, `Lima`, `Asunción`).

### Resultados (16/11/2026)
- **CSV y base:** 71.343 filas, 0 provincias no argentinas, 0 coordenadas fuera de Argentina, 0 coordenadas incompletas. Reporte: `docs/pruebas/validacion_argentina_2026-11-16.md`.
- **Muestra de auditoría:** 200 casos estratificados por fuente (semilla fija `20261116`): 100 % rastreable al Excel, 100 % de provincia/ciudad coherente, 100 % de coincidencia con el archivo crudo cuando existe, 2,5 % de duplicados exactos y 3 % de provincias dudosas (las 1.917 filas «Sin confirmar»). Reporte: `docs/pruebas/auditoria_muestra_2026-11-16.md`.
- **Duplicados:** 653 grupos con clave estricta (nombre + dirección + provincia; sin dirección, coordenadas a ~10 m). La clave gruesa nombre + provincia + ciudad da 1.960 grupos y sobrecuenta sucursales; no se usa para borrar.
- **Límite conocido:** el recuadro de coordenadas es generoso y por sí solo no distingue un punto de Chile o Uruguay cercano a la frontera; esos casos los rechaza la provincia. No se consulta cada localidad en internet.

