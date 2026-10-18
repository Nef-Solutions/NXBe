# API de Overol

## Datos generales

- Base URL local: `http://127.0.0.1:8000/api/`
- Formato principal: `application/json`
- Codificación: UTF-8.
- Las rutas protegidas aceptan JWT mediante el encabezado `Authorization: Bearer <access_token>`.
- Las sesiones Django se mantienen como compatibilidad para el panel y clientes existentes.
- Las peticiones con JWT no necesitan conservar cookies ni enviar CSRF.
- Los identificadores son enteros.
- Las fechas se entregan en formato ISO 8601.

## Convenciones de error

Los errores de validación usan HTTP `400` y un objeto cuyos campos contienen el problema:

```json
{
  "rut": ["El RUT no puede estar vacío."]
}
```

Respuestas frecuentes:

| Código | Significado |
| :--- | :--- |
| `201` | Recurso creado. |
| `202` | Solicitud aceptada para procesarse. |
| `204` | Operación exitosa sin contenido. |
| `400` | Datos faltantes o inválidos. |
| `401` | Falta iniciar sesión. |
| `403` | El usuario no tiene el rol o permiso requerido. |
| `404` | Recurso inexistente o no visible para el usuario. |
| `409` | La transición de estado no es válida. |

## Autenticación

### `POST /api/auth/register/`

No requiere sesión.

Campos JSON:

| Campo | Tipo | Obligatorio | Valores o regla |
| :--- | :--- | :---: | :--- |
| `email` | string | Sí | Correo válido y único. |
| `username` | string | No | Si falta, se usa el correo. |
| `first_name` | string | Sí | Nombre válido, sin secuencias SQL peligrosas. |
| `last_name` | string | Sí | Apellido válido. |
| `phone` | string | No | Teléfono. |
| `rut` | string | Sí | RUT chileno válido, por ejemplo `11.111.111-1`. |
| `address` | string | Sí para cliente | Dirección declarada. |
| `commune` | string | Sí para cliente | Comuna declarada. |
| `role` | string | Sí | `CLIENT` o `PROFESSIONAL`. No se permite registrar `ADMIN`. |
| `password` | string | Sí | Mínimo 8 caracteres y validaciones Django. |
| `privacy_policy_accepted` | boolean | Sí | Debe ser `true`. |
| `privacy_policy_version` | string | Sí | Versión de los términos aceptados. |
| `professional_profile` | object | Sí para profesional | Puede incluir `id_card_front`, `id_card_back` y `visit_fee`. |

Ejemplo de cliente:

```json
{
  "email": "cliente@ejemplo.cl",
  "first_name": "Ana",
  "last_name": "Pérez",
  "phone": "+56912345678",
  "rut": "11.111.111-1",
  "address": "Av. Principal 123",
  "commune": "Santiago",
  "role": "CLIENT",
  "password": "ClaveSegura123!",
  "privacy_policy_accepted": true,
  "privacy_policy_version": "2026-10"
}
```

### `POST /api/auth/login/`

```json
{
  "email": "cliente@ejemplo.cl",
  "password": "ClaveSegura123!"
}
```

Las credenciales incorrectas no indican qué dato falló. Después de tres intentos fallidos consecutivos se bloquea el acceso durante seis horas.

### `POST /api/auth/token/`

Es el endpoint recomendado para el frontend. No requiere sesión y devuelve un token de acceso y uno de renovación:

```json
{
  "email": "cliente@ejemplo.cl",
  "password": "ClaveSegura123!"
}
```

Respuesta:

```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

El `access` dura 15 minutos. El `refresh` dura 7 días.

### `POST /api/auth/token/refresh/`

Solicita un nuevo token de acceso sin pedir nuevamente la contraseña:

```json
{
  "refresh": "eyJ..."
}
```

### `POST /api/auth/token/verify/`

Comprueba que un token sea válido:

```json
{
  "token": "eyJ..."
}
```

### Cómo consumir rutas protegidas

El frontend debe enviar el token de acceso en cada petición protegida:

```http
Authorization: Bearer eyJ...
Content-Type: application/json
```

Cuando el access token expire, debe llamar a `/api/auth/token/refresh/`. Si el refresh token también expira, el usuario debe iniciar sesión nuevamente.

El endpoint `/api/auth/login/` basado en sesión se conserva para compatibilidad, pero el frontend nuevo debe preferir `/api/auth/token/`.

### `POST /api/auth/logout/`

Requiere sesión. No recibe cuerpo.

### `GET /api/auth/me/`

Requiere sesión. Devuelve el perfil propio.

### `PATCH /api/auth/me/`

Requiere sesión. Solo acepta actualmente `phone`, `address` y `commune`. No enviar `email`, `username`, `first_name`, `last_name`, `rut` ni `role` esperando modificarlos.

### `POST /api/auth/password/change/`

```json
{
  "current_password": "ClaveAnterior123!",
  "new_password": "ClaveNueva456!"
}
```

### `POST /api/auth/password/reset/`

```json
{
  "email": "cliente@ejemplo.cl"
}
```

Siempre devuelve el mismo mensaje para no revelar si el correo existe.

## Verificación y administración

### `GET|POST /api/auth/verification/messages/`

Solo profesionales autenticados.

Para `POST`:

```json
{
  "message": "Adjunto nuevamente la documentación solicitada."
}
```

### `POST /api/auth/verification/{professional_id}/{decision}/`

Solo administradores. `decision` debe ser `approve` o `reject`. Para rechazar, `reason` es obligatorio:

```json
{
  "reason": "La fotografía de la cédula no es legible."
}
```

### `POST /api/auth/admin/accounts/{user_id}/status/`

Solo administradores. `status` debe ser `ACTIVE`, `SUSPENDED`, `BLOCKED` o `DEACTIVATED`; `reason` siempre es obligatorio.

## Catálogo

### `GET /api/catalog/professionals/`

No requiere sesión. Parámetros opcionales:

| Parámetro | Tipo | Regla |
| :--- | :--- | :--- |
| `keyword` | string | Busca en nombre, especialidad, oficio y keywords. |
| `zone_id` | integer | ID existente de `HomeZone`. |
| `category_id` | integer | ID existente de `TradeCategory`. |
| `page` | integer | Página, inicia en `1`. |
| `page_size` | integer | Entre `1` y `50`; por defecto `20`. |

Solo devuelve profesionales verificados. No expone RUT, correo, teléfono ni dirección exacta.

### `GET /api/catalog/professionals/{id}/`

Devuelve el detalle público de un profesional verificado y activo, incluyendo especialidades, oficios, experiencia, tarifa, promedio y opiniones.

## Visitas y servicios

Todas las rutas siguientes requieren sesión.

### `GET|POST /api/requests/`

`GET` devuelve las solicitudes del usuario actual.

`POST` solo lo puede realizar un cliente:

```json
{
  "professional": 12,
  "specialty": 4,
  "problem_description": "El enchufe de la cocina no funciona.",
  "tentative_schedule": "Sábado por la mañana",
  "visit_address": "Calle Ejemplo 123"
}
```

El profesional debe estar aprobado y la especialidad debe pertenecerle.

### `POST /api/requests/{id}/{action}/`

Acciones válidas:

| Acción | Usuario | Cuerpo |
| :--- | :--- | :--- |
| `accept` | Profesional de la solicitud | `{}` |
| `reject` | Profesional de la solicitud | `{ "reason": "No tengo disponibilidad." }` |
| `cancel` | Cliente de la solicitud | `{}` |
| `finish` | Profesional de la solicitud | `{}` |
| `confirm` | Cliente de la solicitud | `{}` |

Estados principales: `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED`, `EXPIRED`, `PROFESSIONAL_FINISHED` y `COMPLETED`.

## Calificaciones y posventa

### `POST /api/ratings/`

Solo después de completar la visita:

```json
{
  "visit": 10,
  "quality": 5,
  "punctuality": 4,
  "treatment": 5,
  "comment": "Trabajo claro y ordenado."
}
```

Los valores de las tres puntuaciones deben estar entre `1` y `5`. Cada usuario solo puede calificar una vez la misma visita.

### `GET|POST /api/claims/`

Un cliente puede crear un reclamo sobre una visita completada:

```json
{
  "visit": 10,
  "description": "El problema reapareció después del servicio."
}
```

### `POST /api/claims/{id}/respond/`

Solo el profesional de la visita:

```json
{
  "response": "Coordinaré una nueva revisión."
}
```

### `POST /api/claims/{id}/escalate/`

Cliente o profesional. No recibe cuerpo.

### `POST /api/claims/{id}/resolve/`

Solo administradores:

```json
{
  "resolution": "Se acuerda una visita de corrección."
}
```

### `GET|POST /api/tickets/`

Crear ticket:

```json
{
  "subject": "No puedo cancelar una solicitud",
  "description": "La solicitud aparece como pendiente.",
  "visit": 10
}
```

`visit` es opcional.

### `POST /api/tickets/{id}/resolve/`

Solo administradores:

```json
{
  "response": "La solicitud fue cancelada correctamente."
}
```

## Notificaciones

### `GET /api/notifications/`

Devuelve solo las notificaciones del usuario autenticado.

### `POST /api/notifications/{id}/read/`

Marca como leída una notificación propia. No recibe cuerpo.

## Centro de Desarrollo Profesional

### `GET /api/professional-center/content/`

Solo profesionales autenticados. Devuelve contenido visible de los módulos `TAX`, `SAFETY` y `MANAGEMENT`.

### `POST /api/professional-center/progress/`

Solo profesionales:

```json
{
  "content": 3
}
```

No se debe registrar dos veces el mismo contenido para el mismo profesional.

## Vencimiento de solicitudes

El backend incluye un comando administrativo, no un endpoint HTTP:

```powershell
python manage.py expire_visit_requests
```

Marca como `EXPIRED` las solicitudes `PENDING` con más de 30 días y crea una notificación para el cliente.