# Usuarios, login con Google, comercios y despliegue

## Quién puede hacer qué
| Quién | Cómo entra | Qué puede hacer hoy |
|-------|-----------|---------------------|
| **Invitado** (usuario gratuito) | "Continuar sin registrarme" | Usar Foody y explorar, con un cupo diario menor (`ANONIMOS_POR_DIA`, por IP) y sin historial guardado |
| **Usuario con cuenta** | Google | Todo lo anterior con cupo mayor (`CONSULTAS_POR_DIA`), historial que se conserva aunque la sesión venza, y perfil con sus restricciones |
| **Comercio o emprendimiento** (con o sin local físico) | Google, y después Perfil → «Mi comercio» (quien ya inició sesión entra directo al chat) | Completar el formulario: nombre, rubros (hasta 3), modalidad, provincia (CABA o cualquiera de las 23 provincias), barrio o localidad, dirección si tiene local, Instagram o sitio web si es online, sin TACC y declaración de responsabilidad. Queda **pendiente** hasta que un administrador lo aprueba; al aprobarse, **Foody empieza a recomendarlo** |
| **Premium** (personas y comercios) | — | **Próximamente**: solo hay un vistazo en la interfaz; no se cobra ni se activa nada |

Al **aprobarse**, el comercio se publica en el catálogo `restaurants` (fuente «Registro de comercios GastronomIA», confianza «declarado_comercio»), que es lo que consulta Foody. Si el comercio edita sus datos, vuelve a «pendiente» y sale del catálogo hasta una nueva aprobación. Foody lo indica como dato cargado por el propio comercio y sugiere confirmar.

**Sobre la antigüedad de 6 meses:** Google no le informa a las aplicaciones cuándo se creó una cuenta, así que esa regla no se puede verificar automáticamente. Se cubre con la declaración del formulario, el enlace de Instagram o sitio web y la **revisión manual del administrador**, que debe comprobar la antigüedad antes de aprobar.

## Cómo funciona el login
1. El navegador muestra el botón oficial de Google y obtiene un token de identidad.
2. `POST /api/auth/google`: el backend (`sesion.py`) lo valida con la librería oficial (firma, vigencia, que sea para **este** `GOOGLE_CLIENT_ID` y correo verificado).
3. Devuelve un token de sesión propio, firmado con `SESSION_SECRET`, que vence a las 12 horas.
4. El usuario es la cuenta de Google: se crea en el primer ingreso y después se reutiliza. Cada conversación queda guardada en la base asociada a esa cuenta; con «Nuevo chat» se empieza otra y la lista permite volver a cualquiera de ellas (`/api/chat/conversaciones` y `/api/chat/historial?chat_id=…`).

**No se guardan contraseñas.** La identidad sale siempre del token firmado, nunca de lo que mande el navegador.

## 1. Crear el Client ID de Google (una vez)
1. Entrá a https://console.cloud.google.com y creá un proyecto.
2. "APIs y servicios" > "Pantalla de consentimiento de OAuth": tipo Externo; completá nombre y correo. En modo "Prueba", agregá como usuarios de prueba los correos que van a ingresar (el tuyo, compañeros y profesor).
3. "Credenciales" > "Crear credenciales" > "ID de cliente de OAuth" > **Aplicación web**.
4. En "Orígenes autorizados de JavaScript" agregá `http://localhost:5173` y, al publicar, `https://TU-APP.vercel.app`.
5. Copiá el Client ID (termina en `.apps.googleusercontent.com`). No necesitás el secreto del cliente.

## 2. Variables de entorno
Backend (`backend/.env`, ver `backend/.env.example`): `GOOGLE_CLIENT_ID`, `SESSION_SECRET` (32+ caracteres; generala con `python -c "import secrets; print(secrets.token_urlsafe(48))"`), `FRONTEND_ORIGINS`, `CONSULTAS_POR_DIA`, `ANONIMOS_POR_DIA`, `ANONIMOS_POR_DIA_GLOBAL`, `ADMIN_EMAILS` (tu correo de Google, para aprobar comercios), `COMERCIOS_AUTOAPROBADOS` (0 normal; 1 solo para pruebas o demos: los comercios se aprueban solos), `ENTORNO`, además de `GEMINI_API_KEY` y `DATABASE_URL`.

Frontend (`frontend/.env`, ver `frontend/.env.example`): `VITE_API_URL` y `VITE_GOOGLE_CLIENT_ID`. Son datos públicos: **nunca** va ahí la clave de Gemini.

## 3. Probar en local
`restart.bat`, abrir http://localhost:5173 (página principal) y entrar con "Hablar con Foody". La primera vez que arranca el backend crea la tabla `comercios`; para correr las pruebas con base de datos (`PRUEBAS_CON_BD=1`) conviene haber iniciado el backend una vez.

## 4. Publicar
Guía completa y comparación de opciones: **`deploy/README.md`**.

- **Frontend (Vercel):** carpeta `frontend`, framework Vite. `vercel.json` incluye la redirección de `/chat` y cabeceras de seguridad. Cargá `VITE_API_URL` (URL pública del backend) y `VITE_GOOGLE_CLIENT_ID`.
- **Backend (servidor que NO se duerme):** se recomienda **Oracle Cloud Always Free** (2 OCPU ARM / 12 GB, gratis para siempre) con el `Dockerfile` y `docker-compose.yml` de la raíz. También sirve cualquier VPS o Fly.io (~US$ 2–4/mes). Evitá los planes gratuitos que duermen por inactividad.
- **Base de datos:** PostgreSQL con PostGIS. Dos caminos:
  - en la misma VM con el servicio `db` del `docker-compose.yml` (PostGIS incluido), o
  - administrada con **Neon Free**: plan gratuito permanente, sin pausa por inactividad y con PostGIS.
  - Render Free **no** sirve para esto: el servicio se duerme y la base gratuita vence a los 30 días.
- Poné `ENTORNO=produccion` para ocultar `/docs`. `FRONTEND_ORIGINS` debe ser exactamente el dominio de Vercel (con `https://`, sin barra final).
- `run_backend.py` escucha solo en `127.0.0.1` (uso local).

## Pendientes conocidos
- Verificación de documentos del comercio y detección de duplicados.
- Orden por «Destacado» (solo tendría sentido con Premium, que no existe).
- Premium (personas y comercios): solo existe como aviso de «Próximamente». El proyecto no recibe ni procesa dinero.
- Menú del comercio y su límite en el plan gratuito: sin definir.
- Reseñas con moderación y reporte de información incorrecta.
- El historial restaura el texto de la conversación, no las tarjetas de los lugares.
- Las conversaciones no se pueden borrar desde la interfaz: «Nuevo chat» abre una nueva y las anteriores quedan disponibles en la lista. El contexto de Gemini de cada hilo se descarta a los 30 días sin actividad.
- Los cupos diarios y las sesiones se guardan en PostgreSQL (`cuotas_diarias` y `sesiones_gemini`). Si la base falla, el backend vuelve al contador en memoria; el chat sigue funcionando.
