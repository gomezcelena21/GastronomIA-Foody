# Despliegue sin que el servidor se duerma y sin base de datos que venza

> **¿Sin dinero ni tarjeta?** Seguí `deploy/GUIA_GRATIS_VERCEL_RENDER_NEON.md`: frontend en Vercel, backend en Render (servicio web gratis, con un monitor que lo mantiene despierto) y base en Neon. Lo de abajo es para un servidor propio.

## Por qué no usar la base de Render

- El **servicio web gratuito** de Render se duerme por inactividad (la primera visita puede tardar 30–60 s); se mitiga con un monitor que visite `/ping`, como explica la guía gratuita.
- La **base PostgreSQL gratuita** de Render vence a los 30 días (y hay proveedores que dan 90). No es permanente.

Este proyecto necesita un proceso Python que quede encendido y una base PostgreSQL **con PostGIS**. Las opciones de abajo cumplen eso.

## Arquitectura recomendada

```
Navegador
   │
   ├── Frontend React (Vercel, gratis)  ──https──►  Backend FastAPI
   │                                                │
   │                                                └── PostgreSQL + PostGIS
   │                                                    (en la misma VM o en Neon)
   └── Login con Google
```

Vercel **solo** hostea el frontend. El backend y la base van aparte.

---

## Opción A (recomendada, $0): Oracle Cloud Always Free

Oracle da, para siempre y sin vencer:

- 2 OCPU ARM Ampere A1 y **12 GB de RAM** (o 2 VM AMD de 1 GB).
- 200 GB de disco.
- 10 TB de salida por mes.
- La instancia **no se duerme** por inactividad.

Alcanza de sobra para FastAPI + PostgreSQL/PostGIS con ~27.000 lugares.

> **Única advertencia:** Oracle puede reclamar una instancia *Always Free* que pase 7 días con CPU < 20 %, red < 20 % y memoria < 20 %. Con la app y Postgres corriendo, y con algo de tráfico real, no suele pasar. Si te preocupa, usá 1 OCPU / 4 GB (el umbral de memoria baja a 800 MB) o las dos VM AMD micro. También podés pasar la cuenta a *Pay As You Go*: los recursos Always Free siguen siendo gratis.

### 1. Crear la VM

1. Creá una cuenta en https://cloud.oracle.com/free (pide tarjeta para verificar; no cobra si te quedás en Always Free).
2. **Compute → Instances → Create instance**.
3. Imagen: **Ubuntu 22.04** o **24.04**.
4. Shape: **VM.Standard.A1.Flex**, 1 OCPU / 4 GB (o 2/12 si te deja).
5. Descargá la clave SSH y anotá la **IP pública**.
6. En **Networking → Security List** de la VCN, abrí **solo** los puertos **80** y **443** (TCP, origen `0.0.0.0/0`). **No abras el 8000**: el backend queda detrás de Caddy y no debe ser público.

### 2. Entrar y preparar el servidor

```bash
ssh -i tu-clave.key ubuntu@IP_DEL_SERVIDOR

# Firewall del sistema (Ubuntu)
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Docker + compose
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Subir el proyecto

Sin repositorio Git, desde tu PC:

```powershell
scp -i tu-clave.key -r "C:\Users\Usuario\Documents\GastronomIA\Gastronomía Proyecto" ubuntu@IP_DEL_SERVIDOR:/home/ubuntu/gastronomia
```

O subilo a GitHub y hacé `git clone` en la VM.

### 4. Configurar variables

```bash
cd /home/ubuntu/gastronomia
cp .env.produccion.example .env.produccion
nano .env.produccion
```

Mínimo a completar:

- `POSTGRES_PASSWORD`: una clave larga.
- `GEMINI_API_KEY`: tu clave de Google AI Studio.
- `GOOGLE_CLIENT_ID`: el mismo del frontend.
- `SESSION_SECRET`: 32+ caracteres (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`).
- `FRONTEND_ORIGINS`: `https://tu-app.vercel.app` (sin barra final).
- `ADMIN_EMAILS`: tu correo de Google.
- `DOMINIO`: si tenés dominio, `api.tudominio.com` (DNS tipo A a la IP). Si no, `TU_IP.nip.io` (por ejemplo `129.150.10.20.nip.io`) para HTTPS gratis. **Sin HTTPS no funciona con Vercel**: el navegador bloquea que una página https llame a un backend http.

