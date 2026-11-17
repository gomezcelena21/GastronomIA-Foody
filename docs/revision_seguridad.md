# Revisión de seguridad (noviembre 2026)

Revisión del código del backend y del frontend antes del despliegue. Estado: **corregido**, **mitigado** o **pendiente**.

| # | Hallazgo | Riesgo | Estado |
|---|----------|--------|--------|
| 1 | El inicio de sesión era una pantalla falsa: cualquiera "entraba" con el botón de Google | Alto | Corregido: login real con Google; el servidor verifica firma, vigencia, audiencia y correo verificado (`sesion.py`) |
| 2 | `/api/conversaciones/{id}/mensajes` devolvía la conversación de cualquier persona con solo cambiar el número | Alto | Corregido: exige sesión y solo muestra conversaciones propias |
| 3 | `/api/usuarios` permitía crear usuarios con cualquier correo y leer o modificar el perfil de cualquier `id` | Alto | Corregido: exige sesión, el perfil es el de la cuenta de Google y el correo no se puede cambiar |
| 4 | El chat aceptaba el `id_usuario` que mandaba el navegador | Alto | Corregido: con cuenta, la identidad sale solo del token firmado; el invitado no tiene identidad guardada |
| 5 | Chat sin límite por persona (podía agotar la cuota de Gemini) | Medio | Corregido: cupo diario por cuenta, cupo menor por IP para invitados y tope general diario de invitados, además del límite por minuto |
| 6 | Se podían escribir datos personales en el chat y llegaban a la IA y al historial | Medio | Corregido: se bloquean email, teléfono, documento, tarjeta, CBU y contraseñas antes de llegar a la IA |
| 7 | La IA podía responder cualquier tema (código, cuentos, tareas) | Medio | Mitigado: filtro por reglas + reglas 18 y 19 del prompt. Ningún filtro de IA es perfecto |
| 8 | Datos de ejemplo con nombre y correo ficticios en el perfil inicial | Bajo | Corregido: el perfil toma los datos de Google; al cambiar de cuenta se borran favoritos y guardados locales |
| 9 | CORS fijo a `localhost` | Medio | Corregido: `FRONTEND_ORIGINS` por variable de entorno |
| 10 | Sin cabeceras de seguridad ni protección de caché en datos personales | Medio | Corregido: `nosniff`, `X-Frame-Options`, `Referrer-Policy`, HSTS y `Cache-Control: no-store` |
| 11 | `/docs` y `/openapi.json` públicos en producción | Bajo | Corregido: se ocultan con `ENTORNO=produccion` |
| 12 | Descarga de archivos (`/api/downloads`) | Medio | Ya corregido antes (`resolver_descarga` no sale de `analytics`), con prueba |
| 13 | Consultas SQL | Bajo | Sin hallazgos: parámetros y `normalizar_limite` |
| 14 | Registro de comercios y posibles estafas | Medio | Controlado: solo con sesión, cada cuenta toca solo su comercio, textos sin datos personales, declaración de responsabilidad, enlace de presencia online, revisión manual antes de publicar y posibilidad de suspender. La antigüedad de 6 meses no se puede verificar automáticamente (Google no informa la fecha de creación de la cuenta) |
| 15 | Premium y pagos | — | No existen todavía: no se procesan pagos ni datos de tarjetas |
| 16 | El filtro de "solo comida" depende de reglas y del prompt | Medio | Pendiente: reforzar con un clasificador de temas |
| 17 | Cupos diarios y token de sesión | Bajo | Corregido: los cupos y las sesiones se persisten en PostgreSQL (con vuelta a memoria si la base falla). El token sigue en `sessionStorage`, que es lo esperable para una SPA sin cookies de terceros |
| 18 | El límite por IP del invitado depende de que el servidor vea la IP real | Medio | Corregido: uvicorn usa `--proxy-headers` y el puerto 8000 ya no se publica (solo Caddy, por 80/443), así nadie puede llamar al backend directo ni falsear `X-Forwarded-For`. `FORWARDED_ALLOW_IPS` es configurable. Hay un `docker-compose.override.yml` que abre el 8000 solo en 127.0.0.1 para pruebas |
| 19 | Panel de administración para aprobar comercios | Medio | Hecho: solo los correos de `ADMIN_EMAILS` pueden aprobar, rechazar o suspender; `COMERCIOS_AUTOAPROBADOS` debe estar en 0 en producción |
| 20 | Inyección de instrucciones por los datos: el nombre, la dirección o el barrio de un comercio los escribe una persona y después los lee la IA | Medio | Mitigado en tres capas: (1) el formulario rechaza textos que parecen órdenes para una IA (`diseno.parece_instruccion_ia`); (2) lo que ve Gemini pasa por `diseno.dato_seguro_para_ia` (sin saltos de línea ni ` < >, recortado, y reemplazado si parece una orden); (3) regla 23 del prompt y `validar_respuesta_ia`. Más la revisión manual del administrador. Ningún filtro de texto es perfecto. Pruebas en `tests/test_comercios.py` |
| 21 | Servidor publicado sin HTTPS | Medio | Corregido en la documentación: se elimina la opción `http://IP:8000`; solo dominio o `TU_IP.nip.io` con HTTPS por Caddy (Vercel bloquea llamadas http desde una página https) |
| 22 | La sesión de Google se recuerda en el navegador (localStorage) hasta que vence el token | Bajo (decisión de diseño) | Se aceptó por usabilidad: quien ya inició sesión entra directo al chat. El token dura 12 h, no contiene contraseñas, el backend lo verifica en cada pedido, «Cerrar sesión» lo borra y, si el servidor lo rechaza (por ejemplo porque se cambió `SESSION_SECRET`), la app vuelve al inicio. Riesgo residual: en una computadora compartida conviene cerrar sesión. El invitado no se guarda |

## Qué se guarda
- Contraseñas: ninguna (la identidad la prueba Google).
- De una cuenta: nombre y correo de Google, restricciones y preferencias, historial de chat.
- De un comercio: los datos del formulario (nombre, qué vende, zona, dirección y teléfono del local, Instagram opcional).

## Recomendaciones para publicar
- Cargar secretos solo como variables de entorno del servicio. Revocar la clave de Gemini que estuvo en el `.env` anterior.
- No subir a Git: `.env`, claves ni archivos de datos pesados. Revisar con `git status` antes del primer commit.
- Mantener la pantalla de consentimiento de Google en modo "Prueba" con usuarios autorizados, o publicarla.
