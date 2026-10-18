# Instalación y puesta en marcha en otro computador

Esta guía prepara el backend de Overol desde cero en un computador nuevo.

## 1. Requisitos previos

Instalar y comprobar:

| Herramienta | Uso | Comprobación |
| :--- | :--- | :--- |
| Git | Descargar el repositorio. | `git --version` |
| Python 3.14 | Ejecutar Django. | `python --version` |
| Docker Desktop | Ejecutar PostgreSQL/PostGIS y Redis. | `docker --version` |
| Docker Compose | Orquestar los servicios. | `docker compose version` |

En Windows, Docker Desktop debe estar abierto y ejecutándose antes de continuar.

## 2. Descargar el proyecto

Clonar el repositorio y entrar en su carpeta:

```powershell
git clone <URL_DEL_REPOSITORIO>
Set-Location overol-backend/backend
```

El repositorio contiene material de proyecto en la raíz y el código ejecutable dentro de `backend/`. Todos los comandos Django y Docker de esta guía se ejecutan desde `backend/`, donde están `manage.py` y `docker-compose.yml`.

Si el proyecto se entrega como ZIP, descomprimirlo y entrar a la carpeta `backend`, que contiene `manage.py`.

## 3. Configurar variables locales

Crear el archivo `.env` a partir de la plantilla incluida:

```powershell
Copy-Item .env.example .env
```

Para desarrollo local se pueden conservar los valores de la plantilla, aunque se recomienda cambiar `SECRET_KEY` y `POSTGRES_PASSWORD` cuando el proyecto se use fuera del computador del equipo. El archivo `.env` no debe subirse a GitHub.

## 4. Crear un entorno virtual

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación de scripts, ejecutar una vez como usuario:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Luego activar nuevamente:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux o macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 5. Instalar dependencias Python

El archivo de dependencias está dentro de `documentacion`:

```powershell
python -m pip install --upgrade pip
python -m pip install -r documentacion/requirements.txt
```

En Linux o macOS se puede usar el mismo comando con `python3` si `python` no apunta a Python 3.

## 6. Levantar servicios de infraestructura

Desde la raíz del proyecto:

```powershell
docker compose up -d
```

Esto inicia:

- PostgreSQL 16 con PostGIS en `localhost:5432`.
- Redis 7 en `localhost:6379`.

Comprobar el estado:

```powershell
docker compose ps
```

Los servicios deben aparecer en estado `running` o `healthy` según la versión de Docker.

## 7. Aplicar la base de datos

Ejecutar las migraciones:

```powershell
python manage.py migrate
```

Validar la configuración:

```powershell
python manage.py check
```

Para crear un administrador del panel:

```powershell
python manage.py createsuperuser
```

El panel administrativo quedará en `http://127.0.0.1:8000/admin/`.

## 8. Ejecutar pruebas

```powershell
python manage.py test
```

Las pruebas crean una base temporal y no deberían borrar la base de desarrollo.

## 9. Iniciar el backend

```powershell
python manage.py runserver
```

URLs principales:

- API: `http://127.0.0.1:8000/api/`
- Administración: `http://127.0.0.1:8000/admin/`
- Archivos de desarrollo: `http://127.0.0.1:8000/media/`

Para permitir conexiones desde otro dispositivo de la misma red local:

```powershell
python manage.py runserver 0.0.0.0:8000
```

En ese caso se debe acceder usando la IP del computador servidor y permitir el puerto `8000` en el firewall si Windows lo solicita.

## 10. Vencimiento de solicitudes

El comando revisa solicitudes pendientes con más de 30 días:

```powershell
python manage.py expire_visit_requests
```

Para automatizarlo se debe programar ese comando con el Programador de tareas de Windows, cron o un scheduler de producción. El proyecto no incluye todavía un proceso permanente para ejecutarlo automáticamente.

## 11. Configuración actual de base de datos

La configuración actual de desarrollo usa los valores definidos en `core/settings.py`:

| Variable lógica | Valor de desarrollo |
| :--- | :--- |
| Motor | PostgreSQL |
| Base de datos | `overol_db` |
| Usuario | `overol_user` |
| Contraseña | `overol_password` |
| Host | `localhost` |
| Puerto | `5432` |

No se deben reutilizar estas credenciales en producción. Antes de desplegar en un entorno real es necesario moverlas a variables de entorno y cambiar también `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` y CORS.

## 12. Problemas frecuentes

### `No module named django`

Activar `.venv` e instalar dependencias:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r documentacion/requirements.txt
```

### `relation ... does not exist`

Las migraciones no están aplicadas:

```powershell
python manage.py migrate
```

### No se puede conectar a PostgreSQL

Comprobar Docker:

```powershell
docker compose ps
docker compose logs db
```

Si los servicios no están activos:

```powershell
docker compose up -d
```

### El puerto `5432`, `6379` o `8000` está ocupado

Detener el proceso que usa el puerto o cambiar el mapeo en `docker-compose.yml`. Si se cambia el puerto de PostgreSQL, también debe actualizarse `PORT` en `core/settings.py`.

### Reiniciar la base de datos local

Esto elimina todos los datos de desarrollo:

```powershell
docker compose down -v
docker compose up -d
python manage.py migrate
```

## 13. Alcance no incluido

Esta guía no configura suscripciones, pagos, chatbot, IA ni geolocalización real porque esas áreas están fuera del alcance actual del proyecto.