### 5. Levantar todo

```bash
docker compose --env-file .env.produccion up -d --build
```

Esto crea:

- `db`: PostgreSQL 16 + PostGIS (el esquema se carga solo la primera vez).
- `backend`: FastAPI en el puerto 8000, **solo accesible dentro de Docker** (no se publica a internet).
- `caddy`: HTTPS automático en 80/443.

Verificá:

```bash
curl http://127.0.0.1:8000/health   # funciona desde el propio servidor (docker-compose.override.yml lo abre solo en localhost)
# {"status":"healthy","database":"connected"}
```

### 6. Cargar la base unificada (27.064 lugares)

La primera vez la base está vacía (solo el esquema). Importá el dataset:

```bash
docker compose --env-file .env.produccion exec backend \
  python /app/scripts/cargar_base_unificada.py
```

Al terminar corre `ANALYZE` solo. Verificá:

```bash
docker compose --env-file .env.produccion exec backend \
  python -c "import os,psycopg2;c=psycopg2.connect(os.environ['DATABASE_URL']);q=c.cursor();q.execute('SELECT count(*) FROM restaurants');print(q.fetchone())"
```

### 7. Conectar Vercel

En **Vercel → Project → Settings → Environment Variables**:

```env
VITE_API_URL=https://api.tudominio.com
VITE_GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
VITE_CONTACT_EMAIL=contacto@gastronomia.com.ar
```

`VITE_CONTACT_EMAIL` es el correo público que aparece en `/privacidad` y
`/terminos`. No es un secreto: podés cambiarlo sin tocar el código.

Si no usás dominio, `VITE_API_URL=https://TU_IP.nip.io` (HTTPS por Caddy). No uses `http://IP:8000`: el puerto 8000 está cerrado y, además, Vercel (https) bloquearía la llamada.

Después:

- Root Directory: `frontend`
- Framework: Vite
- Build: `npm run build`
- Output: `dist`

### 8. Google Cloud Console

En **Orígenes autorizados de JavaScript** agregá el dominio de Vercel:

```
https://tu-app.vercel.app
```

No hace falta agregar el backend: el login se valida del lado del servidor con el Client ID.

---

## Opción B: base administrada que no vence (Neon) + servidor chico

Si preferís no administrar PostgreSQL:

### Base: Neon Free

- Plan **gratuito permanente** (no es prueba de 30/90 días).
- **No pausa por inactividad**: el cómputo se suspende a los 5 minutos y se reanuda en milisegundos en la próxima consulta. Los datos y la cadena de conexión no cambian.
- 1 GB de storage (tu base usa muchísimo menos).
- Soporta **PostGIS**.

Pasos:

1. https://neon.com → crear proyecto.
2. En **SQL Editor** ejecutá `database/schema.sql`.
3. Copiá la cadena de conexión (`...?sslmode=require`).
4. En `.env.produccion` poné `DATABASE_URL=...` y **no levantes** el servicio `db`:

```bash
docker compose --env-file .env.produccion up -d --build backend caddy
docker compose --env-file .env.produccion exec backend \
  python /app/scripts/cargar_base_unificada.py
```

> Supabase Free también sirve, pero **pausa** el proyecto tras ~7 días sin uso (no lo borra). Neon no pausa.

### Servidor: Fly.io (pago chico, sin sleep)

Fly.io ya no tiene free tier. Una máquina `shared-cpu-1x` de 256 MB siempre encendida cuesta **~US$ 2,19/mes** (512 MB: ~US$ 3,69). No se duerme. Ideal si querés cero mantenimiento y no te importa pagar eso.

Alternativas pagas baratas: Hetzner CX22 (~€4/mes), Oracle Pay As You Go (los Always Free siguen gratis).

---

## Comparación rápida

| Opción | ¿Se duerme? | ¿Vence? | Costo | PostGIS |
|---|---|---|---|---|
| Render Free | Sí (inactividad) | DB a los 30 días | $0 | Sí |
| **Oracle Always Free** | **No** | **No** | **$0** | **Sí** |
| Neon Free (DB) | Cómputo on-demand (ms) | **No** | **$0** | **Sí** |
| Supabase Free (DB) | Pausa a los 7 días sin uso | No | $0 | Sí |
| Fly.io | No | No | ~US$ 2–4/mes | Depende de la DB |
| Railway | No | Ya no hay free real | ~US$ 5/mes | Sí |

