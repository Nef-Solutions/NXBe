# Publicar Overol gratis

Guía de cómo está publicado Overol sin costo y cómo volver a hacerlo paso a paso. La publicación es automática: cada `git push` a `main` actualiza el sitio.

```text
 Navegador ──► Streamlit Community Cloud ──► Render ──────────► Supabase
               (front, overol-front/)        (backend, Docker)   ├─ PostgreSQL + PostGIS
                                                                 └─ Storage (fotos y cédulas)
 GitHub Actions ── una vez al día ──► vence solicitudes antiguas en la base
```

## Estado actual (publicado el 15-11-2026)

| Parte | Dirección | Servicio y nombre |
|---|---|---|
| Front | <https://overol-nxbe.streamlit.app> | Streamlit Community Cloud, app `overol-nxbe` (cuenta GitHub `Nef-Solutions`) |
| Backend (API) | <https://overol-backend.onrender.com/api/> | Render, servicio web `overol-backend` del Blueprint `overol` |
| Admin de Django | <https://overol-backend.onrender.com/admin/> | Mismo servicio de Render |
| Base de datos y archivos | Panel de Supabase | Organización `NXBe`, proyecto `overol` (ref `ogthnnocigsmdqmgokry`, región `us-east-1`) |
| Tarea diaria | Pestaña **Actions** del repositorio | Flujo `Vencer solicitudes pendientes` |

| Parte | Plan | Se actualiza solo con… |
|---|---|---|
| Front | Gratis | push a `main` |
| Backend | Free | push a `main` que toque `backend/` |
| Base de datos y archivos | Free | No depende del código. Las migraciones las aplica el backend al arrancar. |
| Tarea diaria | Gratis | Se ejecuta todos los días a las 09:00 UTC |

Ninguno de los servicios pidió tarjeta de crédito, y en todos se entra con la cuenta de GitHub.

**Ningún secreto va al repositorio:** contraseña de la base, `DATABASE_URL`, claves de Storage ni clave de Gemini. Cada uno vive solo en el panel del servicio que lo usa.

---

## Paso 1. Supabase: base de datos y archivos

1. Entra a <https://supabase.com> con GitHub.
2. Si la cuenta no tiene organización, crea una con **New organization**: nombre `NXBe`, tipo *Personal* y plan **Free - $0/month**.
3. **New project** dentro de la organización:
   - **Project name:** `overol`
   - **Database password:** Supabase rechaza las contraseñas débiles ("You need a stronger password"). Usa una de 20 caracteres o más, **solo con letras y números**, y **guárdala**: no se vuelve a mostrar. Los símbolos `@ : / ? #` rompen la cadena de conexión.
   - **Region:** abre la lista y elige **East US (North Virginia)** (`us-east-1`), la misma zona que el backend en Render. La opción general "Americas" no permite elegir la zona exacta.
   - **Security → desmarca "Enable Data API".** Django crea sus tablas en el esquema `public`. Con la Data API activa, Supabase las publicaría por su API REST, incluida la de usuarios. Overol no la usa.
   - **Create new project.** Tarda uno o dos minutos hasta que el estado pase a *Healthy*.
4. **Cadena de conexión** (`DATABASE_URL`): botón **Connect** arriba → **Direct** → método **Session pooler**. Copia la URI:

   ```text
   postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres
   ```

   - Reemplaza `[YOUR-PASSWORD]` (con los corchetes) por la contraseña del punto 3. Revisa que no queden espacios al principio ni al final.
   - El usuario debe ser **`postgres.<ref>`**, con el punto y el identificador del proyecto, no solo `postgres`.
   - El servidor (`aws-1-…`) puede variar entre proyectos: copia siempre el que muestra el panel.
   - Usa **Session pooler** y no "Direct connection": la directa solo funciona por IPv6, y Render y GitHub Actions usan IPv4.
5. **Buckets** (menú **Storage** → **Files** → **New bucket**):
   - `media`, con **Public bucket** activado. Guarda fotos de perfil y certificaciones.
   - `private-media`, **sin** activar público. Guarda las cédulas, que solo se leen a través de la API.
6. **Conexión S3** (**Storage** → **S3 Configuration**; la dirección es `…/project/<ref>/storage/s3`):
   - Revisa que esté activado **S3 protocol connection**.
   - Anota el **Endpoint** (`https://<ref>.storage.supabase.co/storage/v1/s3`) y la **Region** (`us-east-1`).
   - En **Access keys** → **New access key** (por ejemplo `render-backend`), anota el **Access key ID** y el **Secret access key**. El secreto se muestra una sola vez.
