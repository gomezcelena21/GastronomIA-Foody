# GastronomIA

Asistente conversacional para buscar, filtrar y elegir establecimientos gastronómicos de toda la Argentina (71.343 lugares de la base unificada), con foco en restricciones alimentarias (sin TACC, vegetariano, vegano). La IA (Gemini) **interpreta y redacta**, pero la fuente de verdad es la base de datos: el backend valida la respuesta antes de mostrarla.

Proyecto sin fines de lucro: cualquiera puede usarlo gratis, con límites diarios, y no hay ningún plan de pago. Los comercios de todo el país pueden registrarse con Google y sumar su local al catálogo (un administrador los aprueba).

## Arquitectura
```
Usuario → Frontend (React + Vite) → Backend (FastAPI) ⇄ Gemini (function calling)
                                          ↓
                                PostgreSQL + PostGIS
```
Flujo de 8 etapas del diseño (PDF "Diseño del sistema", Sección 5): entrada → preparación de la solicitud → la IA devuelve parámetros → validación de cobertura (toda la Argentina; rechaza otros países) → consulta a la BD → resultados reales a la IA → respuesta → **validación del backend** (bloquea locales, teléfonos o links inventados y garantías absolutas) → respuesta al usuario.
Correspondencia completa entre el PDF y el código: `docs/diseno_sistema_seccion5.md`.

## Tecnologías
Frontend: React 19, Vite, TypeScript | Backend: Python, FastAPI, SQLAlchemy | IA: Gemini (SDK oficial `google-genai`) | DB: PostgreSQL + PostGIS | ETL/análisis: Python.

## Instalación (Windows)
1. Instalá Python 3.10+, Node.js y PostgreSQL con PostGIS. Si todavía no tenés la base cargada, creá una base vacía, definí `DATABASE_URL` y corré `python scripts\cargar_base_nube.py`: aplica `database/schema.sql` e carga los 71.343 lugares de `data/dataset_unificado_ARGENTINA.csv` (con provincia, región, partido y zona) en bloques (pide confirmación y no borra nada si la base ya tiene datos).
2. Abrí `backend\.env` y pegá tu **clave nueva** de Gemini en `GEMINI_API_KEY` (y revisá `DATABASE_URL`). Hay un molde en `backend\.env.example`. Para el login completá también `GOOGLE_CLIENT_ID` y `SESSION_SECRET` (ver `docs/despliegue_y_login.md`) y creá `frontend\.env` a partir de `frontend\.env.example`.
3. Doble clic en **`setup.bat`** (instala dependencias de Python y Node, actualiza Vite y corre las auditorías).
4. (Opcional, una vez) `python scripts\poblar_diseno.py` carga las tablas nuevas del diseño con los datos existentes.
5. Doble clic en **`restart.bat`** → http://localhost:5173

Variables de `backend/.env`: `GEMINI_API_KEY`, `GEMINI_MODEL`, `DATABASE_URL`, `PORT`, `VALORACIONES_CON_IA` (0 por defecto), `GEMINI_RPM` (10), `GEMINI_MAX_ESPERA` (20), `GEMINI_TIMEOUT` (12) y `OPTIMIZAR_AL_INICIAR` (1). Si el plan gratis de Gemini se agota o no contesta a tiempo, el chat responde en modo sin IA: ver `docs/cuota_gemini.md`. Las demás variables (límites diarios, `ADMIN_EMAILS`, `COMERCIOS_AUTOAPROBADOS`, `FRONTEND_ORIGINS`, etc.) están comentadas en `backend/.env.example` y `.env.produccion.example`.
Los scripts nuevos de `scripts/` leen `DATABASE_URL` de `backend/.env` o del entorno; si no está, usan `PGPASSWORD` (y opcionalmente `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`).

## Publicarlo
- **Gratis y sin tarjeta (recomendado para este proyecto):** frontend en **Vercel**, backend en **Render** (servicio web gratis, con un monitor que visita `/ping` para que no se duerma) y base en **Neon**. Paso a paso: `deploy/GUIA_GRATIS_VERCEL_RENDER_NEON.md`. La base se carga una sola vez con `scripts/cargar_base_nube.py`.
- **Servidor propio con Docker** (Oracle Cloud u otro): `docker-compose.yml` + Caddy con HTTPS automático, backups y logs rotados. Ver `deploy/README.md`. En este modo solo Caddy (80/443) es público: el backend no publica el puerto 8000 al exterior.
- `/ping` responde sin consultar la base (sirve para monitoreo); `/health` además comprueba la conexión a la base.

