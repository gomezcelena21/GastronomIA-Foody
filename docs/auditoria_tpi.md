# Auditoría automática — GastronomIA

Generada el 17/11/2026 21:53 con `python auditoria/auditar.py` (Python 3.14.6, Windows). Este archivo se reescribe en cada corrida.

**Veredicto:** SIN FALLAS. Hay límites conocidos y advertencias declarados abajo (nada oculto).

| ✔ OK | ◐ PARCIAL | ⚠ ADVERTENCIA | ○ NO IMPLEMENTADA | ✋ MANUAL | … NO EJECUTADO | ✘ FALLA |
|---|---|---|---|---|---|---|
| 60 | 6 | 2 | 1 | 4 | 1 | 0 |


## 1. Diseño del sistema (PDF Sección 5) vs. código

| ID | Verificación | Estado | Detalle |
|---|---|---|---|
| D-01 | Base de datos: 12 entidades (+2 tablas de unión del ER) | ✔ OK | Las 14 tablas están definidas en models.py y models_diseno.py. |
| D-02 | 9 endpoints del backend (sección 5.10.1) | ✔ OK | Los 9 endpoints están declarados. |
| D-03 | 5 métodos del backend (sección 5.10.2) | ✔ OK | OrquestadorBackend: procesar_consulta, preparar_solicitud_ia, validar_parametros, consultar_base_de_datos, validar_respuesta_ia |
| D-04 | 3 métodos del componente de IA (sección 5.10.2) | ✔ OK | ComponenteIA: interpretar_consulta, generar_respuesta, extraer_valoraciones. Con Gemini, interpretar y redactar ocurren dentro del function calling; las versiones por reglas son las del modo sin IA. |
| D-05 | Flujo de 8 etapas (validación y registro) | ✔ OK | validar_parametros se aplica antes de consultar la base; la respuesta de la IA se valida antes de mostrarla (etapa 7); si la validación falla se responde solo con datos reales; la consulta se limpia antes de usarse; la conversación se registra (Conversacion/Mensaje/Recomendacion) |
| D-06 | La IA nunca accede a la base de datos (regla de diseño) | ✔ OK | ComponenteIA no referencia db, Session, query ni execute. |
| D-07 | Una característica alimentaria nunca se presenta como garantía | ✔ OK | Existe la advertencia estándar, el campo nivel_informacion (declarado/inferido/no_verificado) y el validador de garantías absolutas. |

## 2. Historias de usuario (HU-01 a HU-16): ¿está implementada y probada?

| ID | Verificación | Estado | Detalle |
|---|---|---|---|
| HU-01 | Búsqueda en lenguaje coloquial con IA | ✔ OK | Pruebas: 3 de 3 pruebas automáticas pasaron. |
| HU-02 | Advertencias de seguridad alimentaria | ✔ OK | Pruebas: 4 de 4 pruebas automáticas pasaron. |
| HU-03 | Consultas fuera de la cobertura geográfica | ✔ OK | Pruebas: 1 de 1 pruebas automáticas pasaron. |
| HU-04 | Citación transparente de la fuente | ✔ OK | Pruebas: 4 de 4 pruebas automáticas pasaron. |
| HU-05 | Contacto directo para confirmar restricciones | ✔ OK | Pruebas: verificación manual pendiente (TC-010). |
| HU-06 | Refinamiento conversacional de resultados | ◐ PARCIAL | El contexto de la conversación lo mantiene Gemini (sesión por usuario). En el modo sin IA no hay seguimiento de contexto. Pruebas: verificación manual pendiente (TC-009). |
| HU-07 | Consultas sin resultados coincidentes | ✔ OK | Pruebas: 1 de 1 pruebas automáticas pasaron. |
| HU-08 | Preferencias de ambiente y presupuesto | ◐ PARCIAL | El presupuesto se filtra por nivel de precio (1 a 4); la base no tiene el dato «ambiente», por eso no se puede filtrar por romántico o tranquilo. Pruebas: sin prueba automática: verificación manual. |
| HU-09 | Búsqueda específica de restricciones | ◐ PARCIAL | Devuelve los locales que existan en la base; hay pocos registros con oferta sin TACC, así que no se puede garantizar «al menos 3» en cada barrio. Pruebas: 2 de 2 pruebas automáticas pasaron. |
| HU-10 | Búsqueda por ubicación actual | ◐ PARCIAL | Existe la búsqueda por cercanía (/api/restaurants/nearby y herramienta del chat), pero no está unificada en GET /api/establecimientos ni limita a 15 cuadras (radio configurable en km). Pruebas: sin prueba automática: verificación manual. |
| HU-11 | Registro de restricciones recurrentes | ✔ OK | Pruebas: 1 de 1 pruebas automáticas pasaron. |
| HU-12 | Múltiples restricciones simultáneas | ✔ OK | Pruebas: 1 de 1 pruebas automáticas pasaron. |
| HU-13 | Reseñas en lenguaje natural | ◐ PARCIAL | El endpoint y la extracción de aspectos funcionan; falta el formulario o la ruta desde el chat para enviar la reseña. Pruebas: 2 de 2 pruebas automáticas pasaron. |
| HU-14 | Sugerencias basadas en historial | ◐ PARCIAL | Se guardan restricciones, preferencias e historial y se pasan a la IA; todavía no se infieren gustos a partir de reseñas pasadas. Pruebas: sin prueba automática: verificación manual. |
| HU-15 | Solicitud proactiva de feedback | ○ NO IMPLEMENTADA | NO IMPLEMENTADA: requiere un planificador de mensajes automáticos y la ficha con reseñas; está prevista en el diseño pero fuera del alcance del prototipo. Pruebas: sin prueba automática: verificación manual. |
| HU-16 | Explicación de la recomendación | ✔ OK | Pruebas: 1 de 1 pruebas automáticas pasaron. |

