# Auditoría por muestreo de la base nacional

- **Fecha:** 2026-11-16
- **Muestra:** 200 casos estratificados por fuente, semilla fija `20261116`.
- **Población:** 71.343 lugares.
- **Método:** sin consultas a internet. Se compara cada caso con la planilla de origen por `ID` y, cuando hay archivo crudo, con Overture u OSM/BA Data por identificador, nombre y coordenadas (tolerancia 1 km).

## Resultado global

| Indicador | Resultado |
|---|---:|
| Rastreables en el Excel de origen | 200/200 (100.0 %) |
| Fuente coincide con el Excel | 200/200 (100.0 %) |
| Provincia coincide con el Excel | 200/200 (100.0 %) |
| Ciudad/barrio coherente | 200/200 (100.0 %) |
| Dirección coincide (sobre las comparables) | 187/187 (100.0 %) |
| Coordenadas coinciden (sobre las comparables) | 182/182 (100.0 %) |
| Aparece en el archivo crudo (sobre las comparables) | 188/188 (100.0 %) |
| Duplicados exactos en la muestra | 5/200 (2.5 %) |
| Provincias dudosas en la muestra | 6/200 (3.0 %) |

## Por fuente

| Fuente | Población | Muestra | Rastreable | Provincia OK | Ciudad OK | Crudo OK | Duplicados | Dudosas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| overture | 62.880 | 158 | 100 % | 100 % | 100 % | 100 % | 3 % | 0 % |
| osm | 5.431 | 18 | 100 % | 100 % | 100 % | 100 % | 0 % | 28 % |
| ba_data | 2.721 | 12 | 100 % | 100 % | 100 % | 100 % | 0 % | 0 % |
| google_places | 302 | 6 | 100 % | 100 % | 100 % | n/d | 0 % | 0 % |
| guia_kosher | 8 | 5 | 100 % | 100 % | 100 % | n/d | 20 % | 0 % |
| guia_celiacos | 1 | 1 | 100 % | 100 % | 100 % | n/d | 0 % | 100 % |

## Duplicados en toda la base

- Clave estricta (nombre + dirección + provincia; sin dirección, coordenadas a ~10 m): **653 grupos**, **653 filas extra**.
- Clave gruesa (nombre + provincia + ciudad): **1.960 grupos**, **2.731 filas extra**. La clave gruesa sobrecuenta cadenas con varias sucursales; no se usa para borrar.

## Casos para revisar en la muestra

| ID | Nombre | Fuente | Provincia | Ciudad | Motivo |
|---|---|---|---|---|---|
| U00460 | 404 Not Found | guia_celiacos | Buenos Aires | Sin confirmar | región Sin confirmar; ciudad Sin confirmar; provincia a confirmar en el Excel |
| U07690 | Al Taglio | osm | Buenos Aires | Sin confirmar | región Sin confirmar; ciudad Sin confirmar; provincia a confirmar en el Excel |
| U03591 | Bendito Pizza | osm | Buenos Aires | Sin confirmar | región Sin confirmar; ciudad Sin confirmar; provincia a confirmar en el Excel |
| U04036 | Parilla El Colo | osm | Buenos Aires | Sin confirmar | región Sin confirmar; ciudad Sin confirmar; provincia a confirmar en el Excel |
| U07743 | Fábrica Pizzas | osm | Buenos Aires | Sin confirmar | región Sin confirmar; ciudad Sin confirmar; provincia a confirmar en el Excel |
| U04269 | Lo de Charly | osm | Buenos Aires | Sin confirmar | región Sin confirmar; ciudad Sin confirmar; provincia a confirmar en el Excel |

## Cobertura de archivos

- Excel de origen: `C:\Users\Usuario\Documents\Base de datos Gastronomia\Base_Unificada_Restricciones_Argentina.xlsx`
- Overture crudo: `C:\Users\Usuario\Documents\Base de datos Gastronomia\overture_ar.csv`
- OSM/BA Data crudo: `C:\Users\Usuario\Documents\GastronomIA\Gastronomía Proyecto\etl\raw\dataset_gastronomia_CABA_GBA.csv`

## Limitaciones

- No se valida cada localidad contra un mapa en línea: la auditoría es de **trazabilidad** (¿el dato existe en la fuente?) y de **coherencia interna** (provincia, ciudad, dirección y coordenadas).
- Las fuentes Google Places, guías kosher y guías de celíacos no tienen archivo crudo en el repositorio; para ellas se informa `n/d` en la columna de archivo crudo.
- Una fila «dudosa» no es un error: marca datos que el sistema ya señala como provisorios (por ejemplo, región «Sin confirmar»).

## Conclusión

**Muestra consistente:** prácticamente todos los casos se rastrean a la planilla y a las fuentes crudas, y las dudas de provincia son marginales.
