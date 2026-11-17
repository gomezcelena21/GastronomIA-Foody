# Plan de pruebas de GastronomIA

Documento de referencia de las pruebas del proyecto (consigna del TPI, sección 7, y apunte de la unidad 7). Resume qué se prueba, con qué
estrategia, quién, con qué criterio se da por terminado y dónde están los resultados.

## 1. Objetivo y alcance

**Objetivo:** comprobar que el sistema cumple las 16 historias de usuario y que la funcionalidad de IA (asistente Foody con Gemini) es
confiable: no inventa datos, no se rompe cuando la API falla y no deja pasar entradas peligrosas.

| Se prueba | No se prueba (todavía) |
|---|---|
| Backend: reglas de negocio, validaciones, seguridad, modo sin IA | Prueba de carga del sitio publicado con miles de usuarios (necesita una herramienta externa) |
| Funcionalidad de IA: casos, adversarios, fallas de la API | Calidad de las respuestas de Gemini ante cualquier pregunta posible (se muestrea con 10 casos) |
| Frontend: tipos (`tsc`) y recorridos E2E con Playwright | Compatibilidad con todos los navegadores y teléfonos |
| Despliegue: configuración (puerto cerrado, `/ping`, HTTPS) | Rendimiento de los servicios gratis (Render, Neon, Vercel) |

## 2. Estrategia: del centro del espiral hacia afuera

| Nivel | Qué verifica | Archivos / herramienta | Quién |
|---|---|---|---|
| **Unidad** (caja blanca) | Cada función por separado, todos sus caminos | `test_diseno`, `test_caja_blanca`, `test_privacidad`, `test_sesion`, `test_cuota` | Equipo, automática |
| **Integración** | Backend + base de datos + componentes de IA | `test_api_diseno` (necesita FastAPI y PostgreSQL), `scripts/probar_ia.py` | Equipo, automática |
| **Validación** (caja negra) | Que se cumplan los requisitos y las historias de usuario | `test_caja_negra`, `test_casos_uso_ia`, planilla `casos_de_prueba_GastronomIA.xlsx` | Equipo |
| **Sistema** | Seguridad, recuperación ante fallas, rendimiento, recorridos completos | ver sección 5 | Equipo |
| **Aceptación** | Que le sirva a quien lo usa | prueba alfa y beta (sección 7) | Docente, familiares, comercios |

Se prueba de abajo hacia arriba y de forma incremental: primero cada función, después cómo se combinan, y recién después el sistema completo.

## 3. Técnicas de diseño de casos

- **Caja blanca (camino básico):** `caja_blanca.md` — grafo de flujo, V(G) y un caso por camino para tres funciones.
- **Caja negra (particiones y valores límite):** `caja_negra.md`.
- **Los resultados esperados salen del requisito, no del código** (historias en `docs/historias-usuario/`).

## 4. Pruebas específicas de la funcionalidad de IA (TPI, sección 7)

| Qué | Dónde | Estado |
|---|---|---|
| 10 casos con entrada, respuesta y evaluación: uso normal, ambiguos, fuera de cobertura y de dominio, dos adversarios (inyección y garantía falsa) y un caso límite (mensaje de 1.501 caracteres) | `casos_ia.md` + `scripts/probar_ia.py` | Casos definidos. **Resultado con la API real: pendiente de correr en la PC del equipo** (`python scripts\probar_ia.py` con el backend en marcha); queda en `resultados_ia_<fecha>.md` |
| Falla de la API (cuota, timeout, respuesta vacía) | `test_cuota`, `test_modo_sin_ia`, casos TC-024 a TC-027 | Automática, pasa |
| Respuesta inventada o peligrosa (teléfono, local o «100 % seguro» inventados) | `test_diseno.ValidarRespuestaIA`, TC-013 a TC-018 | Automática, pasa |
| Órdenes escondidas en los datos de un comercio | `test_comercios` (TC-043, TC-044) | Automática, pasa |
| Evaluación con ejemplos del intérprete del modo sin IA | `evaluacion_interprete.md` | 35 de 37 (95 %), mínimo 85 % |
| Casos difíciles y de equidad (ambigua, vacía, GBA sin datos, errores de tipeo) | `evaluacion_interprete.md` | Incluidos; los errores de tipeo son un límite conocido |
| Las pruebas pueden fallar (romper a propósito) | `romper_a_proposito.md` | 12 de 12 detectados |

## 5. Pruebas del sistema

