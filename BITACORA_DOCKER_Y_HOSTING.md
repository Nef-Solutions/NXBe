# Bitácora: Docker y publicación gratuita de Overol

Registro detallado del trabajo del **15 de noviembre de 2026**: qué se cambió en el repositorio, qué se configuró en cada servicio, por qué se tomó cada decisión, qué se comprobó y qué queda pendiente.

Las guías de uso diario son [DOCKER.md](DOCKER.md), para trabajar en local, y [HOSTING.md](HOSTING.md), para publicar. Este documento explica cómo se llegó a ellas.

> Este documento no contiene contraseñas ni claves. Los valores secretos viven solo en los paneles de Supabase, Render, Streamlit y GitHub.

---

## 1. Resumen

| Antes | Después |
|---|---|
| Solo la base de datos corría en Docker; backend y front se instalaban a mano en cada PC. | Todo el proyecto corre con `docker compose up`, con recarga automática al guardar. La forma anterior sigue funcionando. |
| El proyecto solo funcionaba en local. | Publicado gratis y con despliegue automático en cada push a `main`. |
| El backend guardaba archivos en el disco local y solo leía la base desde `POSTGRES_*`. | El backend acepta `DATABASE_URL`, guarda archivos en Supabase Storage (las cédulas en un bucket privado) y tiene ajustes de seguridad para producción. |
| La carpeta del front se llamaba `Overol Front` (con espacio). | Se llama `overol-front`. Streamlit Cloud no soporta espacios en la ruta. |
| El README tenía enlaces rotos y datos desactualizados. | La documentación está al día y se comprobó que los enlaces funcionan. |

**Sitio publicado:**

| Parte | Dirección |
|---|---|
| Aplicación (front) | <https://overol-nxbe.streamlit.app> |
| API | <https://overol-backend.onrender.com/api/> |
| Admin de Django | <https://overol-backend.onrender.com/admin/> |

---

## 2. Pull Requests fusionados

