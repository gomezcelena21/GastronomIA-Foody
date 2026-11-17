# Ciberseguridad: auditoría y correcciones (5/11/2026)

Alcance: código de `backend/`, `frontend/`, scripts y archivos de configuración de GastronomIA. Método: lectura del código, revisión de `node_modules` contra `package-lock.json` y búsqueda de avisos publicados hasta el 4/11/2026.

## 1. Hallazgos en el código propio
| ID | Severidad | OWASP 2021 | Hallazgo | Corrección | Prueba automatizada |
|---|---|---|---|---|---|
| SEG-01 | Crítica | A02 Fallas criptográficas / exposición de secretos | Clave real de Gemini escrita en `.env.example` (se comparte con el zip) y en `.env` | Moldes con texto de relleno; `.env` fuera de Git | `SecretosEnElCodigo.test_sin_claves_de_api...` |
| SEG-02 | Alta | A01 Control de acceso roto | `/api/downloads/{ruta}` permitía salir de `analytics/` (p. ej. `../.env`) | `diseno.resolver_descarga()`: ruta confinada + extensiones permitidas | `DescargasSeguras` (8 rutas de ataque), `ApiSinBaseDeDatos.test_descargas...` |
| SEG-03 | Alta | A03 Inyección | `LIMIT {limit}` armado con un valor que decide la IA (inyección SQL vía prompt) | `LIMIT :limit` parametrizado + `normalizar_limite()`; parámetros de la IA limpiados | `InyeccionSQL` |
| SEG-04 | Alta | A02 / A05 | Contraseña de PostgreSQL escrita en `database.py` y 6 scripts | Se lee de `DATABASE_URL` / `PGPASSWORD` | `test_sin_contrasenas_de_bd_en_el_codigo` |
| SEG-05 | Media | A05 Configuración insegura | Se devolvían mensajes de excepción al cliente (`/health`, chat, herramientas) | Mensajes genéricos y registro en el servidor | `test_errores_sin_detalles_internos` |
| SEG-06 | Media | A04 Diseño inseguro | Sin rate limit ni tope de entradas (el README lo prometía) | 20 mensajes/min en chat, 30/min en escrituras; mensaje ≤ 1500; `session_id` validado; sesiones ≤ 200 | `ApiSinBaseDeDatos.test_rate_limit...`, `EntradasSeguras` |
| SEG-07 | Media | A05 | CORS con métodos y cabeceras `*` y credenciales | Solo `localhost/127.0.0.1:5173`, GET/POST/PUT | `test_cors_sin_comodines`, `test_cors_no_acepta_origenes_ajenos` |
| SEG-08 | Media | A04 | Estado del chat compartido entre pedidos simultáneos y sesión de BD ya cerrada | Lock por pedido y sesión de BD nueva en cada pedido | (revisión de código) |
| SEG-09 | Media | A04 / IA | La respuesta de la IA se mostraba sin validar (datos inventados, "100% seguro para celíacos") | `validar_respuesta_ia()` (teléfonos, links, mails y locales entre «» o negrita que no estén en la BD; garantías absolutas) + respuesta segura armada solo con datos reales; reglas 11-17 en el prompt. Límite: no detecta un nombre inventado escrito en texto libre sin «» | `ValidarRespuestaIA`, `RespuestaSegura` |
| SEG-10 | Baja | A05 | `.gitignore` incompleto | Se agregan `.env` en subcarpetas, logs, `*.db-wal` | `test_gitignore_protege_el_env` |

Otras correcciones: `/api/restaurants/nearby` era inalcanzable (la ruta `{id}` lo capturaba); ahora `{id:int}`.

## 2. Cadena de suministro (ataques recientes a npm y PyPI)
- Contexto: gusano ChainDrop/Shai-Hulud (agosto 2026, keyv y cacheable), tensorlake 0.5.144 comprometido (octubre), LiteLLM 1.107.0 con puerta trasera (21/10), variante "Hades" en PyPI (junio), paquetes falsos con nombres parecidos a Flask, Requests y NumPy.
- Resultado para este proyecto: las dependencias del frontend (react, react-dom, react-markdown, chart.js, react-chartjs-2, vite, typescript, oxlint) no coinciden con ningún paquete afectado; los 119 paquetes de `node_modules` tenían exactamente las versiones del `package-lock.json`; solo `husky` y `patch-package` tienen scripts de instalación (normales, de desarrollo). El backend usa `google-genai`, `fastapi`, `sqlalchemy`, `geoalchemy2`, `requests`, etc.; ninguno figura en los incidentes consultados.
- Prevención: `npm ci` (instala lo que dice el lockfile), `requirements.txt` con nombres exactos, `npm audit` y `pip-audit` (los corre `setup.bat`).

## 3. Vulnerabilidades de componentes
| Componente | Aviso | Estado |
|---|---|---|
| Vite 8.2.2 | CVE-2026-112945 (baja, corregida en 8.2.4) y otros avisos moderados de octubre del servidor de desarrollo | `setup.bat` ejecuta `npm update vite`. Solo aplica si se expone el servidor a la red (`--host`); no es el caso |
| Starlette (FastAPI) | CVE-2026-48710 (Host malformado, corregido en 1.0.1); CVE-2026-48818 (StaticFiles en Windows, corregido en 1.1.0) | `requirements.txt` pide `starlette>=1.0.1`. El proyecto no usa StaticFiles |
| `google-genai` | Reemplaza al obsoleto `google-generativeai` | Migrado: el backend usa el SDK oficial y `requirements.lock` fija la versión |

## 4. Pendientes (decisión o acción del equipo)
1. **Revocar la clave de Gemini anterior** y generar una nueva (si el repo estuvo en GitHub, la clave sigue en el historial aunque se borre el archivo).
2. Agregar autenticación antes de publicar el sistema: hoy `GET /api/usuarios/{id}` devuelve el email sin login. El backend escucha solo en 127.0.0.1.
3. Migrar el SDK de Gemini.
4. En la documentación de `analytics/` figura "cambiar PostgreSQL de trust a password/md5": confirmar que la base exige contraseña.
5. La IA puede ser manipulada con prompt injection; se reduce (reglas del prompt, parámetros acotados, sin acceso directo a la BD, validación de la salida) pero no se elimina.
6. Se eliminaron `backend_old/` y `docs_tpi_backup/` (copias viejas con el mismo código vulnerable).
