# Overol con Docker

Guía para levantar Overol con Docker y para trabajar en él, según si tu parte es el **front** (Streamlit) o el **backend** (Django).

Docker es opcional: la forma anterior, con `venv` y solo la base de datos en Docker, sigue funcionando igual. Está descrita en [backend/readme.md](backend/readme.md) y en [overol-front/README.md](overol-front/README.md).

---

## 1. Qué levanta Docker

| Servicio | Qué es | Dirección en tu PC | Nombre dentro de Docker |
|---|---|---|---|
| `db` | PostgreSQL 16 + PostGIS | `localhost:5432` | `db:5432` |
| `backend` | API Django | `http://localhost:8000` (API en `/api/`, admin en `/admin/`) | `http://backend:8000` |
| `front` | Front Streamlit | `http://localhost:8501` | `http://front:8501` |

Archivos involucrados:

| Archivo | Para qué sirve |
|---|---|
| [`docker-compose.yml`](docker-compose.yml) (raíz) | Define `backend` y `front`, e incluye la base de `backend/docker-compose.yml`. |
| [`docker-compose.override.yml`](docker-compose.override.yml) (raíz) | Modo **desarrollo**: monta el código y recarga al guardar. Docker Compose lo aplica solo. |
| [`backend/docker-compose.yml`](backend/docker-compose.yml) | Solo la base de datos. Lo usan las dos formas de trabajo, así que comparten la misma base y los mismos datos. |
| [`backend/Dockerfile`](backend/Dockerfile) | Imagen del backend: Python 3.14, Gunicorn y migraciones al arrancar. |
| [`overol-front/Dockerfile`](overol-front/Dockerfile) | Imagen del front: Python 3.11 y Streamlit. |

---

## 2. Requisitos y primera vez

1. Instalar **Docker Desktop** y dejarlo abierto. En Windows, antes de usar cualquier comando `docker`, debe aparecer el ícono de la ballena en la bandeja.
2. Clonar el repositorio y crear el archivo de variables del backend:

   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

   Rellena en `backend/.env` lo que necesites, por ejemplo `GEMINI_API_KEY` para el asistente Overil. Si no existe `backend/.env`, todo arranca igual con los valores por defecto.

   No hace falta cambiar `POSTGRES_HOST`: dentro de Docker, el `docker-compose.yml` lo reemplaza por `db`.

3. Levantar todo desde la **raíz** del repositorio:

   ```powershell
   docker compose up --build
   ```

   La primera vez tarda unos minutos porque descarga las imágenes e instala las dependencias. Después es mucho más rápido.

