# GastronomIA — Metodología Kanban

Se eligió Kanban por la necesidad de un flujo continuo y flexible: hay tareas de investigación de datos abiertos y ajustes iterativos de la integración con la API del modelo de lenguaje.

## Tablero
Trello: https://trello.com/invite/b/6ab0839a3d9448ad8b01a0fc/ATTI224ed44bda5871a04d1b02af132fe62dA2EB4ABD/proyecto-bot-gastronomia

| Columna | Contenido |
|---|---|
| **Backlog** | historias de usuario y requerimientos técnicos |
| **Pendiente** | tareas priorizadas, desglosadas y listas para tomar |
| **En proceso** | tareas en desarrollo (límite WIP: 3) |
| **Test** | validación: ¿funciona el código? ¿las respuestas de la IA respetan las reglas (por ejemplo, recomendar contactar al local ante celiaquía)? |
| **Finalizado** | tareas integradas y operativas |

Las tareas de la funcionalidad de IA se identifican con una etiqueta propia.

## Límite WIP
3 tareas en «En proceso» (ajustable según los integrantes). Al llegar al límite, el equipo colabora para destrabar una tarea antes de tomar otra.

## Roles (auto-organizados)
Extracción y limpieza de datos públicos · integración y ajuste del prompt de la API · interfaz conversacional · pruebas de calidad (QA) sobre las respuestas de la IA.

| Rol | Integrante | Qué hizo en el proyecto |
|---|---|---|
| Extracción y limpieza de datos | (completar con el nombre) | (completar) |
| Integración y ajuste del prompt de la API | (completar con el nombre) | (completar) |
| Interfaz conversacional | (completar con el nombre) | (completar) |
| Pruebas de calidad (QA) | (completar con el nombre) | (completar) |

## Cómo se aplica Kanban en el proyecto
- **Flujo:** cada historia de usuario (`docs/historias-usuario/`) se convierte en tareas del tablero y avanza de izquierda a derecha: Backlog → Pendiente → En proceso → Test → Finalizado.
- **Límite WIP de 3:** nadie toma una tarea nueva si ya hay tres en proceso; el equipo primero destraba una.
- **Criterio de avance:** una tarea pasa a «Test» cuando cumple los criterios de aceptación de su historia y a «Finalizado» cuando sus pruebas (`docs/pruebas/plan_de_pruebas.md`) pasan y cumple la Definition of Done.
- **Defectos:** cada bug encontrado (`docs/pruebas/registro_de_bugs.md`) vuelve al tablero como una tarjeta hasta quedar corregido y probado de nuevo.
- **Etiqueta de IA:** las tareas de la funcionalidad de IA llevan una etiqueta propia para poder rastrearlas.

## Definition of Done
1. El código funciona sin errores críticos y está en el repositorio compartido (Git).
2. Si maneja datos, provienen de fuentes oficiales (nacionales, provinciales o municipales) u OpenStreetMap.
3. Si es de IA: responde en lenguaje natural y cumple la regla inquebrantable (nunca asegurar aptitud alimentaria al 100 % y dar teléfono/web de contacto).

## Evidencia pendiente
La consigna pide capturas del tablero en **al menos tres momentos distintos** del proyecto. No se pueden generar desde el código: hay que sacarlas del Trello.
Guardalas en `docs/metodologia/capturas_tablero/` (ver el `LEEME.md` de esa carpeta) y completá esta tabla con lo que realmente muestran:

| Momento | Fecha de la captura | Archivo | Qué muestra |
|---|---|---|---|
| 1 | (completar) | (completar) | (completar) |
| 2 | (completar) | (completar) | (completar) |
| 3 | (completar) | (completar) | (completar) |
