# Red neuronal propia de Foody

Generado por `python scripts/entrenar_modelo_foody.py` el 2026-11-26. Código: `backend/modelo_foody.py`. Pesos: `backend/modelo_foody.json` (722 KB). Textos de respuesta: `backend/conocimiento_foody.py`.

## Para qué sirve

Cuando Gemini (y el proveedor de respaldo) no responden, Foody entiende la consulta sin IA externa. La red reconoce el tipo de comida, la restricción alimentaria y el precio aunque haya errores de tipeo o se usen otras palabras («pizeria», «sin tak», «pastas», «algo baratito»), y además la intención: si la persona saluda, agradece, se despide, pide ayuda, pregunta qué es algo («¿qué es sin TACC?»), cuenta una restricción que la base no cubre (lactosa, diabetes, alergias), opina sobre un local o pregunta algo que no es de comida.

La red **entiende, no redacta**: las respuestas son textos escritos y revisados a mano, amables y con las advertencias de seguridad. Así nunca puede inventar un dato de salud. Solo agrega lo que entiende: nunca quita una restricción que detectaron las reglas.

## Cómo es

- **Tipo:** perceptrón multicapa (una capa oculta ReLU) con 30 salidas sigmoides (clasificación multietiqueta): 3 restricciones, 17 tipos de comida, 2 de precio y 8 intenciones.
- **Entrada:** palabras, pares de palabras y trozos de 2 a 4 letras, llevados a 4096 posiciones con *hashing*. Los trozos de letras son lo que la hace tolerante a errores de tipeo.
- **Entrenamiento:** 59468 frases sintéticas (plantillas formales y coloquiales, sinónimos, zonas reales de la base, errores de tipeo simulados y ejemplos negativos), optimizador Adam, entropía cruzada binaria. Solo numpy, sin GPU.
- **En producción:** inferencia en Python puro y pesos en int8. No suma dependencias al servidor gratis de Render.

## Comparación de versiones

Se entrenaron 6 versiones y se eligió la mejor **solo con la validación sintética**, para que la prueba manual y las consultas reales sigan siendo una evaluación independiente.

| Neuronas ocultas | Épocas | Validación sintética | Prueba manual | Consultas reales | Tiempo |
|---|---|---|---|---|---|
| 32 | 12 | 5650 de 5945 (95 %) | 141 de 145 (97 %) | 36 de 38 (95 %) | 30 s |
| 48 | 14 | 5649 de 5945 (95 %) | 143 de 145 (99 %) | 36 de 38 (95 %) | 55 s |
| 64 | 14 | 5666 de 5945 (95 %) | 140 de 145 (97 %) | 34 de 38 (89 %) | 83 s |
| 96 | 14 | 5673 de 5945 (95 %) | 144 de 145 (99 %) | 35 de 38 (92 %) | 106 s |
| 64 | 20 | 5680 de 5945 (96 %) | 144 de 145 (99 %) | 35 de 38 (92 %) | 121 s |
| 128 **(elegida)** | 16 | 5688 de 5945 (96 %) | 140 de 145 (97 %) | 35 de 38 (92 %) | 142 s |

## Resultados de la versión elegida

| Conjunto | Aciertos exactos | Precisión | Exhaustividad |
|---|---|---|---|
| Validación sintética | 5688 de 5945 (96 %) | 0.99 | 0.97 |
| Prueba escrita a mano | 140 de 145 (97 %) | 0.99 | 0.98 |
| Consultas reales hechas a Foody | 35 de 38 (92 %) | 0.93 | 1.00 |

*Acierto exacto:* todas las etiquetas de la frase correctas, sin sobrantes. *Precisión:* de las etiquetas que puso la red, cuántas eran correctas (bajo = inventa). *Exhaustividad:* de las correctas, cuántas encontró (bajo = se le escapan).

### Por grupo (prueba escrita a mano)

| Grupo | Precisión | Exhaustividad |
|---|---|---|
| restricciones | 1.00 | 1.00 |
| cocinas | 1.00 | 0.97 |
| precio | 1.00 | 1.00 |
| intenciones | 0.96 | 0.98 |

### Fallos en prueba escrita a mano

| Consulta | Esperado | Obtenido |
|---|---|---|
| parila en villa urquiza | parrilla | (nada) |
| asdo en mataderos | parrilla | (nada) |
| guiso de lentejas | comida_casera | comida_casera, gracias |
| conoces alguna parrilla buena por mataderos? | parrilla | parrilla, saludo |
| como hago una pagina web | fuera_de_tema | (nada) |

### Fallos en consultas reales

| Consulta | Esperado | Obtenido |
|---|---|---|
| (3 frases; no se publican por privacidad) | | |

## Límites

- Honestidad sobre la evaluación: la prueba escrita a mano y las consultas reales no se usan para entrenar, pero sí se miraron durante el desarrollo para encontrar qué le faltaba aprender (se agregaron plantillas generales, nunca las frases de prueba). La prueba más independiente son consultas NUEVAS que la red no vio nunca (por ejemplo, las de producción exportadas con scripts/exportar_consultas_reales.py).
- Los datos de entrenamiento son sintéticos. Las consultas reales se usan solo para evaluar; cuando haya más, se pueden sumar al entrenamiento.
- No entiende negaciones («no soy celíaco»): igual que las reglas, en la duda agrega la restricción, que es lo más seguro.
- No redacta: si la pregunta no encaja en ninguna intención conocida, Foody pide que la reformule.
- La zona la siguen resolviendo las reglas (con corrección de tipeo aparte), porque son más de 1.600 nombres propios.