7. Anota la URL pública del bucket `media`:

   ```text
   https://<ref>.supabase.co/storage/v1/object/public/media
   ```

   `<ref>` es el identificador del proyecto, que aparece en la URL del panel de Supabase.

**PostGIS:** no hay que activarlo a mano. La migración `catalog.0003_enable_postgis` lo activa al primer arranque del backend. Si fallara, actívalo en **Database** → **Extensions** → `postgis`, eligiendo el esquema `public`, y vuelve a desplegar.

### Cambiar la contraseña de la base

**Project Settings** → **Database** → **Reset database password**. Después:

1. Actualiza `DATABASE_URL` en Render (paso 2) y en el secret de GitHub (paso 5).
2. **Espera unos minutos antes de volver a desplegar en Render.** El pooler de Supabase tarda en reconocer la contraseña nueva. Si Render despliega justo después del cambio, falla con `password authentication failed`. En ese caso, espera y usa **Manual Deploy** → **Deploy latest commit**.

---

## Paso 2. Render: backend

1. Entra a <https://dashboard.render.com> con GitHub.
2. **New** → **Blueprint**. Si GitHub no está conectado, haz clic **tú** en **GitHub → Connect account**: se abre una ventana emergente de autorización que los navegadores automatizados bloquean.
3. Si aparece "No repositories found", haz clic en **Configure account** y, en **Repository access** de GitHub, marca `NXBe` (o *All repositories*) → **Save**.
4. Elige `Nef-Solutions/NXBe`. Render lee [`render.yaml`](render.yaml) y propone el servicio `overol-backend` en la rama `main`.
   - **Blueprint Name:** `overol`
   - Valores que Render pide:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | La cadena del paso 1.4 (secreta) |
   | `S3_ENDPOINT_URL` | Endpoint del paso 1.6 |
   | `S3_REGION` | `us-east-1` |
   | `S3_ACCESS_KEY_ID` | Access key ID del paso 1.6 (secreta) |
   | `S3_SECRET_ACCESS_KEY` | Secret access key del paso 1.6 (secreta) |
   | `S3_MEDIA_PUBLIC_URL` | URL del paso 1.7 |
   | `GEMINI_API_KEY` | Clave de <https://aistudio.google.com/apikey> (secreta). Si queda vacía, el asistente avisa que no está disponible y lo demás funciona. |
   | `TRANSBANK_RETURN_URL` | `https://overol-backend.onrender.com/api/payments/transbank/return/`. Si Render asigna otra URL al servicio, se corrige en el paso 4. |
   | `PAYMENT_RESULT_URL` | Provisorio: `https://example.com/`. Se completa en el paso 4. |

   Al salir de cada casilla, Render oculta el valor con puntos (`••••`). Es normal y el valor queda guardado.

   `SECRET_KEY` lo genera Render solo. `DEBUG=False`, `WEB_CONCURRENCY` y los nombres de los buckets ya vienen en `render.yaml`.
5. **Deploy Blueprint.** El primer despliegue construye la imagen de `backend/Dockerfile` y aplica todas las migraciones en Supabase. El log termina con `Your service is live 🎉`.
6. Comprueba que esta dirección devuelve la lista de oficios en JSON:

   ```text
   https://overol-backend.onrender.com/api/catalog/categories/
   ```

**Cambiar variables después:** servicio **overol-backend** → **Environment** → **Edit** → cambiar el valor → **Save, rebuild, and deploy**.

### Crear el administrador

El plan gratuito de Render no tiene consola. El superusuario se crea **una sola vez** desde un PC, conectándote a la base de Supabase con Docker. Queda guardado en Supabase y sirve desde cualquier computador.

Desde la raíz del repositorio, con Docker Desktop abierto:

1. **Guardar la conexión solo en esa ventana**, para que la contraseña no quede en los comandos. Reemplaza `TU-CONTRASEÑA`:
   - En **PowerShell** (el prompt empieza con `PS`):
     ```powershell
     $env:DATABASE_URL = "postgresql://postgres.<ref>:TU-CONTRASEÑA@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
     ```
   - En **CMD** (Símbolo del sistema):
     ```bat
     set "DATABASE_URL=postgresql://postgres.<ref>:TU-CONTRASEÑA@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
     ```
2. **Crear el superusuario.** `-e DATABASE_URL` sin valor pasa la variable del paso 1. El comando pide, en este orden: correo, *username*, nombre, apellido y contraseña (dos veces).
   ```powershell
   docker compose run --rm --no-deps -e DATABASE_URL backend python manage.py createsuperuser
   ```
