# GastronomIA — Casos de uso

Actores: **Usuario** (persona que busca dónde comer), **Sistema** (frontend + backend), **IA** (Gemini). Cada caso indica las historias y los casos de prueba (`docs/pruebas/casos_de_prueba_GastronomIA.xlsx`) que lo cubren.

## CU-01 Buscar con lenguaje natural — HU-01, 03, 07, 08, 09 · TC-001 a TC-007
- **Precondición:** backend y frontend en marcha.
- **Flujo principal:** 1) el usuario escribe su consulta en el chat; 2) el backend la limpia y le agrega el perfil; 3) la IA devuelve los parámetros de búsqueda; 4) el backend valida la cobertura y consulta la base; 5) la IA redacta la respuesta con los resultados reales; 6) el backend valida la respuesta; 7) se muestran los locales con su fuente y el motivo.
- **Alternativos:** consulta de otro país → se informa que solo hay datos de Argentina, sin recomendar (A1). Consulta no interpretable → se ofrecen los filtros manuales (A2). Sin resultados → se sugiere flexibilizar criterios (A3). La respuesta de la IA inventa datos → se reemplaza por una respuesta armada solo con datos de la base (A4).
- **Postcondición:** la conversación, los mensajes y las recomendaciones quedan registrados.

## CU-02 Ver la ficha de un local — HU-02, 04, 05, 16 · TC-008, TC-010, TC-011, TC-012
- **Flujo principal:** el usuario toca «Ver ficha»; se muestran dirección, teléfono, web, fuente y fecha, la advertencia alimentaria («Información inferida. Confirmar con el local» o «Sin datos») y «¿Por qué te lo recomendamos?». Puede contactar por teléfono o sitio web.

## CU-03 Repreguntar sobre los resultados — HU-06 · TC-009
- **Flujo principal:** tras recibir una lista, el usuario pide «¿cuál es el más barato?»; la IA responde sobre la lista anterior sin reiniciar la búsqueda.
- **Alternativo:** sin cuota de IA no hay seguimiento de contexto (límite declarado).

## CU-04 Filtrar manualmente — HU-01 (CA-03), HU-10 · TC-039
- **Flujo principal:** en Explorar, el usuario elige provincia y necesidades alimentarias y recibe el listado.

## CU-05 Gestionar el perfil y las restricciones — HU-11, 12 · TC-033 a TC-035
- **Flujo principal:** el usuario carga una o varias restricciones y preferencias; el sistema las guarda (`/api/usuarios`) y las aplica a cada búsqueda.
- **Alternativos:** email inválido o restricción desconocida → rechazo con mensaje claro.

## CU-06 Dejar una reseña — HU-13 · TC-036, TC-037
- **Flujo principal:** el usuario escribe su opinión; el sistema extrae valoraciones por aspecto (comida, servicio, precio, ambiente…) y confirma el guardado.
- **Estado:** el endpoint y la extracción funcionan; falta el formulario en pantalla.

## CU-07 Buscar cerca de mí — HU-10
- **Flujo principal:** el usuario comparte su ubicación y recibe locales cercanos. **Estado:** parcial (ver auditoría).

## CU-08 Atender una consulta sin cuota de IA — NF-01 · TC-024 a TC-027
- **Disparador:** Gemini responde 429 o se llenó el cupo por minuto.
- **Flujo principal:** el sistema espera si la espera es corta; si no, interpreta la consulta por reglas, consulta la base y responde con un aviso de que no hay IA.
