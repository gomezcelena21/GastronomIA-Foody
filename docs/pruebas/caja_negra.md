# Pruebas de caja negra: particiones de equivalencia y valores límite

La caja negra diseña los casos **desde el requisito**, sin mirar el código. Se divide la entrada en clases donde se espera el mismo
comportamiento (particiones de equivalencia), se incluyen siempre las clases inválidas y se prueban los **valores justo en el límite y
justo afuera**. Los resultados esperados salen del requisito, no de lo que hace el código.

Pruebas: `tests/test_caja_negra.py` (11 pruebas, casos TC-051, TC-052 y TC-053 de la planilla).

## 1. Longitud del mensaje del chat (requisito: 1 a 1.500 caracteres)

| Partición | Entrada | Esperado |
|---|---|---|
| Inválida: no es texto | `None`, `123`, `[]` | `""` |
| Inválida: vacío | `""`, `"   "`, `"\t\n"` | `""` |
| Límite inferior | 1 carácter | 1 carácter |
| Válida | 2 y 1.499 caracteres | sin cambios |
| **Límite superior** | **1.500** caracteres | 1.500 (sin recortar) |
| **Justo afuera** | **1.501** y 5.000 caracteres | recortado a 1.500 |
| Con caracteres de control | `"ho\x00la\x07"` | `"hola"` |

## 2. Cantidad de resultados (requisito: de 1 a 25; si el dato no sirve, 10)

| Partición | Entrada | Esperado |
|---|---|---|
| Por debajo del mínimo | `-5`, `0` | 1 |
| **Límite inferior / válida** | `1`, `2`, `10`, `24` | igual |
| **Límite superior** | `25` | 25 |
| **Por encima del máximo** | `26`, `1000` | 25 |
| Texto numérico / decimal | `"7"`, `7.9` | 7 |
| Inválida: no numérica | `"abc"`, `None` | 10 |
| Inválida: intento de inyección | `"1; DROP TABLE restaurants"` | 10 |

## 3. Cobertura geográfica (HU-03: toda la Argentina)

| Partición | Entrada | Esperado |
|---|---|---|
| Cubierta | `Palermo`, `Lanús Oeste`, `Rosario`, `Mar del Plata`; provincias `CABA`, `Buenos Aires`, `Córdoba`, `Santa Fe`, `Mendoza`; sin zona | aceptada |
| Fuera de cobertura | ciudades `Montevideo`, `Madrid`, `Miami`, `Santiago de Chile`; provincias `Uruguay`, `Chile` | rechazada con el mensaje de que solo hay datos de Argentina |
| **Límite: nombres parecidos** | `San Justo` (GBA), `San Juan` (provincia), `Concepción del Uruguay` (Entre Ríos) frente a `Uruguay` (país) | aceptada / aceptada / aceptada / rechazada |
| Mayúsculas y tildes | `MONTEVIDEO`, `URUGUAY` (rechazadas); `CÓRDOBA`, `cordoba` (aceptadas) | coherente con lo anterior |
| **Límite conocido** | `Tandil` (ciudad que no figura en la lista de zonas) | **se acepta**: el sistema rechaza lugares de otros países, no exige una lista blanca; la base devuelve cero resultados |

El último caso es un hallazgo de la caja negra: no es un error, pero queda documentado como límite de diseño.

## 4. Límite de mensajes por minuto (requisito SEG-06: 20 por minuto por cliente)

| Situación | Esperado |
|---|---|
| Mensajes 1.º al 20.º en la misma ventana | permitidos |
| **Mensaje 21.º** | rechazado |
| **Justo en el borde de la ventana** (60 s después) | rechazado |
| **Recién afuera** (60,001 s) | permitido otra vez (la ventana se desliza) |
| Otro cliente distinto | no se ve afectado |

## Relación con la caja blanca

Los mismos tres requisitos se probaron también con caja blanca (`caja_blanca.md`). Cada técnica encuentra lo que la otra no ve: la
blanca asegura que todos los caminos del código se ejecutan; la negra asegura que lo que el requisito pide realmente ocurre,
incluso en los bordes.