3. **Darle el rol Administrador.** Django crea los superusuarios con el rol *Cliente*, y el panel de administración del front exige *Administrador*. Este comando se lo asigna a todos los superusuarios:
   ```powershell
   docker compose run --rm --no-deps -e DATABASE_URL backend python manage.py shell -c "from apps.authentication.models import User; n = User.objects.filter(is_superuser=True).update(role=User.Role.ADMIN); print('Administradores actualizados:', n)"
   ```
4. Probar en `https://overol-backend.onrender.com/admin/` y en el front, con "Ingresar".

Con `DATABASE_URL`, el contenedor ignora la base local y escribe en la de Supabase. Así se ejecuta cualquier comando de Django contra producción, así que hazlo con cuidado.

**Más administradores:** no hace falta repetir los comandos. En `/admin/` → **Usuarios**, abre o crea el usuario y, en **Permisos y Rol**, cambia **Rol** a *Administrador*. Si además debe entrar al admin de Django, marca **Es staff** (y **Es superusuario** si corresponde).

**En local es distinto:** cada PC tiene su propia base en Docker, sin el superusuario de producción. Ahí se usa `docker compose exec backend python manage.py seed_demo`, que crea `admin@demo.overol.cl` con la contraseña `OverolDemo123!`, o `docker compose exec backend python manage.py createsuperuser`.

**Datos de demostración:** `seed_demo` crea cuentas con una contraseña que es pública, porque está en el repositorio. Para una demo académica se pueden cargar con el mismo comando, cambiando `createsuperuser` por `seed_demo`. Si el sitio va a recibir usuarios reales, no lo hagas.

---

## Paso 3. Streamlit Community Cloud: front

1. Entra a <https://share.streamlit.io> → **Continue to sign-in** → **Continue with GitHub**, y autoriza el acceso al repositorio.
2. **Create app** → **Deploy a public app from GitHub**:
   - **Repository:** `Nef-Solutions/NXBe`
   - **Branch:** `main`
   - **Main file path:** `overol-front/app.py`
   - **App URL:** `overol-nxbe`, que da `https://overol-nxbe.streamlit.app`.
3. **Advanced settings**:
   - **Python version:** **3.11**, la misma de la imagen Docker del front y de sus pruebas. Streamlit propone 3.14 por defecto.
   - **Secrets:**

     ```toml
     OVEROL_API_URL = "https://overol-backend.onrender.com/api/"
     OVEROL_API_TIMEOUT = "60"
     OVEROL_COOKIE_SECURE = "1"
     OVEROL_MODO_DEMO = "0"
     OVEROL_STREAMLIT_STARTED = "1"
     ```

     - `OVEROL_API_TIMEOUT = "60"`: el backend gratuito de Render se duerme y tarda hasta un minuto en despertar. Con el valor por defecto (10 segundos), la primera visita mostraría un error.
     - `OVEROL_STREAMLIT_STARTED = "1"`: evita que `app.py` intente lanzar otra instancia de Streamlit. `app.py` también lo detecta solo; este secret es una protección adicional.
   - **Save.** Espera a que se cierre el cuadro antes de presionar **Deploy**: si se presiona con el cuadro abierto, la app no se crea.
4. **Deploy.** Streamlit instala `overol-front/requirements.txt` y publica en uno o dos minutos.

**Cambiar los secrets después:** en <https://share.streamlit.io>, menú **⋮** de la app → **Settings** → **Secrets**.

**Importante:**
- **No uses espacios en la ruta del front.** Streamlit Cloud separa la ruta por los espacios. Con la carpeta antigua `Overol Front/` intentaba instalar `Front/requirements.txt` y fallaba con "Error installing requirements". Por eso la carpeta se llama `overol-front`.
- **La ruta del archivo principal no se puede cambiar** en una app existente. Si cambia, hay que borrar la app (menú **⋮** → **Delete**) y crearla de nuevo con la misma URL.

---

## Paso 4. Conectar el pago de Webpay con el front

En Render, servicio **overol-backend** → **Environment** → **Edit**:

| Variable | Valor actual |
|---|---|
| `PAYMENT_RESULT_URL` | `https://overol-nxbe.streamlit.app/` |
| `TRANSBANK_RETURN_URL` | `https://overol-backend.onrender.com/api/payments/transbank/return/` |

**Save, rebuild, and deploy.**

---

## Paso 5. Tarea diaria en GitHub Actions

El flujo [`.github/workflows/vencer-solicitudes.yml`](.github/workflows/vencer-solicitudes.yml) vence cada día las solicitudes pendientes con más de 30 días. Además mantiene activa la base de Supabase, que en el plan gratuito se pausa tras 7 días sin uso.

1. En GitHub: repositorio → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
   - **Name:** `DATABASE_URL`
   - **Secret:** la misma cadena del paso 1.4.
