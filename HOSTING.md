# Publicar Overol gratis

Guía paso a paso para dejar Overol en internet sin costo, con publicación automática: cada `git push` a `main` actualiza el sitio.

```text
 Navegador ──► Streamlit Community Cloud ──► Render ──────────► Supabase
               (front, overol-front/)        (backend, Docker)   ├─ PostgreSQL + PostGIS
                                                                 └─ Storage (fotos y cédulas)
 GitHub Actions ── una vez al día ──► vence solicitudes antiguas en la base
```

| Parte | Servicio | Plan | Se actualiza solo con… |
|---|---|---|---|
| Front | Streamlit Community Cloud | Gratis | push a `main` |
| Backend | Render (Web Service con Docker) | Free | push a `main` que toque `backend/` |
| Base de datos y archivos | Supabase | Free | (no depende del código; las migraciones las aplica el backend al arrancar) |
| Tarea diaria | GitHub Actions | Gratis | — |

Ninguno de los tres pide tarjeta de crédito para el plan gratuito, y en todos se puede entrar con la cuenta de GitHub.

> **Antes de empezar:** los cambios de Docker y hosting deben estar en `main`, porque Render y Streamlit publican desde esa rama. Fusiona primero el Pull Request de la rama `docker-completo`.

Ten a mano un bloc de notas para ir guardando los valores. Ninguno de ellos va al repositorio.

---

## Paso 1. Supabase: base de datos y archivos

1. Entra a <https://supabase.com>, inicia sesión con GitHub y crea un proyecto (**New project**):
   - **Name:** `overol`
   - **Database password:** genera una y **guárdala**.
   - **Region:** `East US (North Virginia)`, la misma zona que el backend en Render.
2. **Cadena de conexión** (`DATABASE_URL`): botón **Connect** arriba → pestaña de cadenas de conexión → **Session pooler**. Copia la URI, que se ve así:

   ```text
   postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
   ```

   Reemplaza `[YOUR-PASSWORD]` por la contraseña del punto 1. Si la contraseña tiene símbolos como `@`, `:` o `/`, genera otra solo con letras y números.

   Usa la de **Session pooler** y no la "Direct connection": la directa solo funciona por IPv6, y Render y GitHub Actions usan IPv4.
3. **Buckets** (menú **Storage** → **New bucket**):
   - `media`, marcado como **Public bucket**. Guarda fotos de perfil y certificaciones.
   - `private-media`, **sin** marcar público. Guarda las cédulas, que solo se leen a través de la API.
4. **Claves de Storage** (**Storage** → **Settings** → **S3 Connection**):
   - Anota el **Endpoint** (`https://<ref>.supabase.co/storage/v1/s3`) y la **Region** (por ejemplo `us-east-1`).
   - En **S3 Access Keys** → **New access key**, anota el **Access key ID** y el **Secret access key**. El secreto se muestra una sola vez.
5. Anota la URL pública del bucket `media`:

   ```text
   https://<ref>.supabase.co/storage/v1/object/public/media
   ```

   `<ref>` es el identificador del proyecto, que aparece en la URL del panel de Supabase.

**PostGIS:** no hay que activarlo a mano. La migración `catalog.0003_enable_postgis` lo hace al primer arranque del backend. Si esa migración fallara, actívalo en **Database** → **Extensions** → `postgis`, eligiendo el esquema `public`, y vuelve a desplegar.

---

## Paso 2. Render: backend

1. Entra a <https://render.com> con GitHub. Si el repositorio es de la organización **Nef-Solutions**, autoriza a Render a ver esa organización. Puede que un administrador de la organización tenga que aprobarlo.
2. **New** → **Blueprint** → elige el repositorio `NXBe`. Render lee [`render.yaml`](render.yaml) y propone el servicio `overol-backend`.
3. Render pide los valores marcados como secretos:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | La cadena del paso 1.2 |
   | `S3_ENDPOINT_URL` | Endpoint del paso 1.4 |
   | `S3_REGION` | Region del paso 1.4 |
   | `S3_ACCESS_KEY_ID` | Access key ID del paso 1.4 |
   | `S3_SECRET_ACCESS_KEY` | Secret access key del paso 1.4 |
   | `S3_MEDIA_PUBLIC_URL` | URL del paso 1.5 |
   | `GEMINI_API_KEY` | Clave de <https://aistudio.google.com/apikey>. Si se deja vacía, el asistente avisa que no está disponible. |
   | `TRANSBANK_RETURN_URL` | Por ahora `https://overol-backend.onrender.com/api/payments/transbank/return/`. Se corrige en el paso 4 si la URL real es distinta. |
   | `PAYMENT_RESULT_URL` | Por ahora `https://example.com/`. Se completa en el paso 4. |

   `SECRET_KEY` lo genera Render solo. `DEBUG=False` y los nombres de los buckets ya vienen en `render.yaml`.
