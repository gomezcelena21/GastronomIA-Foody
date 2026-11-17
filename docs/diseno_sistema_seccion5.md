# Diseño del sistema (Sección 5) → implementación

Documento fuente: `docs/GastronomIA_Diseno_del_sistema_con_diagramas_UML.pdf`.
Este archivo muestra dónde vive en el código cada elemento del diseño. Lo existente no se reemplazó: se sumó encima.

## 1. Arquitectura en cuatro componentes
| Componente | Código |
|---|---|
| Interfaz | `frontend/src/App.tsx` |
| Backend (reglas, BD, coordinación con la IA) | `backend/main.py`, `orquestador.py`, `diseno.py`, `rutas_diseno.py` |
| Base de datos | PostgreSQL + PostGIS (`backend/models.py`, `models_diseno.py`) |
| IA | Gemini (`backend/gemini_service.py`, `ComponenteIA` en `orquestador.py`) |

## 2. Base de datos: 12 entidades + 2 tablas de unión = 14 tablas del diseño
| Entidad del PDF | Tabla / clase |
|---|---|
| Establecimiento | `restaurants` (`models.Restaurant`, ya existía) |
| Fuente | `sources` (`models.Source`, ya existía) |
| Usuario | `usuarios` |
| RestriccionAlimentaria | `restricciones_alimentarias` |
| UsuarioRestriccion | `usuario_restriccion` |
| Preferencia | `preferencias` |
| HistorialPreferencia | `historial_preferencias` |
| Conversacion | `conversaciones` |
| Mensaje | `mensajes` |
| Recomendacion | `recomendaciones` |
| Resena | `resenas` |
| Valoracion | `valoraciones` |
| (tabla de unión del ER) EstablecimientoRestriccion | `establecimiento_restriccion` (con `nivel_informacion`: declarado / inferido / no_verificado) |
| (tabla de unión del ER) EstablecimientoFuente | `establecimiento_fuente` |

Además de estas 14, el sistema tiene la tabla `comercios` (alta de locales por sus dueños) y, en el esquema original, `restaurant_features`, `menus` y `query_logs`. `database/schema.sql` crea el catálogo original (`restaurants`, `sources`, etc.); las tablas del diseño se crean solas al iniciar el backend.
Las tablas nuevas se crean solas al iniciar el backend. `python scripts/poblar_diseno.py` las completa con los datos existentes.
Regla del diseño: una característica alimentaria **nunca** es una certificación absoluta → `nivel_informacion` + advertencia en la ficha.

## 3. Endpoints (9)
| Método | Endpoint | HU | Dónde |
|---|---|---|---|
| POST | `/api/chat` | 01, 06, 08, 09, 16 | `main.py` → `OrquestadorBackend.procesar_consulta` |
| GET | `/api/establecimientos` | 01, 09, 10 | `main.py` (alias de `/api/restaurants`) |
| GET | `/api/establecimientos/{id}` | 02, 04, 05, 15 | `main.py` (alias; suma `advertencia_alimentaria` y fuente) |
| GET | `/api/restricciones` | 02, 09 | `rutas_diseno.py` |
| POST | `/api/usuarios` | 11 | `rutas_diseno.py` |
| GET | `/api/usuarios/{id}` | 11, 12 | `rutas_diseno.py` |
| PUT | `/api/usuarios/{id}` | 10, 11, 12, 14 | `rutas_diseno.py` |
| GET | `/api/conversaciones/{id}/mensajes` | 06, 16 | `rutas_diseno.py` |
| POST | `/api/resenas` | 13 | `rutas_diseno.py` |

## 4. Métodos del sistema (17)
**Backend (5)** — clase `OrquestadorBackend` (`orquestador.py`)
| Método del PDF | Implementación |
|---|---|
| procesarConsulta() | `procesar_consulta()` |
| prepararSolicitudIA() | `preparar_solicitud_ia()` (agrega restricciones y preferencias del usuario) |
| validarParametros() | `diseno.validar_parametros()` (cobertura de toda la Argentina; rechaza otros países), llamada dentro de `ChatService._search_restaurants` |
| consultarBaseDeDatos() | `ChatService._search_restaurants()` (SQL parametrizado) |
| validarRespuestaIA() | `diseno.validar_respuesta_ia()` (bloquea teléfonos, links y mails que no están en la BD, locales citados entre «» que no están en los resultados y garantías absolutas) |