| PR | Rama | Contenido |
|---|---|---|
| [#7](https://github.com/Nef-Solutions/NXBe/pull/7) | `docker-completo` | Docker completo, preparación del backend y del front para producción, `render.yaml`, tarea diaria, `DOCKER.md`, `HOSTING.md` y documentación corregida. |
| [#8](https://github.com/Nef-Solutions/NXBe/pull/8) | `renombrar-front` | Carpeta `Overol Front` renombrada a `overol-front`, con todas sus referencias actualizadas. |
| [#9](https://github.com/Nef-Solutions/NXBe/pull/9) | `arreglar-tarea-diaria` | Corrección de la tarea diaria: descargar el código antes de entrar a `backend/`. |
| [#10](https://github.com/Nef-Solutions/NXBe/pull/10) | `docs-hosting-actualizado` | `HOSTING.md` y los README actualizados con la publicación real. |

Todos se trabajaron en ramas aparte y llegaron a `main` por Pull Request, porque `main` es lo que se publica.

---

## 3. Cambios en el repositorio

### 3.1 Docker

| Archivo | Qué hace |
|---|---|
| [`docker-compose.yml`](docker-compose.yml) (raíz, nuevo) | Levanta `db`, `backend` y `front`. Incluye `backend/docker-compose.yml` para que ambas formas de trabajo usen la misma base. |
| [`docker-compose.override.yml`](docker-compose.override.yml) (nuevo) | Modo desarrollo, que Compose aplica solo: monta el código, usa `runserver` y Streamlit con recarga, y muestra las cuentas de demostración en el login. |
| [`backend/Dockerfile`](backend/Dockerfile) (nuevo) | Imagen del backend: Python 3.14, Gunicorn, `collectstatic`, usuario sin privilegios y migraciones al arrancar. Respeta `PORT`. |
| [`backend/.dockerignore`](backend/.dockerignore) (nuevo) | Deja fuera `.env`, `media/`, `private_media/` y `.venv`. |
| [`backend/docker-compose.yml`](backend/docker-compose.yml) | Credenciales con valores por defecto y *healthcheck* `pg_isready`, para que el backend espere a la base. |

Se probó en local:
- El backend y el front arrancan.
- La recarga automática funciona en ambos.
- `seed_demo` y el login funcionan.
- El modo producción funciona: Gunicorn y los estilos del admin cargan.

### 3.2 Backend listo para producción

| Archivo | Cambio |
|---|---|
| [`backend/core/settings.py`](backend/core/settings.py) | Ver la lista detallada abajo. |
| [`backend/apps/authentication/storage.py`](backend/apps/authentication/storage.py) | Las cédulas van a un bucket S3 **privado** si `S3_PRIVATE_BUCKET` está definido, o al disco local si no. Siguen leyéndose solo a través de la API. |
| [`backend/documentacion/requirements.txt`](backend/documentacion/requirements.txt) | Nuevas dependencias: `gunicorn`, `whitenoise`, `dj-database-url` y `django-storages[s3]`. |
| [`backend/.env.example`](backend/.env.example) | `PAYMENT_RESULT_URL` apunta al front real (`http://localhost:8501/`). Antes apuntaba al puerto 3000. |

Cambios en `settings.py`:
- Lee la base desde `DATABASE_URL`, que tiene prioridad sobre `POSTGRES_*`.
- Agrega WhiteNoise y `STATIC_ROOT`, para servir los estilos del admin con Gunicorn.
- Guarda los archivos en almacenamiento compatible con S3 (variables `S3_*`).
- Agrega solo el dominio de Render a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.
- Con `DEBUG=False`: cookies seguras, confianza en el https del proxy y CORS restringido a `CORS_ALLOWED_ORIGINS`.
- Lee el correo SMTP desde `EMAIL_*`.

Sin las variables nuevas, el backend se comporta igual que antes en local.

### 3.3 Front listo para Streamlit Cloud

| Archivo | Cambio |
|---|---|
| [`overol-front/app.py`](overol-front/app.py) | No lanza una segunda instancia de Streamlit si ya corre dentro de Streamlit (`streamlit.runtime.exists()`). |
| [`overol-front/core/config.py`](overol-front/core/config.py) | Lee la configuración de las variables de entorno o, si no están, de `st.secrets`, que es como la entrega Streamlit Cloud. |
| Carpeta `overol-front/` | Renombrada desde `Overol Front`. |

### 3.4 Publicación y tareas

| Archivo | Qué hace |
|---|---|
| [`render.yaml`](render.yaml) | Blueprint del backend en Render: plan gratuito, región Virginia, Docker, publicación automática solo cuando cambia `backend/`, y las variables (los secretos se escriben en el panel). |
| [`.github/workflows/vencer-solicitudes.yml`](.github/workflows/vencer-solicitudes.yml) | Todos los días a las 09:00 UTC ejecuta `expire_visit_requests` contra la base de producción, lo que además evita que Supabase pause la base. Si falta el secret `DATABASE_URL`, no hace nada. |
| [`.gitignore`](.gitignore) | Ignora `private_media/` y `.streamlit/secrets.toml`. |

### 3.5 Documentación

- **Nuevos:** [`DOCKER.md`](DOCKER.md), [`HOSTING.md`](HOSTING.md) y esta bitácora.
- **Reescrito:** [`README.md`](README.md).
  - Antes mencionaba una carpeta `Overol/` que no existe y Redis, que no se usa.
  - Tenía 8 enlaces a documentos inexistentes.
  - Decía que los pagos y el asistente no estaban implementados, aunque sí lo están.
- **Actualizados:** [`backend/readme.md`](backend/readme.md), el [manual técnico](backend/documentacion/manual-tecnico-integral-backend.md), [`overol-front/README.md`](overol-front/README.md), [`overol-front/DESPLIEGUE.md`](overol-front/DESPLIEGUE.md) y la guía de pruebas del front.

---

## 4. Servicios configurados

### 4.1 Supabase (base de datos y archivos)

- **Organización:** `NXBe`, plan Free.
- **Proyecto:** `overol`. Ref `ogthnnocigsmdqmgokry`, región **East US (North Virginia)** (`us-east-1`), la misma zona que Render.
- **Data API desactivada**, para que las tablas de Django (incluida la de usuarios) no queden expuestas por la API REST de Supabase.
- **Conexión:** se usa el **Session pooler** (`aws-1-us-east-1.pooler.supabase.com:5432`, usuario `postgres.<ref>`), porque la conexión directa solo funciona por IPv6.
- **Buckets:** `media` (público: fotos de perfil y certificaciones) y `private-media` (privado: cédulas).
- **S3:** protocolo activado y clave de acceso `render-backend`.
- **PostGIS:** lo activó la migración `catalog.0003_enable_postgis` en el primer arranque.

### 4.2 Render (backend)

- **Blueprint** `overol`, con el servicio web **`overol-backend`** (plan Free, Docker, rama `main`).
- Render se conectó a GitHub con acceso al repositorio `NXBe`.
- **Variables:** las secretas se escribieron en el panel (`DATABASE_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` y `GEMINI_API_KEY`); el resto viene de `render.yaml` o se completó en el panel.
  - `PAYMENT_RESULT_URL=https://overol-nxbe.streamlit.app/`
  - `TRANSBANK_RETURN_URL=https://overol-backend.onrender.com/api/payments/transbank/return/`

### 4.3 Streamlit Community Cloud (front)

- **App:** `overol-nxbe`, desde `Nef-Solutions/NXBe`, rama `main`, archivo `overol-front/app.py`.
- **Python:** 3.11, la misma versión de la imagen Docker y de las pruebas.
- **Secrets:** `OVEROL_API_URL`, `OVEROL_API_TIMEOUT=60`, `OVEROL_COOKIE_SECURE=1`, `OVEROL_MODO_DEMO=0` y `OVEROL_STREAMLIT_STARTED=1`.
- La primera app, con la ruta `Overol Front/app.py`, se borró y se creó de nuevo después del cambio de nombre de la carpeta.

### 4.4 GitHub

- **Secret de Actions:** `DATABASE_URL`, para la tarea diaria.
- La tarea **Vencer solicitudes pendientes** se ejecutó a mano y terminó en verde (ejecución #2).

### 4.5 Administrador

- Se creó un **superusuario** en la base de producción desde un PC, porque Render Free no tiene consola. Se usó Docker apuntando a Supabase con `DATABASE_URL`.
- Se le asignó el rol **Administrador** (`role=ADMIN`). Django crea los superusuarios con el rol *Cliente*, y el panel de administración del front exige *Administrador*.
- El paso a paso está en [HOSTING.md](HOSTING.md#crear-el-administrador).

---

## 5. Decisiones y motivos

| Decisión | Motivo |
|---|---|
| **No usar Vercel** | El front Streamlit necesita un servidor siempre encendido y WebSocket, y Vercel solo ejecuta funciones cortas. |
| **Streamlit Community Cloud** para el front | Es gratis, está hecho para Streamlit y publica solo desde GitHub. |
| **Render** para el backend | Tiene plan gratis con Docker y publicación automática. Se duerme sin uso, algo aceptable para un proyecto académico. |
| **Supabase** para la base y los archivos | Una sola cuenta da PostgreSQL con PostGIS y almacenamiento compatible con S3. La base gratuita de Render se borra a los 30 días y su disco se borra en cada despliegue. |
| **Mismas zonas** (Virginia) | Reduce la latencia entre el backend y la base. |
| **Cédulas en un bucket privado** | No tienen URL pública; solo se leen a través de la API, con permiso de administrador. |
| **Docker sin reemplazar la forma anterior** | Nadie del equipo queda obligado a cambiar su manera de trabajar. Ambas formas comparten la misma base local. |
| **Renombrar la carpeta en vez de un archivo puente** | Es la solución definitiva y evita duplicar `requirements.txt` y la configuración. |
| **Trabajo en ramas y Pull Requests** | `main` se publica solo; así cada cambio se revisa antes de llegar al sitio. |

---

## 6. Qué se comprobó

- **Backend:** las **79 pruebas** pasan dentro de Docker, tanto con la configuración local como con `DATABASE_URL`. `makemigrations --check` no detecta cambios pendientes.
- **Front:** todas las pruebas automáticas pasan (`TODO OK`), antes y después del cambio de nombre de la carpeta.
- **Modo producción en local:**
  - Pruebas con `DEBUG=False`, una base PostGIS y un servidor S3 de prueba (moto).
  - Las fotos van al bucket público con una URL de Supabase.
  - Las cédulas van al bucket privado y se pueden leer de vuelta.
  - Los dominios desconocidos se rechazan (400).
  - Las cookies seguras y el CSRF de Render están activos.
- **Sitio publicado:**
  - La API y el admin responden (200) y el admin carga con sus estilos.
  - El front muestra la portada con datos del backend.
  - Las migraciones se aplicaron en Supabase.
  - La tarea diaria termina en verde.

**Todavía no se ha probado en el sitio publicado:**
- Registro y login.
- Subida de cédula.
- «Mantener mi sesión iniciada», en particular la cookie en Streamlit Cloud.
- Pago de suscripción en Webpay sandbox.

La lista está en [HOSTING.md](HOSTING.md#paso-6-comprobar-que-quedó-bien).

---

## 7. Problemas encontrados

| Problema | Solución |
|---|---|
| Render no conectaba a la base (`password authentication failed`). | Se cambió la contraseña en Supabase y se volvió a desplegar unos minutos después, porque el pooler tarda en reconocer una contraseña nueva. |
| Streamlit: "Error installing requirements". | La ruta `Overol Front` tenía un espacio. Se renombró la carpeta a `overol-front` (PR #8) y se creó la app de nuevo. |
| Render: "No repositories found". | Se dio acceso al repositorio `NXBe` desde **Configure account** en GitHub. |
| La tarea diaria fallaba en 9 segundos. | Entraba a `backend/` antes de descargar el código. Se corrigió en el PR #9. |
| `$env:` no funcionaba al crear el superusuario. | La ventana era CMD, no PowerShell. En CMD se usa `set "DATABASE_URL=..."`. |

Detalle de cada caso en [HOSTING.md](HOSTING.md#problemas-encontrados-y-cómo-se-resolvieron).

---

## 8. Pendientes y recomendaciones

1. **Avisar al equipo** que haga `git pull`: la carpeta del front cambió de nombre y hay guías nuevas.
2. **Probar el flujo completo** en el sitio publicado (sección 6).
3. **Imágenes de cédulas en el historial de Git:** `backend/private_media/verifications/` tiene imágenes subidas antes de este trabajo. `.gitignore` evita que se suban nuevas, pero las existentes siguen en el repositorio y en su historial. Si son datos reales, hay que eliminarlas también del historial.
4. **Contraseña de la base:** cámbiala si se compartió por algún canal. Después actualízala en Render y en el secret de GitHub, y espera unos minutos antes de volver a desplegar.
5. **Correo real:** hoy los códigos de recuperación de contraseña solo aparecen en el log de Render. Para enviarlos por correo hay que configurar SMTP (ver [HOSTING.md](HOSTING.md#límites-del-plan-gratuito)).
6. **Cuentas de demostración:** no ejecutes `seed_demo` en producción si el sitio va a recibir usuarios reales, porque su contraseña es pública.

---

## 9. Dónde está cada cosa

| Necesito… | Dónde |
|---|---|
| Trabajar en local con Docker | [DOCKER.md](DOCKER.md) |
| Publicar o cambiar la configuración publicada | [HOSTING.md](HOSTING.md) |
| Crear o dar rol a un administrador | [HOSTING.md](HOSTING.md#crear-el-administrador) |
| Variables del front | [overol-front/DESPLIEGUE.md](overol-front/DESPLIEGUE.md) |
| Variables y detalles del backend | [backend/readme.md](backend/readme.md) y el [manual técnico](backend/documentacion/manual-tecnico-integral-backend.md) |
| Cambiar secretos | Paneles de Render (**Environment**), Streamlit (**Settings → Secrets**), GitHub (**Settings → Secrets → Actions**) y Supabase |
