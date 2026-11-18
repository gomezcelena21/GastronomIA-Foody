# Evaluación del intérprete del modo sin IA

Generado por `python tests/test_evaluacion_interprete.py --escribir`. Es el equivalente de evaluar un modelo con un conjunto de ejemplos: una persona preparó la respuesta correcta de cada consulta a partir del requisito (entender zona, tipo de comida y restricción) y se mide el porcentaje de aciertos exactos.

**Resultado: 40 de 42 aciertos (95 %). Mínimo aceptable: 85 %.**

| Categoría | Aciertos |
|---|---|
| normal | 10 de 10 |
| escritura | 6 de 6 |
| combinada | 2 de 2 |
| ambigua | 4 de 4 |
| nacional | 4 de 4 |
| fuera | 3 de 3 |
| gba | 11 de 11 |
| tipeo | 0 de 2 |

## Detalle

| Categoría | Consulta | Resultado | Obtenido (zona, cocinas, restricciones, zona sin datos) |
|---|---|---|---|
| normal | Restaurantes en Palermo | Acierta | ('Palermo', [], [], None) |
| normal | pizzería sin TACC en Palermo | Acierta | ('Palermo', ['pizzeria'], ['sin_tacc'], None) |
| normal | opciones veganas en Villa Crespo | Acierta | ('Villa Crespo', [], ['vegano'], None) |
| normal | comida vegetariana en Caballito | Acierta | ('Caballito', [], ['vegetariano'], None) |
| normal | sushi en Recoleta | Acierta | ('Recoleta', ['japonesa'], [], None) |
| normal | parrilla en Belgrano | Acierta | ('Belgrano', ['parrilla'], [], None) |
| normal | heladería en Núñez | Acierta | ('Núñez', ['heladeria'], [], None) |
| normal | comida china en Flores | Acierta | ('Flores', ['china'], [], None) |
| normal | empanadas en Almagro | Acierta | ('Almagro', ['empanadas'], [], None) |
| normal | café vegetariano en San Telmo | Acierta | ('San Telmo', ['cafe'], ['vegetariano'], None) |
| escritura | SIN TACC EN CABALLITO | Acierta | ('Caballito', [], ['sin_tacc'], None) |
| escritura | pizzeria sin tacc en palermo | Acierta | ('Palermo', ['pizzeria'], ['sin_tacc'], None) |
| escritura | soy celíaco, busco algo en Belgrano | Acierta | ('Belgrano', [], ['sin_tacc'], None) |
| escritura | una panadería sin gluten en Boedo | Acierta | ('Boedo', ['panaderia'], ['sin_tacc'], None) |
| escritura | algo con asado por Villa Urquiza | Acierta | ('Villa Urquiza', ['parrilla'], [], None) |
| escritura | hamburguesas veganas en Palermo | Acierta | ('Palermo', ['hamburguesa'], ['vegano'], None) |
| combinada | pizzería vegana y sin TACC en Palermo | Acierta | ('Palermo', ['pizzeria'], ['sin_tacc', 'vegano'], None) |
| combinada | café o pastelería sin gluten en Colegiales | Acierta | ('Colegiales', ['cafe', 'pasteleria'], ['sin_tacc'], None) |
| ambigua | tengo hambre | Acierta | (None, [], [], None) |
| ambigua | hola | Acierta | (None, [], [], None) |
| ambigua | asdf qwerty | Acierta | (None, [], [], None) |
| ambigua | (vacía) | Acierta | (None, [], [], None) |
| nacional | restaurante en Córdoba | Acierta | ('Córdoba', [], [], None) |
| nacional | pizzería en Rosario | Acierta | ('Rosario', ['pizzeria'], [], None) |
| nacional | algo sin TACC en Mar del Plata | Acierta | ('Mar del Plata', [], ['sin_tacc'], None) |
| nacional | restaurante en Mendoza | Acierta | ('Mendoza', [], [], None) |
| fuera | restaurante en Montevideo | Acierta | ('Montevideo', [], [], None) |
| fuera | pizzería en Madrid | Acierta | ('Madrid', ['pizzeria'], [], None) |
| fuera | algo sin TACC en Santiago de Chile | Acierta | ('Santiago de Chile', [], ['sin_tacc'], None) |
| gba | sushi en Lomas de Zamora | Acierta | ('Lomas de Zamora', ['japonesa'], [], None) |
| gba | milanesas en Avellaneda | Acierta | ('Avellaneda', [], [], None) |
| gba | algo vegano cerca de Lanús | Acierta | ('Lanús', [], ['vegano'], None) |
| gba | hamburguesas veganas en Tigre | Acierta | ('Tigre', ['hamburguesa'], ['vegano'], None) |
| gba | pizzería en Quilmes | Acierta | ('Quilmes', ['pizzeria'], [], None) |
| gba | comer en Morón sin TACC | Acierta | ('Morón', [], ['sin_tacc'], None) |
| gba | café en Béccar | Acierta | ('Béccar', ['cafe'], [], None) |
| gba | sushi en Hurlingham | Acierta | ('Hurlingham', ['japonesa'], [], None) |
| gba | pizzería en Cañuelas | Acierta | ('Cañuelas', ['pizzeria'], [], None) |
| gba | parrilla en Marcos Paz | Acierta | ('Marcos Paz', ['parrilla'], [], None) |
| gba | pizzería en Presidente Perón | Acierta | (None, ['pizzeria'], [], 'Presidente Perón') |
| tipeo | pizeria en palermo | **Falla** | ('Palermo', [], [], None) |
| tipeo | sin tak en belgrano | **Falla** | ('Belgrano', [], [], None) |

## Qué muestra

- Las consultas normales, ambiguas, nacionales (interior del país), fuera de Argentina y de GBA se resuelven bien. Una consulta ambigua no inventa parámetros.
- **Límite conocido (tipeo):** el intérprete trabaja por palabras clave y no corrige errores de escritura («pizeria», «sin tak»).
- **Cobertura nacional:** con la base cargada (más de 71.000 lugares de todo el país) se reconocen 1.598 barrios, localidades, ciudades y partidos. Para los partidos de GBA sin locales cargados (por ejemplo Presidente Perón) el sistema lo dice en lugar de mostrar locales de otra zona.
- Cuando se cambia el intérprete, esta evaluación se vuelve a correr (es la prueba de regresión de la IA).
