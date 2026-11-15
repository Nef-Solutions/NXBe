# Overol

Proyecto Capstone del equipo NXBe para conectar clientes con profesionales de oficios del hogar. Overol permite buscar profesionales, solicitar visitas, coordinar servicios, evaluar resultados y gestionar situaciones de posventa.

Este repositorio reúne el producto y los documentos del proceso académico:

- Un **front** en Streamlit que consume la API del backend.
- Un **backend** REST modular en Django.
- Requisitos, diseño, evidencias y entregables de las distintas fases del proyecto.

## Sitio publicado

| Parte | Dirección |
|---|---|
| Aplicación (front) | <https://overol-nxbe.streamlit.app> |
| API | <https://overol-backend.onrender.com/api/> |
| Admin de Django | <https://overol-backend.onrender.com/admin/> |

Se publica solo con cada push a `main`, con planes gratuitos de Streamlit Community Cloud, Render y Supabase. El backend gratuito se duerme tras 15 minutos sin uso, así que la primera visita puede tardar hasta un minuto. Detalles, configuración y cómo rehacerlo en [HOSTING.md](HOSTING.md).

## Componentes del proyecto

### Front (Streamlit)

La carpeta [overol-front](overol-front/) contiene la aplicación web en Streamlit, con pantallas para visitantes, clientes, profesionales y administradores. Todos los datos vienen del backend a través de su API REST con JWT: el front no guarda datos propios.

La versión anterior, que funcionaba sola con SQLite, quedó en el tag `front-modo-local-final`.

### Backend REST (Django)

La carpeta [backend](backend/) contiene una API desarrollada con Django y Django REST Framework. Usa PostgreSQL/PostGIS en Docker, JWT para las rutas protegidas y una estructura modular por dominio:

- `authentication`: usuarios, roles, perfiles, sesiones, recuperación de contraseña y verificación profesional.
- `catalog`: oficios, especialidades, búsqueda (incluida la búsqueda por radio con PostGIS) y disponibilidad.
- `visits`: solicitudes de visita, reseñas, posventa, soporte, notificaciones y centro profesional.
- `assistant`: Overil, asistente que recomienda un oficio del catálogo usando Gemini.
- `payments`: suscripción mensual de profesionales con Webpay Plus en modo de pruebas (sandbox).

### Documentación y entregables

- [Documentos_equipo](Documentos_equipo/): visión del producto, backlog, diseño, Definition of Done y requisitos funcionales y no funcionales.
- [Fase 1](Fase%201/): evidencias grupales e individuales de la primera fase.
- [Fase 2](Fase%202/): evidencias grupales e individuales de la segunda fase. La presentación y el video se guardan con Git LFS.
- [Documentación técnica del backend](backend/documentacion/): manual técnico, esquema de base de datos, guía de integración front/API y reporte de pruebas.

## Estructura general

```text
NXBe/
├── overol-front/              # Front Streamlit (consume la API)
├── backend/                   # API Django, docker-compose de la base y documentación técnica
├── Documentos_equipo/         # Documentos de producto, requisitos y diseño
├── Fase 1/                    # Evidencias y entregables de la primera fase
├── Fase 2/                    # Evidencias y entregables de la segunda fase
├── docker-compose.yml         # Proyecto completo en Docker (base + backend + front)
├── docker-compose.override.yml  # Modo desarrollo de Docker (recarga al guardar)
├── DOCKER.md                  # Guía de Docker para quien trabaja el front y el backend
├── HOSTING.md                 # Publicación gratuita (Streamlit Cloud + Render + Supabase)
├── BITACORA_DOCKER_Y_HOSTING.md  # Registro detallado de cómo se hizo Docker y la publicación
├── render.yaml                # Blueprint de Render para el backend
├── .github/workflows/         # Tarea diaria que vence solicitudes en producción
└── README.md                  # Esta guía
```

## Requisitos

- Git y Git LFS (para la presentación y el video de la Fase 2).
- Docker Desktop. En Windows debe estar abierto antes de usar `docker`.
- Solo si trabajas sin Docker: Python 3.14 para el backend (validado con CPython 3.14.8) y Python 3.11 o superior para el front.

## Ejecutar con Docker (recomendado)

Desde la raíz del repositorio:

```powershell
Copy-Item backend\.env.example backend\.env
docker compose up --build
docker compose exec backend python manage.py seed_demo   # usuarios de demostración, una vez
```

| Servicio | URL |
|---|---|
| Front | `http://localhost:8501` |
| API | `http://localhost:8000/api/` |
| Django Admin | `http://localhost:8000/admin/` |