## 3. Pruebas automatizadas

| ID | Verificación | Estado | Detalle |
|---|---|---|---|
| P-01 | Todas las pruebas automáticas | ✔ OK | 258 pruebas: 258 pasaron, 0 salteadas, 0 fallaron en 3.41 s. |
| P-api_diseno | test_api_diseno.py | ✔ OK | 23 pasaron, 0 salteadas, 0 fallaron. |
| P-base_unificada | test_base_unificada.py | ✔ OK | 24 pasaron, 0 salteadas, 0 fallaron. |
| P-caja_blanca | test_caja_blanca.py | ✔ OK | 14 pasaron, 0 salteadas, 0 fallaron. |
| P-caja_negra | test_caja_negra.py | ✔ OK | 11 pasaron, 0 salteadas, 0 fallaron. |
| P-casos_uso_ia | test_casos_uso_ia.py | ✔ OK | 24 pasaron, 0 salteadas, 0 fallaron. |
| P-chat_garantias | test_chat_garantias.py | ✔ OK | 6 pasaron, 0 salteadas, 0 fallaron. |
| P-comercios | test_comercios.py | ✔ OK | 18 pasaron, 0 salteadas, 0 fallaron. |
| P-cuota | test_cuota.py | ✔ OK | 15 pasaron, 0 salteadas, 0 fallaron. |
| P-despliegue | test_despliegue.py | ✔ OK | 5 pasaron, 0 salteadas, 0 fallaron. |
| P-diseno | test_diseno.py | ✔ OK | 24 pasaron, 0 salteadas, 0 fallaron. |
| P-evaluacion_int | test_evaluacion_interprete.py | ✔ OK | 3 pasaron, 0 salteadas, 0 fallaron. |
| P-frontend_sesio | test_frontend_sesion.py | ✔ OK | 5 pasaron, 0 salteadas, 0 fallaron. |
| P-geografia | test_geografia.py | ✔ OK | 12 pasaron, 0 salteadas, 0 fallaron. |
| P-modo_sin_ia | test_modo_sin_ia.py | ✔ OK | 30 pasaron, 0 salteadas, 0 fallaron. |
| P-privacidad | test_privacidad.py | ✔ OK | 6 pasaron, 0 salteadas, 0 fallaron. |
| P-rendimiento | test_rendimiento.py | ✔ OK | 4 pasaron, 0 salteadas, 0 fallaron. |
| P-seguridad_codi | test_seguridad_codigo.py | ✔ OK | 15 pasaron, 0 salteadas, 0 fallaron. |
| P-sesion | test_sesion.py | ✔ OK | 9 pasaron, 0 salteadas, 0 fallaron. |
| P-verificar_desp | test_verificar_despliegue.py | ✔ OK | 10 pasaron, 0 salteadas, 0 fallaron. |

## 4. Planilla de casos de prueba vs. pruebas reales

| ID | Verificación | Estado | Detalle |
|---|---|---|---|
| X-01 | 68 casos de prueba en la planilla | ✔ OK | 10 Manual - pendiente, 58 Pasó |
| X-02 | Lo que dice la planilla coincide con lo que pasó al correr las pruebas | ✔ OK | Cada caso «Pasó» tiene al menos una prueba que pasó ahora; cada caso «Escrita» tiene su prueba. |

## 5. Ciberseguridad

