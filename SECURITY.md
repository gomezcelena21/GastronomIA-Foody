# Política de seguridad

## Versiones con soporte

La rama `main` es la única versión desplegada y recibe correcciones de seguridad.

| Versión | Con soporte |
| ------- | ----------- |
| `main` (última) | :white_check_mark: |
| Cualquier commit anterior | :x: |

## Cómo reportar una vulnerabilidad

**No abras un issue público.** Usá el reporte privado de GitHub:

1. Entrá a https://github.com/gomezcelena21/GastronomIA-Foody/security/advisories/new
2. Describí el problema, cómo reproducirlo y el impacto que creés que tiene.
3. Si podés, incluí una prueba de concepto mínima (sin datos reales de terceros).

También podés escribir a **contacto@gastronomia.com.ar** con el asunto `SEGURIDAD`.

Qué esperar:

- Confirmación de recepción dentro de los **7 días**.
- Una evaluación inicial y un plan de corrección dentro de los **30 días**.
- Crédito en el aviso publicado, si querés.

## Alcance

Entran en alcance:

- El backend FastAPI (`backend/`) y su API.
- El frontend React (`frontend/`).
- El despliegue (`Dockerfile`, `docker-compose.yml`, `deploy/`).
- La configuración de GitHub Actions (`.github/`).

Quedan fuera de alcance:

- Ataques de denegación de servicio o de fuerza bruta masiva.
- Ingeniería social contra las personas del proyecto.
- Vulnerabilidades en servicios de terceros (Google, Vercel, Render, Neon): reportalas a cada proveedor.
- Faltas de mejores prácticas sin impacto demostrable.

## Datos y secretos

- El repositorio es público y **no contiene claves**: `.env` y `.env.produccion` están en `.gitignore`, y las plantillas `.env.example` solo tienen marcadores.
- El escaneo de secretos y la protección de push de GitHub están activos: un commit con una clave real se bloquea antes de subir.
- Si encontrás una clave real en el historial, reportalo en privado; se rota y se limpia el historial.

## Prácticas del proyecto

- Sesiones firmadas con HMAC-SHA256 y `SESSION_SECRET` de 32+ caracteres; vencen a las 12 h.
- Login únicamente con Google: no se almacenan contraseñas.
- Consultas SQL parametrizadas y descargas restringidas a `analytics/` (sin path traversal).
- Límites por IP, por usuario y global para el chat y el login.
- Dependencias fijadas en `requirements.lock` y `package-lock.json`, con Dependabot semanal y CodeQL en cada push.