Los cambios de código se ven al guardar, sin reconstruir. La guía completa (cómo trabajar solo el front o solo el backend, comandos frecuentes, modo producción y problemas comunes) está en **[DOCKER.md](DOCKER.md)**.

## Ejecutar sin Docker para el código

Sigue siendo posible trabajar con `venv`, dejando solo la base de datos en Docker:

- Backend: [backend/readme.md](backend/readme.md#puesta-en-marcha-local-sin-docker-para-el-código).
- Front: [overol-front/README.md](overol-front/README.md#cómo-ejecutarlo). Incluye el script `scripts/demo_api.ps1`, que levanta backend y front en Windows.

## Pruebas

| Parte | Con Docker | Sin Docker |
|---|---|---|
| Backend | `docker compose exec backend python manage.py test` | `python manage.py test` desde `backend/` |
| Front | — (no necesita el backend) | `python tests/correr_pruebas.py` desde `overol-front/` |

Las pruebas del backend usan una base de datos temporal y simulan Gemini y Transbank. La última ejecución, dentro de Docker, aprobó las 79 pruebas.

## Funcionalidades y alcance

Implementado: registro y verificación manual de profesionales (cédula), búsqueda y categorización, perfiles, cobertura y disponibilidad, solicitudes de visita, reputación, centro de desarrollo profesional, administración, posventa, reclamos y soporte, recuperación de contraseña por código, el asistente Overil (Gemini) y la suscripción mensual de profesionales con Webpay Plus sandbox.

Fuera del alcance actual:

- Cobros reales y renovación automática de la suscripción.
- Mapas en el front (la búsqueda por radio existe en la API).
- Un programador periódico propio para vencer solicitudes. En producción lo reemplaza la tarea diaria de GitHub Actions (ver [HOSTING.md](HOSTING.md)).
- Endpoints para algunas pantallas de administración, como la moderación de reseñas y la bitácora, que se gestionan desde Django Admin.

## API

La API usa JSON y JWT para las rutas protegidas:

```http
Authorization: Bearer <access_token>
```

Prefijos principales:

| Prefijo | Funcionalidad |
| :--- | :--- |
| `/api/auth/` | Registro, autenticación, perfiles, recuperación de contraseña y verificación |
| `/api/catalog/` | Catálogo de oficios y búsqueda de profesionales |
| `/api/professionals/` | Rutas del profesional autenticado (oficios y disponibilidad) |
| `/api/requests/` | Solicitudes y estados de visitas |
| `/api/ratings/` | Calificaciones y reseñas |
| `/api/claims/` | Reclamos de posventa |
| `/api/tickets/` | Soporte |
| `/api/notifications/` | Notificaciones internas |
| `/api/professional-center/` | Contenido y progreso profesional |
| `/api/assistant/` | Asistente Overil |
| `/api/payments/` | Suscripción y Webpay Plus (sandbox) |

La [guía de integración front/API](backend/documentacion/guia-integracion-frontend-api.md) detalla endpoints, cuerpos de petición, respuestas y permisos.

## Documentación

- [Guía de Docker](DOCKER.md)
- [Publicar gratis (hosting)](HOSTING.md)
- [Bitácora de Docker y publicación (15-11-2026)](BITACORA_DOCKER_Y_HOSTING.md)
- [Backend: puesta en marcha y capacidades](backend/readme.md)
- [Manual técnico integral del backend](backend/documentacion/manual-tecnico-integral-backend.md)
- [Esquema de base de datos](backend/documentacion/esquema-base-datos.md)
- [Guía de integración front/API](backend/documentacion/guia-integracion-frontend-api.md)
- [Reporte de pruebas de la API](backend/documentacion/Postman/reporte_de_pruebas_api_overol.md)
- [Front: ejecución, roles y estructura](overol-front/README.md)
- [Front: despliegue en un servidor](overol-front/DESPLIEGUE.md)

## Seguridad y mantenimiento

No subas `backend/.env` al repositorio. Para configurar otro computador, copia `backend/.env.example` y completa los valores locales.

Tampoco subas archivos subidos por usuarios (`backend/media/`, `backend/private_media/`): pueden contener cédulas y datos personales. Ambas carpetas están en `.gitignore`.

Las credenciales de desarrollo no deben reutilizarse en producción. Antes de desplegar se deben cambiar `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, CORS y las credenciales de la base de datos.

Las solicitudes pendientes con más de 30 días pueden marcarse como vencidas:

```powershell
docker compose exec backend python manage.py expire_visit_requests   # con Docker
python manage.py expire_visit_requests                               # sin Docker, desde backend/
```
