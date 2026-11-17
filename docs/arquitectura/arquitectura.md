# GastronomIA — Arquitectura

```
Usuario → Frontend (React + Vite, :5173) → Backend (FastAPI, :8001) ⇄ Gemini (function calling)
                                                  ↓
                                        PostgreSQL + PostGIS (71.343 lugares)
```

## Componentes
| Componente | Responsabilidad | Código |
|---|---|---|
| Interfaz | chat, exploración con filtros, ficha, perfil, favoritos | `frontend/src/App.tsx` |
| Backend (orquestador) | limpia la consulta, valida parámetros y respuesta, registra la conversación | `backend/main.py`, `orquestador.py`, `diseno.py` |
| Servicio de chat | ciclo con Gemini: la IA pide una búsqueda, el backend la ejecuta con SQL parametrizado y devuelve los resultados reales | `backend/chat_service.py`, `gemini_service.py` |
| Control de cuota | evita superar el límite del plan gratis; modo sin IA | `backend/cuota.py` |
| Endpoints del diseño | usuarios, restricciones, reseñas, mensajes | `backend/rutas_diseno.py` |
| Base de datos | 14 tablas del diseño (12 entidades + 2 tablas de unión) y la tabla `comercios` (ver `docs/diseno_sistema_seccion5.md`) | `database/schema.sql` (catálogo original), `backend/models*.py` |

## Decisiones
- **FastAPI + PostgreSQL/PostGIS:** consultas geográficas (cercanía) y búsqueda por texto sobre 71.343 lugares.
- **La IA nunca accede a la base:** solo recibe lo que el backend le devuelve; la auditoría lo verifica leyendo el código.
- **La respuesta de la IA se valida antes de mostrarse:** si inventa teléfonos, links, mails o locales, o promete seguridad absoluta, se reemplaza por una respuesta con datos reales.
- **Fallas de la IA:** 429, errores o respuestas vacías no rompen el sistema (mensaje claro o modo sin IA).

El diseño completo (ER en la p. 4, diagramas de clases en las pp. 5 y 20 a 25, wireframes —«Pantalla 1» a «Pantalla 5»— en las pp. 6 a 11, y diagrama de integración de la IA en las pp. 12 a 14) está en `docs/GastronomIA_Diseno_del_sistema_con_diagramas_UML.pdf`; su correspondencia con el código, en `docs/diseno_sistema_seccion5.md`.
