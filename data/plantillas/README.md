# Plantillas de importación

## menús — `menus.csv`

 Usar con:

```bash
python scripts/importar_menus_csv.py data/plantillas/menus.csv --dry-run
python scripts/importar_menus_csv.py data/plantillas/menus.csv
```

- `restaurant_id` y `dish_name` son obligatorios.
- `price` acepta `12500`, `12.500,50` o `$12.500`.
- `ingredients` se separa con `|` o `;`.
- Las columnas `gluten_free`, `vegetarian`, `vegan`, `lactose_free`,
  `contains_gluten`, `contains_lactose`, `contains_egg` y `contains_nuts`
  aceptan `si` o `no`.
- Si el local ya tenía menús y querés reemplazarlos:
  `--reemplazar` (borra solo los menús de los restaurantes del CSV).

Ejemplo de fila:

```csv
restaurant_id,dish_name,category,description,price,currency,ingredients,gluten_free,vegetarian,vegan,lactose_free,contains_gluten,contains_lactose,contains_egg,contains_nuts,carbohydrates,sugars,fiber,proteins,fats,portion_size,confidence_level,data_date
42,Milanesa de berenjena,principal,Con puré de papa,12500,ARS,berenjena|pan rallado|huevo|papa,no,si,no,si,si,no,si,no,,,,,,plato,community,2026-11-10
```

## verificación sin TACC — `verificacion_sin_tacc.csv`

Primero generá el reporte:

```bash
python scripts/verificar_sin_tacc.py
```

El reporte incluye todos los locales y una columna `sin_tacc` con `si`, `no` o
`sin_dato`. El equipo llama a los locales, completa el estado y después importa:

```bash
python scripts/importar_sin_tacc_csv.py data/plantillas/verificacion_sin_tacc.csv --dry-run
python scripts/importar_sin_tacc_csv.py data/plantillas/verificacion_sin_tacc.csv
```

- `sin_tacc`: `si`, `no`, `opciones` o `sin_dato`.
- `celiac_certified`: `si` o `no` (opcional).
- `confidence_level`: `official`, `community`, `no_verified` (por defecto
  `community`).
- `fuente`: por ejemplo `Llamado telefónico 2026-11-10`.
- `fecha`: `AAAA-MM-DD` (por defecto hoy).

> Importante: ninguna carga convierte un local en “apto garantizado”. El chat y
> los términos siempre recomiendan confirmar con el establecimiento por
> contaminación cruzada.
