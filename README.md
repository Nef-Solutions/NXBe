# Overol

Proyecto Capstone del equipo NXBe para conectar clientes con profesionales de oficios del hogar. Overol permite buscar profesionales, solicitar visitas, coordinar servicios, evaluar resultados y gestionar situaciones de posventa.

Este repositorio reúne el producto, sus dos implementaciones de desarrollo y los documentos del proceso académico:

- Un prototipo integral local para demostraciones.
- Un backend REST modular preparado para evolucionar hacia una arquitectura productiva.
- Requisitos, diseño, evidencias y entregables de las distintas fases del proyecto.

## Componentes del proyecto

### Prototipo integral

La carpeta [Overol](Overol/) contiene una aplicación Streamlit ejecutable localmente. Incluye pantallas para clientes, profesionales y administradores, autenticación local y persistencia SQLite para demostraciones. Es la forma más rápida de explorar el flujo completo de la plataforma.

### Backend REST

La carpeta [backend](backend/) contiene una API desarrollada con Django y Django REST Framework. Usa PostgreSQL/PostGIS y Redis mediante Docker, JWT para las rutas protegidas y una estructura modular por dominio:

- `authentication`: usuarios, roles, sesiones y verificación profesional.
- `catalog`: oficios, especialidades y búsqueda.
- `visits`: visitas, reseñas, posventa, soporte y notificaciones.
- `assistant`: espacio reservado para el asistente de diagnóstico.

El backend implementa registro, autenticación, perfiles profesionales, solicitudes de visita, calificaciones, reclamos, tickets y administración.

### Documentación y entregables

- [Documentos_equipo](Documentos_equipo/): visión del producto, backlog, diseño, Definition of Done y requisitos funcionales y no funcionales.
- [Fase 1](Fase%201/): evidencias grupales e individuales de la primera fase.
- [Fase 2](Fase%202/): evidencias grupales e individuales de la segunda fase.
- [Documentación técnica del backend](backend/documentacion/): instalación, arquitectura, API, base de datos, Docker y pruebas.

## Estructura general

```text
overol-backend/
├── Overol/                  # Prototipo Streamlit con SQLite para demostraciones
├── backend/                 # API Django, infraestructura y documentación técnica
├── Documentos_equipo/       # Documentos de producto, requisitos y diseño
├── Fase 1/                 # Evidencias y entregables de la primera fase
├── Fase 2/                 # Evidencias y entregables de la segunda fase
└── readme.md               # Guía general del proyecto
```

## Requisitos

- Git
- Python 3.14
- Docker Desktop y Docker Compose para ejecutar el backend

En Windows, Docker Desktop debe estar abierto antes de iniciar los servicios del backend.

## Ejecutar el prototipo

El prototipo instala Streamlit automáticamente si no está disponible. Desde la raíz del repositorio:

```powershell
Set-Location Overol
python app.py
```

También se puede iniciar directamente con:

```powershell
streamlit run app.py
```

La aplicación se abrirá en la dirección local indicada por Streamlit. Sus datos de demostración se almacenan en SQLite dentro del prototipo y no reemplazan la persistencia del backend.

## Ejecutar el backend

Todos los comandos del backend se ejecutan desde `backend/`:

```powershell
Set-Location backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r documentacion/requirements.txt
docker compose up -d
python manage.py migrate
python manage.py check
python manage.py runserver
```

URLs locales:

- API: `http://127.0.0.1:8000/api/`
- Administración: `http://127.0.0.1:8000/admin/`

Para crear un administrador:

```powershell
python manage.py createsuperuser
```
## Pruebas

Desde `backend/`:

```powershell
python manage.py test
```

Las pruebas del backend utilizan una base de datos temporal. El prototipo local utiliza su propia base SQLite para las demostraciones.

## Funcionalidades y alcance

El proyecto contempla registro y verificación profesional, búsqueda y categorización, perfiles, solicitudes, reputación, centro de desarrollo profesional, administración, posventa y reclamos.

Todavía están fuera del alcance implementado las suscripciones, los pagos, el chatbot con IA y la geolocalización real con mapas o radios de cobertura. El prototipo puede mostrar flujos de estas épicas, pero el backend aún no las implementa como funcionalidades productivas.

## API

La API usa JSON y JWT para las rutas protegidas:

```http
Authorization: Bearer <access_token>
```

Prefijos principales:

| Prefijo | Funcionalidad |
| :--- | :--- |
| `/api/auth/` | Registro, autenticación, perfiles y verificación |
| `/api/catalog/` | Catálogo y búsqueda de profesionales |
| `/api/requests/` | Solicitudes y estados de visitas |
| `/api/ratings/` | Calificaciones y reseñas |
| `/api/claims/` | Reclamos de posventa |
| `/api/tickets/` | Soporte |
| `/api/notifications/` | Notificaciones internas |
| `/api/professional-center/` | Contenido y progreso profesional |

Consulta el [contrato completo de la API](backend/documentacion/api.md) para conocer endpoints, cuerpos de petición, respuestas y permisos.

## Documentación

- [Índice de documentación del backend](backend/documentacion/README.md)
- [Instalación en otro computador](backend/documentacion/instalacion.md)
- [Arquitectura](backend/documentacion/arquitectura.md)
- [Contrato de API](backend/documentacion/api.md)
- [Base de datos](backend/documentacion/base-de-datos.md)
- [Docker](backend/documentacion/docker.md)
- [Pruebas](backend/documentacion/pruebas.md)
- [Estado de la Definition of Done](backend/documentacion/estado-dod.md)
- [Propuesta Capstone](backend/propuesta_capstone_overol.md)

## Seguridad y mantenimiento

No subir `backend/.env` al repositorio. Para configurar otro computador, copiar `backend/.env.example` y completar los valores locales.

Las credenciales de desarrollo no deben reutilizarse en producción. Antes de desplegar se deben cambiar `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, CORS y las credenciales de la base de datos.

Las solicitudes pendientes con más de 30 días pueden marcarse como vencidas desde `backend/`:

```powershell
python manage.py expire_visit_requests
```