## Configuración de la IA
- **Proveedor y modelo:** Gemini, con el SDK oficial `google-genai`. El modelo se elige con `GEMINI_MODEL` (el valor por defecto está en `backend/gemini_service.py`).
- **Clave:** `GEMINI_API_KEY` en `backend/.env`. Ese archivo nunca se sube a Git; el molde está en `backend/.env.example`. Sin clave, el chat funciona igual en modo sin IA.
- **Prompt del sistema:** constante `SYSTEM_PROMPT` en `backend/gemini_service.py`. Define a Foody y su regla principal: nunca garantiza que un lugar sea apto para una restricción alimentaria y recomienda contactar al local.
- **Function calling:** la IA no consulta la base de datos. Interpreta el mensaje y devuelve parámetros (zona, tipo de comida, restricciones, presupuesto); el backend los valida y consulta PostgreSQL con SQL parametrizado.
- **Validación de la respuesta:** antes de mostrarla, el backend bloquea locales, teléfonos o links inventados y garantías absolutas (`backend/diseno.py`, `RespuestaSegura`).
- **Límites y respaldo:** `GEMINI_RPM` (consultas por minuto), `GEMINI_MAX_ESPERA` y `GEMINI_TIMEOUT` (segundos). Si el plan gratuito se agota o no responde, el chat pasa al proveedor de respaldo (`RESPALDO_API_KEY`, opcional, Groq gratis) y, si tampoco puede, al modo sin IA con la red neuronal propia (ver `docs/cuota_gemini.md` y `docs/pruebas/modelo_propio.md`).
- **Probar la IA:** `python scripts\probar_ia.py` con el backend en marcha (10 casos, tres de ellos adversarios). El resultado queda en `docs/pruebas/resultados_ia_<fecha>.md`.
- **Registro del uso de IA durante el proyecto:** `docs/uso_ia.md`.

## Modo sin IA
Cuando el plan gratis de Gemini se agota o no contesta, Foody sigue respondiendo con reglas y plantillas, directo desde la base: saluda, entiende provincia, ciudad o barrio, tipo de comida y restricciones, retoma la conversación («¿y sin TACC?»), pide el dato que falta y, si no hay resultados, prueba sin el tipo de comida o sin la zona. **Nunca afloja una restricción alimentaria** y siempre muestra la fuente. Detalle en `docs/cuota_gemini.md`.

## Pruebas
```
python -m unittest discover -s tests -v          # 242 pruebas (con PostgreSQL y PRUEBAS_CON_BD=1 corren todas; sin base se saltean 8)
python -m unittest tests.test_api_diseno -v       # API (necesita pip install -r backend/requirements.txt)
set PRUEBAS_CON_BD=1 && python -m unittest tests.test_api_diseno -v   # con PostgreSQL
cd frontend && npm run build && npx playwright test                    # E2E de interfaz (API simulada)
```

Documentación de las pruebas (`docs/pruebas/`): `plan_de_pruebas.md` (estrategia, niveles, alfa y beta), `caja_blanca.md` (grafos de flujo y V(G)),
`caja_negra.md` (particiones y valores límite), `evaluacion_interprete.md` (evaluación con ejemplos), `romper_a_proposito.md` (prueba de las pruebas),
`registro_de_bugs.md` y la planilla `casos_de_prueba_GastronomIA.xlsx` (68 casos). Con `pytest` también corren (`pip install pytest`, luego `pytest tests`).
Detalle y trazabilidad (historia de usuario ↔ prueba): `docs/pruebas/pruebas_automatizadas.md`. Planilla de 68 casos: `docs/pruebas/casos_de_prueba_GastronomIA.xlsx`. Casos de la IA con la API real: `python scripts\probar_ia.py` (ver `docs/pruebas/casos_ia.md`). Bugs: `docs/pruebas/registro_de_bugs.md`.

La integración continua está en `.github/workflows/ci.yml`: backend con PostGIS real, build de frontend, Playwright e imagen Docker.