4. **Apply**. El primer despliegue tarda unos minutos: construye la imagen de `backend/Dockerfile` y aplica todas las migraciones en Supabase.
5. Anota la URL del servicio, por ejemplo `https://overol-backend.onrender.com`, y comprueba que esta dirección muestra la lista de oficios en JSON:

   ```text
   https://overol-backend.onrender.com/api/catalog/categories/
   ```

### Crear el administrador

El plan gratuito de Render no tiene consola. El superusuario se crea desde tu PC, conectándote a la base de Supabase con Docker. Desde la raíz del repositorio:

```powershell
docker compose run --rm --no-deps -e DATABASE_URL="<cadena del paso 1.2>" backend python manage.py createsuperuser
```

Con `DATABASE_URL`, el contenedor ignora la base local y escribe en la de Supabase. Así se ejecuta cualquier comando de Django contra producción, así que hazlo con cuidado.

**Datos de demostración:** `seed_demo` crea cuentas con una contraseña que es pública, porque está en el repositorio. Para una demo académica se pueden cargar con el mismo comando, cambiando `createsuperuser` por `seed_demo`. Si el sitio va a recibir usuarios reales, no lo hagas.

---

## Paso 3. Streamlit Community Cloud: front

1. Entra a <https://share.streamlit.io> con GitHub y autoriza el acceso a la organización si lo pide.
2. **Create app** → **Deploy a public app from GitHub**:
   - **Repository:** `Nef-Solutions/NXBe`
   - **Branch:** `main`
   - **Main file path:** `overol-front/app.py`
   - **App URL:** elige un subdominio, por ejemplo `overol-nxbe`, y anota la URL completa: `https://overol-nxbe.streamlit.app`.
3. **Advanced settings**:
   - **Python version:** 3.12. El front está probado con 3.11 y versiones posteriores.
   - **Secrets:** pega lo siguiente, con la URL de tu backend:

     ```toml
     OVEROL_API_URL = "https://overol-backend.onrender.com/api/"
     OVEROL_API_TIMEOUT = "60"
     OVEROL_COOKIE_SECURE = "1"
     OVEROL_MODO_DEMO = "0"
     ```

     `OVEROL_API_TIMEOUT = "60"` es importante: el backend gratuito de Render se duerme y tarda hasta un minuto en despertar. Con el valor por defecto (10 segundos), la primera visita mostraría un error.
4. **Deploy**. Streamlit instala `overol-front/requirements.txt` y publica.

---

## Paso 4. Conectar el pago de Webpay con el front

En Render, abre el servicio **overol-backend** → **Environment** y corrige:

| Variable | Valor |
|---|---|
| `PAYMENT_RESULT_URL` | La URL del front, por ejemplo `https://overol-nxbe.streamlit.app/` |
| `TRANSBANK_RETURN_URL` | `https://<tu-servicio>.onrender.com/api/payments/transbank/return/` |

Guarda (**Save changes**) y Render vuelve a desplegar solo.

---

## Paso 5. Tarea diaria en GitHub Actions

El flujo [`.github/workflows/vencer-solicitudes.yml`](.github/workflows/vencer-solicitudes.yml) vence cada día las solicitudes pendientes con más de 30 días. Además mantiene activa la base de Supabase, que en el plan gratuito se pausa tras 7 días sin uso.

1. En GitHub: repositorio → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
   - **Name:** `DATABASE_URL`
   - **Secret:** la cadena del paso 1.2.