**IA (3)** — `ComponenteIA` y Gemini
| Método del PDF | Implementación |
|---|---|
| interpretarConsulta() | `ComponenteIA.interpretar_consulta()` (reglas, modo sin IA). Con Gemini decide los parámetros el modelo (function calling) dentro de `ChatService.send_message` |
| generarRespuesta() | `ComponenteIA.generar_respuesta()` (reglas, con el motivo de cada recomendación, HU-16). Con Gemini redacta el modelo con los resultados reales que le devuelve el backend |
| extraerValoraciones() | `ComponenteIA.extraer_valoraciones()` (reglas simples; con `VALORACIONES_CON_IA=1` usa Gemini y filtra su salida) |

Con Gemini, interpretar y redactar ocurren en el mismo ciclo de function calling; las versiones por reglas de `ComponenteIA` son las que usa el modo sin IA (cuando se agota la cuota). El comportamiento del diseño se mantiene: la IA devuelve parámetros, el backend consulta la BD y la IA nunca la toca (la auditoría lo verifica leyendo el código: D-06).

## 5. Flujo de 8 etapas y escenarios alternativos
| Etapa | Dónde |
|---|---|
| 1 Entrada | `App.tsx` → `POST /api/chat` |
| 2 Preparación | `preparar_solicitud_ia` |
| 3 La IA devuelve parámetros | Gemini (function calling) |
| 4 Consulta a la BD | `_search_restaurants` (+ `validar_parametros`) |
| 5 Resultados reales a la IA | `send_message` |
| 6 Generación de la respuesta | Gemini |
| 7 Validación del backend | `validar_respuesta_ia`; si falla se usa `construir_respuesta_segura` (solo datos de la BD) |
| 8 Respuesta | `procesar_consulta` (devuelve `validada: true/false`) |

| Escenario | Respuesta del sistema | Implementación |
|---|---|---|
| A. Consulta interpretada | Recomendaciones | flujo normal |
| B. No interpretable | Filtros manuales | pestaña Explorar (filtros) |
| C. Sin resultados | Flexibilizar criterios | regla 15 del prompt y `construir_respuesta_segura([])` |
| D. Fuera de cobertura | Informa que solo hay datos de Argentina, sin recomendar | `validar_parametros` + regla 12 del prompt |
| E. Restricción alimentaria | Advertencia y contacto | `advertencia_alimentaria()` en la ficha |

## 6. Interfaz: cinco pantallas
| Pantalla del PDF | Código |
|---|---|
| Inicio / búsqueda | buscador del encabezado + pestaña Explorar (filtros) |
| Conversación | pestaña Chat |
| Resultados | tarjetas (muestran fuente) |
| Ficha | `Ficha` en `App.tsx` (contacto, fuente, advertencia alimentaria, "¿Por qué te lo recomendamos?") |
| Perfil | pestaña Perfil (se sincroniza con `/api/usuarios`) |

## 7. Estado real y qué NO está cubierto
El estado de cada historia (implementada / parcial / no implementada) lo calcula la auditoría automática: `AUDITORIA.bat`.

- Las 16 historias de usuario están en `docs/historias-usuario/historias_de_usuario.md`. HU-15 (feedback proactivo) no está implementada; HU-08, 09, 10, 13 y 14 tienen límites declarados en la auditoría.
- `HistorialPreferencia` se registra al crear/actualizar el perfil; todavía no se usa para personalizar recomendaciones (HU-14, "prevista").
- Reseñas: hay endpoint, pero el frontend aún no tiene el formulario para escribirlas.
- El diseño no incluye login: ver `docs/seguridad_ciberseguridad.md`.
- No pude ejecutar el backend con PostgreSQL ni con Gemini en el entorno donde se armó esta versión; ver `docs/pruebas/pruebas_automatizadas.md` para lo que sí se probó.