---

## Backups (importante)

El proyecto trae `deploy/backup.sh` y `deploy/restore.sh`. El backup:

- usa `pg_dump --clean --if-exists` y comprime con gzip;
- descarta archivos vacíos o corruptos (`gzip -t`);
- escribe un `.sha256` junto al backup;
- borra los backups de más de `BACKUP_RETENER_DIAS` días (14 por defecto).

### Opción 1: servicio Docker (recomendado)

```bash
# una vez
mkdir -p backups
docker compose --env-file .env.produccion --profile backups up -d backup
```

Guarda un backup por día en `./backups` y corre como servicio. No arranca con
`docker compose up -d` normal porque está en el perfil `backups`.

### Opción 2: systemd o cron

En el servidor:

```bash
sudo apt-get install -y postgresql-client
sudo cp deploy/gastronomia-backup.service deploy/gastronomia-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gastronomia-backup.timer
```

O copiá la línea de `deploy/crontab.example` con `crontab -e`.

> El PostGIS del compose **no publica** el puerto 5432 en el host (solo lo
> expone a la red interna). Para usar systemd/cron con esa base, agregá
> `ports: ["127.0.0.1:5432:5432"]` al servicio `db` o usá el servicio Docker de
> backups (opción 1). Con Neon/Supabase, el `DATABASE_URL` del `.env.produccion`
> ya es accesible desde el servidor.

### Restaurar

```bash
docker run --rm \
  -v "$PWD/backups:/backups" -v "$PWD/deploy:/deploy:ro" \
  --network container:$(docker compose ps -q db) \
  -e PGPASSWORD="$POSTGRES_PASSWORD" -e PGHOST=127.0.0.1 -e PGUSER=gastro \
  -e PGDATABASE=gastro_ia \
  postgres:16-alpine sh /deploy/restore.sh /backups/gastro_ia_FECHA.sql.gz
```

O, si tenés `psql` en el servidor:

```bash
./deploy/restore.sh backups/gastro_ia_FECHA.sql.gz
```

**El backup incluye `DROP`/`CREATE`**: restaurar sobre producción reemplaza las
tablas. Hacé un backup nuevo antes de restaurar. Con Neon usá también los
snapshots del panel.

Probá el restore al menos una vez al mes en una base temporal, no solo el
`pg_dump`.

---

## Monitoreo (uptime y errores)

### Uptime

Usá un monitor HTTP gratuito (UptimeRobot, Better Stack, Cronitor) apuntando a:

```
https://api.tudominio.com/health
```

- Intervalo: 5 minutos.
- Alerta por correo o Telegram si no responde `200` o si el JSON no dice
  `"status":"healthy"`.
- No hace falta exponer `/docs` ni ningún otro endpoint.

### Errores (Sentry, opcional)

1. Creá un proyecto Python/FastAPI en https://sentry.io.
2. Copiá el DSN y definí en `.env.produccion`:

```env
SENTRY_DSN=https://...
SENTRY_ENVIRONMENT=produccion
SENTRY_TRACES_SAMPLE_RATE=0
```

3. Reiniciá el backend:

```bash
docker compose --env-file .env.produccion up -d backend
```

Sin `SENTRY_DSN`, el código no inicializa Sentry ni envía nada. Los logs también
quedan en Docker con rotación (10 MB × 5 archivos por servicio).

### Logs

```bash
docker compose --env-file .env.produccion logs -f --tail=200 backend
docker compose --env-file .env.produccion logs -f --tail=200 caddy
```

Para revisar el uso de la base:

```bash
docker compose --env-file .env.produccion exec db \
  psql -U gastro -d gastro_ia -c "SELECT count(*) FROM restaurants;"
```

---

## Datos: geocodificación, ratings y menús

La base puede vivir sin estos pasos: el chat y Explorar funcionan con lo que hay.
Son mejoras opcionales.

### Geocodificar los locales sin coordenadas

```bash
docker compose --env-file .env.produccion exec backend \
  python /app/scripts/geocodificar_ba_data.py --dry-run --limit 10

# con NOMINATIM_EMAIL definido en .env.produccion
docker compose --env-file .env.produccion exec backend \
  python /app/scripts/geocodificar_ba_data.py --limit 100
```