2. Pestaña **Actions** → **Vencer solicitudes pendientes** → **Run workflow**, para probarlo una vez. Debe terminar en verde.

GitHub desactiva las tareas programadas si el repositorio pasa 60 días sin actividad. Si eso ocurre, se reactivan desde la misma pestaña.

---

## Paso 6. Comprobar que quedó bien

- [ ] `https://<backend>/api/catalog/categories/` responde con la lista de oficios.
- [ ] `https://<backend>/admin/` carga con estilos y permite entrar con el superusuario.
- [ ] La portada del front carga por https y muestra los oficios.
- [ ] El login **no** muestra cuentas de demostración.
- [ ] Registrar un profesional y subir la cédula funciona. El archivo aparece en el bucket `private-media` de Supabase y el administrador puede verlo.
- [ ] «Mantener mi sesión iniciada» conserva la sesión al recargar. Revísalo especialmente en Streamlit Cloud: la cookie de sesión no se ha probado ahí.
- [ ] Un pago de suscripción en sandbox vuelve al front y muestra el estado real.
- [ ] La tarea de GitHub Actions termina en verde.

---

## Cómo se actualiza después

| Cambio | Qué pasa |
|---|---|
| Push a `main` en `overol-front/` | Streamlit Cloud publica la nueva versión en segundos. Las sesiones abiertas se cierran. |
| Push a `main` en `backend/` | Render reconstruye la imagen y la publica (unos minutos). Si hay migraciones nuevas, se aplican al arrancar. |
| Cambio de dependencias | Igual que el anterior: ambos servicios reinstalan sus `requirements.txt` solos. |
| Push en otras ramas | No se publica nada. Prueben en local con Docker y fusionen a `main` con un Pull Request. |

---

## Límites del plan gratuito

- **Render se duerme** tras 15 minutos sin visitas. La primera petición después tarda unos 30 a 60 segundos. Antes de una presentación, abre el sitio un par de minutos antes.
- **Render Free:** 512 MB de RAM y 750 horas al mes, suficientes para un servicio encendido todo el mes.
- **Streamlit Cloud** duerme la app si pasa varios días sin visitas. Se despierta con un clic en «Yes, get this app back up!». Cada reinicio o publicación cierra las sesiones, porque se guardan en memoria.
- **Supabase Free:** 500 MB de base, 1 GB de archivos y pausa tras 7 días sin actividad (la tarea diaria lo evita).
- **Correo:** el backend imprime los códigos de recuperación de contraseña en su log, porque usa el backend de correo de consola. Para enviarlos de verdad, define en Render `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` y `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` y `DEFAULT_FROM_EMAIL`, con un proveedor SMTP gratuito como Brevo o Gmail con contraseña de aplicación.
- **Webpay** sigue en sandbox: no se hacen cobros reales.
- **Uso comercial:** los planes gratuitos sirven para un proyecto académico o una demo. Para operar como negocio conviene pasar a planes pagados (Render Starter mantiene el servicio siempre despierto).

## Variables de entorno de producción del backend

Además de las de [`backend/.env.example`](backend/.env.example):

| Variable | Para qué sirve |
|---|---|
| `DATABASE_URL` | Conexión completa a PostgreSQL. Si existe, tiene prioridad sobre `POSTGRES_*`. |
| `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Almacenamiento compatible con S3 (Supabase Storage). |
| `S3_MEDIA_BUCKET`, `S3_MEDIA_PUBLIC_URL` | Bucket público de fotos y certificaciones, y su URL pública. |
| `S3_PRIVATE_BUCKET` | Bucket privado de cédulas. Sin `S3_*`, los archivos se guardan en el disco local, como en desarrollo. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes https extra para formularios del admin. El dominio de Render se agrega solo. |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos por CORS. Con `DEBUG=False` y sin lista, no se permite ninguno, y el front no lo necesita porque llama a la API desde su servidor. |
| `RENDER_EXTERNAL_HOSTNAME` | La define Render. Se agrega sola a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`. |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | Correo saliente por SMTP. |
| `PORT`, `WEB_CONCURRENCY` | Puerto y número de procesos de Gunicorn (Render define `PORT`). |