| Tipo | Qué se hace | Evidencia |
|---|---|---|
| **Seguridad** | SQL parametrizado, descargas confinadas, límites por IP, sin secretos en el código, datos de comercios tratados como datos, puerto del backend cerrado | `test_seguridad_codigo`, `test_diseno.EntradasSeguras`, `test_comercios`, `test_despliegue`, `docs/seguridad_ciberseguridad.md`, `docs/revision_seguridad.md` |
| **Recuperación** | Se agota la cuota de Gemini: el sistema sigue respondiendo en modo sin IA; la base no responde: mensaje claro | `test_cuota`, `test_modo_sin_ia`, TC-024 a TC-027 |
| **Rendimiento** (local) | 2.000 respuestas del modo sin IA en pocos segundos; validar una respuesta larga en menos de 1 s | `test_rendimiento` (TC-055) |
| **Resistencia** (local) | 16 hilos compitiendo por el limitador: deja pasar exactamente el máximo; 20.000 clientes distintos sin romperlo | `test_rendimiento` (TC-056) |
| **Carga del sitio publicado** | Pendiente: se haría con una herramienta externa contra el sitio en Render/Vercel | — |
| **Recorridos completos (E2E)** | Landing y aplicación con Playwright | `frontend/` |

## 6. Verificación y validación

- **Verificación** (¿lo construimos bien?): pruebas de unidad, caja blanca, seguridad y auditoría del código contra el diseño (`AUDITORIA.bat`, `docs/auditoria_tpi.md`).
- **Validación** (¿construimos lo correcto?): casos por historia de usuario con criterios de aceptación, y las pruebas alfa y beta.

## 7. Pruebas alfa y beta (plan)

El apunte distingue la prueba **alfa** (el cliente prueba en el lugar de desarrollo, en un entorno controlado) y la **beta** (usuarios finales en su propio entorno, sin el equipo presente).

| Prueba | Quién | Dónde | Qué se registra |
|---|---|---|---|
| Alfa | Docente y compañeros, con el equipo presente | La exposición, con el sistema publicado | Problemas de uso, dudas, sugerencias |
| Beta | Familiares y comercios de la zona | Desde su teléfono o computadora, con el enlace público | Problemas encontrados, dispositivo, qué se esperaba |

Registro (completar con lo que realmente ocurra; no se completa de antemano):

| Fecha | Tipo | Quién | Qué probó | Problemas encontrados | Estado |
|---|---|---|---|---|---|
| (pendiente) | Alfa | | | | |
| (pendiente) | Beta | | | | |

## 8. Regresión

Toda corrección puede romper algo que funcionaba. Por eso, después de cada cambio se vuelve a ejecutar **todo** (`python -m unittest discover -s tests` o
`AUDITORIA.bat`), y la evaluación del intérprete se repite cada vez que cambia el intérprete.

## 9. Criterio para dar por terminada una prueba

- Todas las pruebas automáticas pasan (las que necesitan base de datos, en la PC del equipo).
- Los casos de la planilla con prioridad Alta están en «Pasó».
- Los 10 casos de IA tienen su resultado registrado y evaluado.
- Ningún bug de gravedad Crítica o Alta queda abierto en `registro_de_bugs.md` (el BUG-03/BUG-20 requiere una acción manual: rotar las claves).
- Una prueba que pasa **no demuestra que no haya errores**: solo que con esas pruebas no se encontraron.

## 10. Documentación y registro de defectos

- Casos de prueba: `casos_de_prueba_GastronomIA.xlsx` (planilla) y los archivos de `tests/`.
- Defectos: `registro_de_bugs.md`, con pasos para reproducir, resultado esperado y obtenido, gravedad y caso asociado.
- Uso de IA en las pruebas: `docs/uso_ia.md`.

## 11. Cómo ejecutar

```
python -m unittest discover -s tests -v          # todo
python -m unittest tests.test_caja_blanca -v     # un archivo
python scripts\romper_a_proposito.py --informe   # prueba de las pruebas
python tests\test_evaluacion_interprete.py --escribir
set PRUEBAS_CON_BD=1 & python -m unittest tests.test_api_diseno -v   # con FastAPI y PostgreSQL
```

## 12. Resultados de la última ejecución (12/11/2026)

| Qué | Resultado |
|---|---|
| Pruebas automáticas (entorno sin FastAPI ni PostgreSQL) | 237 pruebas: 212 OK, 25 salteadas, 0 fallas |
| Romper a propósito | 12 de 12 errores detectados |
| Evaluación del intérprete | 35 de 37 (95 %) |
| Complejidad ciclomática calculada sobre el código | coincide con la documentada (2, 6 y 5) |
| Pruebas de API con base de datos | **Pendiente de correr en la PC del equipo** |
| 10 casos de IA con la API real | **Pendiente de correr en la PC del equipo** |