2. Pestaña **Actions** → **Vencer solicitudes pendientes** → **Run workflow** (rama `main`) para probarlo una vez. Debe terminar en verde en unos 30 segundos.

Si falta el secret, la tarea termina sin hacer nada. GitHub desactiva las tareas programadas si el repositorio pasa 60 días sin actividad; se reactivan desde la misma pestaña.

---

## Paso 6. Comprobar que quedó bien

Ya comprobado al publicar:

- [x] `https://overol-backend.onrender.com/api/catalog/categories/` responde con la lista de oficios.
- [x] `https://overol-backend.onrender.com/admin/` carga con estilos.
- [x] La portada del front carga por https y muestra los oficios, lo que confirma que el front llega al backend.
- [x] Las migraciones, incluida PostGIS, se aplicaron en Supabase.
- [x] La tarea de GitHub Actions termina en verde.

- [x] Superusuario creado en producción y con el rol Administrador.

Pendiente de probar:

- [ ] Entrar a `/admin/` y al panel de administración del front con el superusuario.
- [ ] El login **no** muestra cuentas de demostración.
- [ ] Registrar un profesional y subir la cédula. El archivo debe aparecer en el bucket `private-media` y el administrador debe poder verlo.
- [ ] «Mantener mi sesión iniciada» conserva la sesión al recargar. La cookie de sesión no se ha probado en Streamlit Cloud.
- [ ] Un pago de suscripción en sandbox vuelve al front y muestra el estado real.

---

## Cómo se actualiza después

| Cambio | Qué pasa |
|---|---|
| Push a `main` en `overol-front/` | Streamlit Cloud publica la nueva versión en segundos. Las sesiones abiertas se cierran. |
| Push a `main` en `backend/` | Render reconstruye la imagen y la publica (unos minutos). Si hay migraciones nuevas, se aplican al arrancar. |
| Cambio de dependencias | Igual que el anterior: ambos servicios reinstalan sus `requirements.txt` solos. |
| Push en otras ramas | No se publica nada. Prueben en local con Docker ([DOCKER.md](DOCKER.md)) y fusionen a `main` con un Pull Request. |

---

## Problemas encontrados y cómo se resolvieron

| Síntoma | Causa | Solución |
|---|---|---|
| Render: `password authentication failed for user "postgres"` | Usuario sin `.<ref>`, contraseña equivocada o recién cambiada | Revisar la cadena del paso 1.4. Si se cambió la contraseña, esperar unos minutos y usar **Manual Deploy → Deploy latest commit**. |
| Render: "No repositories found" | La app de Render en GitHub no tenía acceso al repositorio | **Configure account** → marcar `NXBe` → **Save** |
| Render: "Connect account" no abre nada | Ventana emergente bloqueada | Hacer el clic a mano, fuera de la automatización |
| Streamlit: "Error installing requirements" | Espacio en la ruta del front | Carpeta sin espacios (`overol-front`) y crear la app de nuevo |
| Streamlit: la app no aparece después de Deploy | Se presionó Deploy con el cuadro de Advanced settings abierto | Guardar, esperar a que se cierre el cuadro y volver a presionar Deploy |
| Actions: `No such file or directory` en `backend` | El flujo entraba a `backend/` antes de descargar el código | Ya corregido: el primer paso descarga el código |
| `$env:DATABASE_URL = ...` da "La sintaxis … no es correcta" | La ventana es CMD, no PowerShell | En CMD se usa `set "DATABASE_URL=..."` |
| `User matching query does not exist` al asignar el rol | El comando tenía un correo de ejemplo | Usar el comando que actualiza a todos los superusuarios (paso 3 de "Crear el administrador") |

---

## Límites del plan gratuito

- **Render se duerme** tras 15 minutos sin visitas. La primera petición después tarda unos 30 a 60 segundos. Antes de una presentación, abre el sitio un par de minutos antes.
- **Render Free:** 512 MB de RAM y 750 horas al mes, suficientes para un servicio encendido todo el mes. No tiene consola (Shell).
- **Streamlit Cloud** duerme la app si pasa varios días sin visitas. Se despierta con un clic en «Yes, get this app back up!». Cada reinicio o publicación cierra las sesiones, porque se guardan en memoria.
- **Supabase Free:** 500 MB de base, 1 GB de archivos (50 MB por archivo) y pausa tras 7 días sin actividad (la tarea diaria lo evita).
- **Correo:** el backend imprime los códigos de recuperación de contraseña en su log de Render, porque usa el backend de correo de consola. Para enviarlos de verdad, define en Render `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` y `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` y `DEFAULT_FROM_EMAIL`, con un proveedor SMTP gratuito como Brevo o Gmail con contraseña de aplicación.
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