Nominatim permite **1 consulta por segundo**: 2.740 pendientes tardan ~46
minutos. El script cachea respuestas en `data/cache_geocodificacion.json` para
no repetir consultas. Si tu red recibe `403`, usá el dataset oficial de BA Data
con coordenadas o un proveedor pago.

### Completar ratings/precios con Google Places (opcional, pago)

```bash
GOOGLE_MAPS_API_KEY=... python scripts/enriquecer_google_places.py --dry-run --limit 10
```

Requiere habilitar **Places API (New)** y facturación en Google Cloud. Revisá
las condiciones de Google: los datos de Maps necesitan atribución y no deben
almacenarse más de 30 días. Si no querés depender de Google, no lo uses.

### Importar menús

Usá la plantilla `data/plantillas/menus.csv` y:

```bash
python scripts/importar_menus_csv.py data/plantillas/menus.csv --dry-run
python scripts/importar_menus_csv.py data/plantillas/menus.csv
```

### Verificar opciones sin TACC

```bash
python scripts/verificar_sin_tacc.py
# completar el CSV con lo confirmado por teléfono
python scripts/importar_sin_tacc_csv.py data/reporte_sin_tacc.csv --dry-run
python scripts/importar_sin_tacc_csv.py data/reporte_sin_tacc.csv
```

Ninguna carga convierte un local en “apto garantizado”: el chat y los términos
siempre recomiendan confirmar por contaminación cruzada.

---

## Actualizar la aplicación

```bash
cd /home/ubuntu/gastronomia
# subir los archivos nuevos
docker compose --env-file .env.produccion up -d --build
```

## Verificación final

1. `https://api.tudominio.com/health` → `healthy`.
2. `https://tu-app.vercel.app` → landing.
3. “Hablar con Foody” → abre `/chat` en otra pestaña.
4. Login con Google y “Continuar sin registrarme”.
5. Enviar “Busco una pizzería sin TACC en Palermo” → respuesta de Foody.
6. Explorar → filtros y mapa.

## Páginas legales

El frontend sirve `/privacidad` y `/terminos` (componente `frontend/src/Legal.tsx`)
y el landing enlaza a ambas. El correo de contacto sale de
`VITE_CONTACT_EMAIL` (por defecto `contacto@gastronomia.com.ar`).

Antes de publicar, revisá que:

1. El correo sea uno que realmente leas.
2. La política refleje los proveedores que uses (Google, hosting, Sentry).
3. Los términos mencionen las licencias de datos (OpenStreetMap/ODbL y
   BA Data/CC-BY-2.5-AR).

## Integración continua (GitHub Actions)

`.github/workflows/ci.yml` corre en cada push/PR:

- **backend**: PostgreSQL 16 + PostGIS real, esquema, dataset y `unittest`;
- **frontend**: `npm ci`, build de producción y Playwright (API simulada);
- **docker**: construye la imagen y verifica que las dependencias importen.

No necesita secretos: Gemini, Google y Sentry se tratan como opcionales. Para
correr lo mismo localmente:

```bash
python -m unittest discover -s tests -v
cd frontend && npm ci && npm run build && npx playwright test
docker build -t gastronomia:local .
```

## Notas

- La clave de Gemini vive **solo** en `.env.produccion` del servidor. Nunca en Vercel ni en el frontend.
- Los cupos diarios (`CONSULTAS_POR_DIA`, `ANONIMOS_POR_DIA`) y las sesiones se guardan en PostgreSQL (`cuotas_diarias`, `sesiones_gemini`) y sobreviven reinicios. Si la base falla, el backend vuelve solo al contador en memoria.
- La imagen instala `backend/requirements.lock` (versiones fijadas) y usa `requirements.txt` solo si el lock no existe.
- Las descargas de `analytics/` necesitan que esa carpeta esté incluida en la imagen (el `Dockerfile` ya la copia).
- El backend aplica índices y `ANALYZE` al iniciar (`OPTIMIZAR_AL_INICIAR=1`). También podés correr `database/maintenance.sql` a mano.
- El importador hace `TRUNCATE restaurant_features, restaurants RESTART IDENTITY CASCADE`: en producción, hacé un backup antes de reimportar el dataset.
