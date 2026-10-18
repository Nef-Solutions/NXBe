# Arquitectura del backend Overol

## Resumen

Overol utiliza un **monolito modular**: el backend se ejecuta como una aplicación Django y organiza cada dominio dentro de `apps/`. Esto permite mantener un despliegue sencillo y compartir la misma base de datos sin separar todavía el sistema en microservicios.

## Estructura principal

```text
overol-backend/
├── core/                         # Configuración global y URLs principales
├── apps/
│   ├── authentication/           # Usuarios, roles y verificación profesional
│   ├── catalog/                  # Oficios, especialidades y búsqueda
│   ├── visits/                   # Solicitudes, servicios, reseñas y posventa
│   └── assistant/                # Reservado para diagnóstico con IA
├── documentacion/                # Guías, API, pruebas y diagramas
├── media/                        # Archivos subidos en desarrollo
├── docker-compose.yml            # PostgreSQL/PostGIS y Redis
└── manage.py                     # Comandos administrativos de Django
```

## Módulos implementados

### `authentication`

Gestiona:

- Registro de clientes y profesionales.
- Inicio de sesión mediante JWT y compatibilidad con sesión Django.
- Cambio y recuperación de contraseña.
- Roles `CLIENT`, `PROFESSIONAL` y `ADMIN`.
- Validación de RUT y sanitización de nombres.
- Estados de cuenta y bloqueo temporal por intentos fallidos.
- Verificación profesional y mensajes al administrador.

### `catalog`

Gestiona:

- Zonas del hogar.
- Categorías de oficios.
- Especialidades.
- Oficios declarados por profesionales.
- Búsqueda pública de profesionales verificados.
- Experiencia y certificaciones declaradas.

### `visits`

Gestiona:

- Solicitudes de visita.
- Aceptación, rechazo y cancelación.
- Finalización y confirmación del servicio.
- Calificaciones de cliente y profesional.
- Reclamos de posventa.
- Tickets de soporte.
- Notificaciones internas.
- Contenido y progreso del Centro de Desarrollo Profesional.
- Bitácora de acciones administrativas.

## Enrutamiento de la API

El enrutamiento comienza en `core/urls.py` y se divide por módulo:

| Prefijo | Módulo |
| :--- | :--- |
| `/api/auth/` | Usuarios, sesiones y verificación. |
| `/api/catalog/` | Búsqueda y perfiles públicos. |
| `/api/requests/` | Solicitudes y estados de visitas. |
| `/api/ratings/` | Calificaciones. |
| `/api/claims/` | Posventa. |
| `/api/tickets/` | Soporte. |
| `/api/notifications/` | Notificaciones internas. |
| `/api/professional-center/` | Contenido y progreso profesional. |

## Persistencia

- PostgreSQL 16 con PostGIS se ejecuta mediante Docker.
- Redis 7 está preparado para caché y futuras tareas asíncronas.
- Las migraciones de Django describen la estructura de la base de datos.
- El diagrama de relaciones está en [base-de-datos.md](base-de-datos.md).

## Áreas reservadas o excluidas

Estas áreas no se consideran implementadas en la etapa actual:

- La aplicación `assistant` queda reservada para el chatbot, que está fuera de alcance.
- No existe una aplicación `locations`; la geolocalización y cobertura real fueron excluidas.
- JWT es el mecanismo recomendado para consumir la API; la sesión Django se conserva como compatibilidad.
- No existen suscripciones ni pasarela de pago.

## Decisiones de diseño

- La lógica de negocio de estados vive en los modelos y servicios del dominio.
- Los serializers validan los datos que llegan desde la API.
- Las vistas aplican autenticación y permisos básicos.
- Las acciones administrativas generan bitácora cuando corresponde.
- El código mantiene los límites de cada módulo para reducir dependencias cruzadas.
