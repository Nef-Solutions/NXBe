# Imagen del backend de Overol (Django + Gunicorn).
# Se usa desde el docker-compose.yml de la raíz del repositorio; ver DOCKER.md.
#   docker build -t overol-backend .
#   docker run -p 8000:8000 --env-file .env -e POSTGRES_HOST=<host-de-la-base> overol-backend
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero: así Docker reutiliza esta capa mientras requirements.txt no cambie
COPY documentacion/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

# Archivos estáticos del admin de Django (los sirve WhiteNoise dentro de Gunicorn)
RUN python manage.py collectstatic --noinput

# Sin privilegios de administrador dentro del contenedor. Las carpetas de archivos subidos
# deben existir y pertenecer al usuario para que los volúmenes hereden el permiso.
RUN useradd --create-home --uid 10001 overol \
    && mkdir -p media private_media \
    && chown -R overol:overol /app
USER overol

EXPOSE 8000

# Aplica las migraciones pendientes y arranca Gunicorn. PORT lo definen algunos
# proveedores (por ejemplo Render); en local se usa 8000.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --access-logfile -"]
