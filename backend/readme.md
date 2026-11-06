# Backend de Overol

API REST desarrollada con Django y Django REST Framework para conectar clientes
con profesionales de oficios del hogar. Usa PostgreSQL/PostGIS y Redis mediante
Docker, y JWT para las rutas protegidas.

## Estructura

```text
backend/
├── apps/
│   ├── authentication/      # Usuarios, roles y verificación profesional
│   ├── catalog/             # Oficios, especialidades y búsqueda
│   ├── visits/              # Visitas, reseñas, posventa y soporte
│   └── assistant/           # Reservado para diagnóstico con IA
├── core/                    # Configuración global y URLs
├── documentacion/           # Instalación, API, arquitectura y pruebas
├── docker-compose.yml       # PostgreSQL/PostGIS y Redis
└── manage.py
```

## Puesta en marcha

Ejecutar desde `backend/`:

```powershell
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

URLs:

- API: `http://127.0.0.1:8000/api/`
- Administración: `http://127.0.0.1:8000/admin/`

## Pruebas

```powershell
python manage.py test
```

Las pruebas utilizan una base de datos temporal.

## Alcance

El backend implementa autenticación, verificación profesional, catálogo,
solicitudes de visita, reputación, posventa, soporte, notificaciones,
contenidos profesionales y administración.

Las suscripciones, pagos, chatbot con IA y geolocalización real están fuera del
alcance actual.

## Documentación

- [Índice de documentación](documentacion/README.md)
- [Instalación](documentacion/instalacion.md)
- [Arquitectura](documentacion/arquitectura.md)
- [Contrato de API](documentacion/api.md)
- [Base de datos](documentacion/base-de-datos.md)
- [Docker](documentacion/docker.md)
- [Pruebas](documentacion/reporte-pruebas-backend-overol.md)
- [Estado de la Definition of Done](documentacion/estado-dod.md)

Las solicitudes pendientes con más de 30 días pueden marcarse como vencidas:

```powershell
python manage.py expire_visit_requests
```
