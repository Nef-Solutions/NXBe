# Servicios Docker de Overol

Este documento explica cómo operar los servicios que necesita el backend. Para preparar un computador nuevo desde cero, revisar [instalacion.md](instalacion.md).

## Servicios

### PostgreSQL/PostGIS

- Servicio Compose: `db`
- Contenedor: `overol_db`
- Imagen: `postgis/postgis:16-3.4`
- Base de datos: `overol_db`
- Usuario: `overol_user`
- Puerto local: `5432`
- Volumen: `postgres_data`

### Redis

- Servicio Compose: `redis`
- Contenedor: `overol_redis`
- Imagen: `redis:7-alpine`
- Puerto local: `6379`

Redis está preparado para caché y futuras tareas asíncronas. La ejecución actual del comando de vencimiento se realiza mediante `manage.py`.

## Comandos habituales

Ejecutar desde la raíz del proyecto, donde está `docker-compose.yml`.

### Iniciar servicios

```powershell
docker compose up -d
```

### Revisar estado

```powershell
docker compose ps
```

### Ver logs de PostgreSQL

```powershell
docker compose logs db
```

### Ver logs de Redis

```powershell
docker compose logs redis
```

### Detener sin borrar datos

```powershell
docker compose stop
```

### Detener y recrear conservando el volumen

```powershell
docker compose down
docker compose up -d
```

### Borrar todos los datos locales

> Este comando elimina el volumen de PostgreSQL y todos los datos de desarrollo.

```powershell
docker compose down -v
docker compose up -d
python manage.py migrate
```

## Conectar Django con PostgreSQL

La configuración actual de desarrollo usa:

```text
Host: localhost
Puerto: 5432
Base de datos: overol_db
Usuario: overol_user
Contraseña: overol_password
```

Después de iniciar el contenedor, aplicar migraciones:

```powershell
python manage.py migrate
```

## Solución de problemas

### El contenedor no inicia

```powershell
docker compose ps
docker compose logs db
```

### El puerto ya está ocupado

Liberar el puerto `5432` o `6379`, o cambiar el mapeo en `docker-compose.yml`. Si se cambia el puerto de PostgreSQL, actualizar también `PORT` en `core/settings.py`.

### Django indica que no existe una tabla

Aplicar migraciones:

```powershell
python manage.py migrate
```

### Reinicio limpio de desarrollo

```powershell
docker compose down -v
docker compose up -d
python manage.py migrate
```