## Datos y operación
- **Conversión nacional**: `python scripts\convertir_base_unificada.py RUTA.xlsx` (descarta provincias no argentinas y coordenadas fuera del país).
- **Carga**: `python scripts\cargar_base_unificada.py --forzar` (conserva los comercios registrados).
- **Validación geográfica**: `python scripts\validar_base_argentina.py --db` (agregá `--limpiar-csv` o `--desactivar` para corregir).
- **Auditoría por muestreo**: `python scripts\auditar_muestra.py` (200 casos, semilla fija; reporte en `docs/pruebas/`).
- **Geocodificación**: `python scripts\geocodificar_ba_data.py --dry-run --limit 10` (Nominatim, 1 req/s, caché).
- **Ratings/precios** (opcional, Google Places): `python scripts\enriquecer_google_places.py --dry-run`.
- **Menús**: plantilla `data/plantillas/menus.csv` y `scripts/importar_menus_csv.py`.
- **Sin TACC**: `scripts/verificar_sin_tacc.py` genera el reporte y `scripts/importar_sin_tacc_csv.py` carga lo confirmado.
- **Backups/monitoreo/despliegue**: ver `deploy/README.md`.
- **Páginas legales**: `/privacidad` y `/terminos` (correo configurable con `VITE_CONTACT_EMAIL`).

## Auditoría automática
Doble clic en **`AUDITORIA.bat`** (o `python auditoria/auditar.py`): comprueba que el diseño del PDF está en el código, audita las 16 historias de usuario, corre todas las pruebas, verifica la planilla de casos, revisa ciberseguridad y documentación, y abre un reporte HTML. Ver `auditoria/LEEME.md`.

## Seguridad
Hallazgos, correcciones y pendientes: `docs/seguridad_ciberseguridad.md`. En resumen: SQL parametrizado, validación de parámetros de la IA, rate limit en el chat, descargas confinadas a `analytics/`, CORS acotado, errores sin detalles internos, sin contraseñas en el código y `.env` fuera de Git. Además: el backend no se publica directo a internet, y los textos que cargan los comercios se tratan como datos (no como órdenes para la IA).
**Uso sin registro y login opcional con Google** (`sesion.py`, `seguridad.py`, `docs/despliegue_y_login.md`): el usuario gratuito puede usar Foody sin registrarse (cupo diario menor, sin historial); con Google el cupo es mayor y se guarda el historial, sin contraseñas guardadas y con sesión firmada que vence a las 12 horas. Con cuenta se pueden tener **varias conversaciones** («Nuevo chat»): cada una conserva su propio contexto y se puede volver a abrir desde la lista, siempre dentro de la misma cuenta. El chat solo habla de gastronomía y bloquea datos personales. Revisión completa en `docs/revision_seguridad.md`.

## Estructura
```
├── backend/   FastAPI: main.py, chat_service.py, orquestador.py, diseno.py, rutas_diseno.py, models*.py
├── frontend/  React + Vite (App.tsx)
├── tests/     pruebas automatizadas (unittest)
├── auditoria/ auditoría automática (auditar.py) y su reporte
├── AUDITORIA.bat  setup.bat  restart.bat  start.bat
├── docs/      requisitos, casos de uso, historias de usuario, arquitectura, diseño, seguridad, pruebas, uso de IA
├── scripts/ etl/ analytics/  carga de datos y análisis
```

## Limitaciones
Dietéticos: solo unos pocos cientos de lugares tienen dato de restricción y ninguno está verificado con el local (la información alimentaria nunca se presenta como garantía). Unos 2.700 lugares de BA Data no tienen coordenadas. Ratings y precios requieren una fuente externa o carga manual. Cobertura de todo el país (solo Argentina). Cada lugar tiene su jerarquía región > partido > zona (CABA; GBA con 26 partidos agrupados en GBA Norte, Oeste y Sur; en el interior, la provincia) en las columnas `region`, `district` y `zone_macro`; 1.917 lugares quedan como «Sin confirmar» y 96 de GBA sin partido.

## Licencia
Proyecto universitario sin fines de lucro. Datos: OpenStreetMap (ODbL) y BA Data (CC-BY-2.5-AR).