4. Cargar los usuarios de demostración (solo la primera vez, o después de borrar la base):

   ```powershell
   docker compose exec backend python manage.py seed_demo
   ```

   Todos usan la contraseña `OverolDemo123!`. Los correos están en [overol-front/README.md](overol-front/README.md#usuarios-de-demostración).

Abre `http://localhost:8501`. En modo desarrollo, el login muestra botones con las cuentas de demostración.

---

## 3. Comandos del día a día

Todos se ejecutan desde la raíz del repositorio.

| Quiero… | Comando |
|---|---|
| Levantar todo | `docker compose up` (agrega `-d` para que quede en segundo plano) |
| Levantar todo tras cambiar `requirements.txt` o un `Dockerfile` | `docker compose up --build` |
| Ver qué está corriendo | `docker compose ps` |
| Ver los mensajes del backend (incluye los códigos de recuperación de contraseña) | `docker compose logs -f backend` |
| Detener todo (los datos se mantienen) | `docker compose down` |
| Ejecutar un comando de Django | `docker compose exec backend python manage.py <comando>` |
| Crear un superusuario para `/admin/` | `docker compose exec backend python manage.py createsuperuser` |
| Crear migraciones nuevas | `docker compose exec backend python manage.py makemigrations` |
| Vencer solicitudes pendientes antiguas | `docker compose exec backend python manage.py expire_visit_requests` |
| Abrir una consola dentro del backend | `docker compose exec backend sh` |
| **Borrar la base y los archivos subidos** y partir de cero | `docker compose down -v` ⚠️ elimina todos los datos locales |

**¿Cuándo hay que reconstruir con `--build`?** Solo cuando cambian las dependencias (`requirements.txt`) o un `Dockerfile`. Para cambios de código basta con guardar el archivo (ver la sección 6).

---

## 4. Si trabajas en el FRONT

No necesitas instalar Django ni PostgreSQL: Docker te da la API funcionando.

### Opción A: todo en Docker (recomendada)

```powershell
docker compose up
```

Edita los archivos de `overol-front/` con tu editor. Al guardar, Streamlit recarga la página solo, porque el modo desarrollo monta la carpeta dentro del contenedor. Los errores se muestran completos en el navegador y en `docker compose logs -f front`.

### Opción B: front en tu PC y API en Docker

Útil si quieres usar el depurador de tu editor sobre el front.

```powershell
docker compose up -d db backend      # base + API en Docker
cd "overol-front"
pip install -r requirements.txt      # solo la primera vez
python app.py                        # usa http://127.0.0.1:8000/api/ por defecto
```

Si el contenedor `front` estaba corriendo, detenlo antes (`docker compose stop front`), porque usa el mismo puerto 8501.

### Pruebas del front

Las pruebas automáticas no necesitan el backend, porque usan uno simulado. Desde `overol-front/`:

```powershell
python tests/correr_pruebas.py
```

---

## 5. Si trabajas en el BACKEND

### Opción A: todo en Docker (recomendada)

```powershell
docker compose up
```

Edita los archivos de `backend/` con tu editor. Al guardar, Django reinicia el servidor solo (`runserver` con recarga automática). Las migraciones pendientes se aplican cada vez que arranca el contenedor.

Pruebas y verificaciones dentro del contenedor:

```powershell
docker compose exec backend python manage.py test
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
```

### Opción B: backend con tu `venv` y base en Docker (la forma de siempre)

Desde `backend/`, sin cambios respecto a antes:

```powershell
docker compose up -d db
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

En este caso `backend/.env` debe tener `POSTGRES_HOST=localhost`, como viene en `.env.example`. Usa la misma base y los mismos datos que la opción A.

Si además quieres el front en Docker apuntando a tu `runserver`:

1. Agrega `host.docker.internal` a `ALLOWED_HOSTS` en `backend/.env`.
2. Desde la raíz, ejecuta:

   ```powershell
   $env:OVEROL_API_URL = "http://host.docker.internal:8000/api/"
   docker compose up --no-deps front
   ```

---

## 6. Desarrollo frente a producción

Al ejecutar `docker compose up`, Docker combina `docker-compose.yml` con `docker-compose.override.yml`. Ese segundo archivo es el **modo desarrollo**:

| | Desarrollo (`docker compose up`) | Producción (`docker compose -f docker-compose.yml up --build`) |
|---|---|---|
| Código | Montado desde tu carpeta: los cambios se ven al guardar | Copiado dentro de la imagen: hay que reconstruir |
| Servidor del backend | `runserver` (recarga automática) | Gunicorn + WhiteNoise para los archivos estáticos |
| Front | Errores completos, menú de desarrollador y cuentas de demostración en el login | Errores ocultos, sin menú ni cuentas de demostración |

Usa el modo producción para comprobar que las imágenes funcionan antes de publicarlas (por ejemplo en Render). Las variables para publicar el front están en [overol-front/DESPLIEGUE.md](overol-front/DESPLIEGUE.md).

---

## 7. Datos: dónde quedan

- **Base de datos:** volumen `overol-backend_postgres_data`. Sobrevive a `docker compose down`, a los reinicios y a los `--build`. Solo se borra con `docker compose down -v`.
- **Archivos subidos** (fotos, certificaciones y cédulas): volúmenes `overol-backend_media_data` y `overol-backend_private_media_data`. Se borran igual, solo con `down -v`.
- Cada PC tiene su propia base. Nadie ve los datos de otro, y para partir todos iguales está `seed_demo`.

---

## 8. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `failed to connect to the docker API` o `cannot find the file specified` | Docker Desktop no está abierto. Ábrelo y espera a que termine de iniciar. |
| `Conflict. The container name "/overol_db" is already in use` | Otra copia del proyecto, o una versión antigua, tiene su propia base corriendo con ese nombre. Revisa con `docker ps -a`, detenla con `docker stop overol_db` y bórrala con `docker rm overol_db`. Borrar el contenedor no borra su volumen, pero esa base antigua usa otro volumen (por ejemplo `backend_postgres_data`), así que sus datos no aparecerán aquí. Vuelve a cargar `seed_demo`. |
| `port is already allocated` (5432, 8000 u 8501) | Hay otro programa usando el puerto: un PostgreSQL instalado en Windows, un `runserver` o un `streamlit` abiertos. Ciérralo o detén ese contenedor. |
| El front dice que no puede conectarse al backend | Revisa `docker compose ps` y `docker compose logs backend`. Si cambiaste `OVEROL_API_URL` en la terminal, ciérrala o ejecuta `Remove-Item Env:OVEROL_API_URL`. |
| `Invalid HTTP_HOST header` | El nombre con que se llama al backend no está en `ALLOWED_HOSTS`. Dentro de Docker ya se agrega `backend`. Para `host.docker.internal`, ver la sección 5. |
| Instalé una librería y el contenedor dice que no existe | Agrégala al `requirements.txt` que corresponda y ejecuta `docker compose up --build`. |
| El backend no arranca y el log muestra un error de la base | Normalmente la base todavía está iniciando: el backend la espera con un *healthcheck*. Si cambiaste las credenciales de `backend/.env` después de crear la base, el volumen conserva las antiguas. Vuelve a las anteriores o borra la base con `docker compose down -v`. |
