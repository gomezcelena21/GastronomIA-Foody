# Validación geográfica de Argentina

- **Fecha:** 2026-11-16
- **CSV:** `C:\Users\Usuario\Documents\GastronomIA\Gastronomía Proyecto\data\dataset_unificado_ARGENTINA.csv`
- **Fuente de provincias:** `backend/geografia.py` (23 provincias + CABA).
- **Criterio:** se descarta solo lo que no se puede ubicar en Argentina (provincia no argentina o coordenadas fuera del recuadro del país). No se descartan direcciones con nombres extranjeros (por ejemplo, «Montevideo 1480» en CABA).

## CSV

- Filas: **71.343**
- Con coordenadas: **68.612** (96.2 %)
- Provincias no argentinas: **0**
- Coordenadas fuera de Argentina: **0**
- Coordenadas incompletas: **0**
- Regiones desconocidas: **0**
- Sin ciudad: **0** · Sin zona: **0**

### Provincias

| Provincia | Lugares |
|---|---:|
| Buenos Aires | 24.501 |
| CABA | 13.936 |
| Córdoba | 6.701 |
| Santa Fe | 4.733 |
| Mendoza | 3.394 |
| Entre Ríos | 1.813 |
| Salta | 1.728 |
| Tucumán | 1.638 |
| Río Negro | 1.351 |
| Misiones | 1.147 |
| Neuquén | 1.030 |
| Jujuy | 974 |
| Chubut | 969 |
| Corrientes | 964 |
| Chaco | 925 |
| Santiago del Estero | 916 |
| San Luis | 807 |
| San Juan | 730 |
| Santa Cruz | 635 |
| Catamarca | 596 |
| La Rioja | 526 |
| La Pampa | 500 |
| Formosa | 433 |
| Tierra del Fuego | 396 |

### Ejemplos de provincias no argentinas

_Ninguno._

### Ejemplos de coordenadas fuera de Argentina

_Ninguno._

### Ejemplos de coordenadas incompletas

_Ninguno._

## Base de datos (`restaurants`)

- Filas: **71.343** · activas: **71.343**
- Provincias no argentinas: **0**
- Coordenadas fuera de Argentina: **0**
- Coordenadas incompletas: **0**
- Regiones desconocidas: **0**

### Ejemplos de provincias no argentinas en la base

_Ninguno._

### Ejemplos de coordenadas fuera de Argentina en la base

_Ninguno._

## Acciones

- Solo validación: no se modificó ningún archivo ni fila.

## Conclusión

**Sin fallas geográficas:** todas las filas tienen una provincia argentina y, cuando tienen coordenadas, caen dentro de Argentina.