| ID | Verificación | Estado | Detalle |
|---|---|---|---|
| S-01 | Sin claves ni contraseñas escritas en el código | ✔ OK | 4 pruebas automáticas pasaron. |
| S-02 | Sin inyección SQL (consultas parametrizadas y límites acotados) | ✔ OK | 2 pruebas automáticas pasaron. |
| S-03 | Descargas confinadas a analytics/ (path traversal) | ✔ OK | 4 pruebas automáticas pasaron. |
| S-04 | CORS, errores sin detalles, rate limit, servidor local, frontend sin HTML crudo | ✔ OK | 5 pruebas automáticas pasaron. |
| S-05 | .env fuera de Git | ✔ OK | .gitignore incluye .env |
| S-06 | Clave de Gemini en backend/.env | ⚠ ADVERTENCIA | Hay una clave cargada en backend/.env: correcto para uso local, pero NO compartas este archivo ni el zip. |
| S-07 | Starlette sin las vulnerabilidades CVE-2026-48710 / 48818 | ✔ OK | requirements.txt pide starlette>=1.0.1 |
| S-08 | Vite actualizado (CVE-2026-112945, corregida en 8.2.4) | ✔ OK | Vite 8.3.8 |
| S-09 | package-lock.json coherente con package.json (npm ci reproducible) | ✔ OK | 13 dependencias directas, 165 paquetes en el lock. |
| S-10 | pip-audit (vulnerabilidades en paquetes de Python) | … NO EJECUTADO | No está instalado. Correr: pip install pip-audit  (setup.bat lo hace). |
| S-11 | npm audit (vulnerabilidades en paquetes de Node) | ⚠ ADVERTENCIA | 0 altas/críticas en producción; 5 solo en dependencias de desarrollo: @vitejs/plugin-react, fdir, picomatch, tinyglobby, vite. No hay versión corregida publicada todavía. |

## 6. Documentación vs. código real

| ID | Verificación | Estado | Detalle |
|---|---|---|---|
| O-01 | Los documentos vigentes solo mencionan archivos que existen | ✔ OK | 27 documentos revisados. |
| O-02 | Sin rastros de la versión anterior (Node/Express/SQLite) en la documentación vigente | ✔ OK | Ningún documento menciona el stack anterior. |
| O-03 | Sin copias viejas del código o de los documentos dentro del proyecto | ✔ OK | El proyecto contiene solo la versión vigente. |

## 7. Checklist de entrega (consignas del proyecto)

| ID | Verificación | Estado | Detalle |
|---|---|---|---|
| C-01 | Historias de usuario (mínimo 8) con criterios de aceptación, incluida una de IA | ✔ OK | 16 historias y 22 criterios de aceptación; HU-01 es la de IA (búsqueda en lenguaje natural). |
| C-02 | Metodología ágil elegida y explicada | ✔ OK | Kanban, WIP 3. |
| C-03 | Diagrama ER y de clases + wireframes + diagrama de integración de la IA | ✔ OK | Están en el PDF de diseño (secciones 5.1 a 5.9). La correspondencia con el código está en docs/diseno_sistema_seccion5.md. |
| C-04 | Pantallas / mockups | ✔ OK | Carpeta «Pantallas movil y web». |
| C-05 | Plan y resultados de pruebas, con casos específicos de IA | ✔ OK | Planilla de 39 casos + pruebas_automatizadas.md; los resultados salen de la sección 3 de este reporte. |
| C-06 | Tabla de herramientas de IA con las 5 etapas y análisis crítico escrito | ✔ OK | Completa. |
| C-06b | Registro de bugs encontrados y cómo se corrigieron (sección 7 de la consigna) | ✔ OK | 46 bugs registrados. |
| C-06c | Casos de prueba de la IA con la respuesta REAL obtenida y si fue adecuada (5 a 10 entradas, con un caso adversario) | ✔ OK | Último registro: resultados_ia_20261116_1924.md |
| C-06d | Tablero con las columnas mínimas (Backlog, Pendiente, En proceso, Finalizado) y tareas de IA identificables | ✔ OK | Columnas: Backlog, Pendiente, En proceso, Finalizado |
| C-07 | Capturas del tablero en 3 momentos distintos | ✋ MANUAL | No se puede verificar desde el código: subir las capturas de Trello. |
| C-08 | README con instrucciones para ejecutar, incluida la configuración de la IA | ✔ OK | Pasos de instalación, variable GEMINI_API_KEY y cómo arrancar. |
| C-09 | Al menos 4 funcionalidades implementadas y trazables a historias de usuario, una de ellas la IA operativa | ✔ OK | 15 historias implementadas (total o parcialmente); la de IA es HU-01. «Operativa con datos reales» se demuestra en vivo con Gemini. |
| C-10 | Commits organizados e incrementales | ✋ MANUAL | No hay carpeta .git en esta copia (copiá la tuya al proyecto) para contar los commits. |
| C-11 | Enlace al repositorio (GitHub/GitLab/Bitbucket) | ✋ MANUAL | No se puede verificar desde el código. |
| C-12 | Exposición oral: demostración en vivo, metodología, herramientas de IA, todos participan | ✋ MANUAL | Se prepara con este reporte y la demostración (restart.bat). |
