# Guía de integración del frontend con la API de Overol

Esta guía es el contrato práctico para integrar una aplicación frontend con las
rutas HTTP que el backend expone actualmente. Describe autenticación, formatos,
permisos, ejemplos de payloads, respuestas, flujos y errores conocidos. Se
contrasta con las vistas, serializers, modelos y rutas de la implementación;
siempre que cambie el backend, se debe actualizar esta guía junto con sus pruebas.

> **Fuente del contrato:** este documento refleja la implementación existente,
> no una API futura ni una especificación OpenAPI generada. Si una capacidad no
> aparece en las rutas documentadas, no se debe asumir que existe.

## 1. Datos de conexión

| Entorno | Base URL de ejemplo |
|---|---|
| Desarrollo local | `http://127.0.0.1:8000` |
| Despliegue | La URL HTTPS entregada por el equipo de backend |

Todas las rutas REST de este documento comienzan con `/api/`. Ejemplo: la ruta
`POST /auth/token/` se consume como
`POST http://127.0.0.1:8000/api/auth/token/`.

- Usar JSON (`Content-Type: application/json`) en operaciones con cuerpo JSON.
- Las respuestas de fecha/hora se serializan como valores ISO 8601. Las fechas
  de visita usan `YYYY-MM-DD`; las horas usan `HH:MM`; timestamps incluyen zona
  horaria.
- Enviar cantidades CLP sin separador de miles. Los importes de pagos aparecen
  serializados como string decimal, por ejemplo `"10000"`.
- Los parámetros de query se envían en URL-encoding. Los IDs son enteros.
- No llamar APIs de terceros desde el navegador usando secretos. En particular,
  `GEMINI_API_KEY`, secretos Django y credenciales Transbank son exclusivos del
  backend.

## 2. Autenticación y convenciones para el cliente HTTP

### JWT

Para obtener tokens:

```http
POST /api/auth/token/
Content-Type: application/json

{"email":"cliente@example.cl","password":"..."}
```

Respuesta `200`:

```json
{
  "refresh": "<refresh-jwt>",
  "access": "<access-jwt>"
}
```

El access token vence en 15 minutos y el refresh en 7 días. El refresh se rota:
al renovarlo, reemplazar **ambos** tokens por los recibidos.

```http
Authorization: Bearer <access-jwt>
```

Toda operación protegida debe incluir esa cabecera. La falta de token suele
responder `401`; un usuario autenticado sin rol o permiso suele recibir `403`.
No usar `POST /api/auth/login/` para obtener JWT: esa ruta crea una sesión Django
y devuelve `{id,email,role}`; el flujo pensado para frontend/API es `/token/`.
No mezclar autenticación por cookie de sesión y autenticación por bearer en el
mismo cliente sin un diseño explícito de CSRF/sesión.

### Renovar, verificar y revocar

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /api/auth/token/refresh/` | `{"refresh":"<refresh-jwt>"}` | `200` con nuevo `access` y refresh rotado. |
| `POST /api/auth/token/verify/` | `{"token":"<jwt>"}` | `200` si el token es válido; error de autenticación si no. |
| `POST /api/auth/logout/` | `{"refresh":"<refresh-jwt>"}` | `204` sin cuerpo; revoca el refresh. |

Tras `logout`, descartar access y refresh localmente. Un access token ya emitido
no se envía al endpoint de logout y puede seguir siendo válido hasta expirar.
El endpoint de cambio de contraseña tampoco revoca por sí mismo los JWT ya
emitidos; el frontend debe cerrar la sesión local y revocar el refresh conocido
si aún es válido.

Tras tres intentos fallidos de inicio de sesión, la cuenta se bloquea por cinco
minutos. La respuesta es `429` y puede incluir `retry_after` en segundos; el
cliente no debe reintentar antes de ese tiempo.

### Ejemplo JavaScript con `fetch`

```js
const API_BASE_URL = "http://127.0.0.1:8000/api";

async function apiRequest(path, { accessToken, ...options } = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const error = new Error(
      typeof body === "object" ? body.detail || "Error de API" : body
    );
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}
```

No enviar `Content-Type: application/json` al usar `FormData`: el navegador debe
construir el `boundary`. El almacenamiento de JWT debe seguir la política de
seguridad del frontend; preferir cookies `HttpOnly`, `Secure`, `SameSite` si la
arquitectura lo permite. No guardar tokens en logs ni incluirlos en URLs.

### Errores generales

La forma de error depende del endpoint y del tipo de validación. DRF suele
responder JSON, pero no todos los errores comparten un esquema:

```json
{"detail":"No tienes permiso para esta operación."}
```

o errores agrupados por campo:

```json
{"visit_date":["La fecha no puede estar en el pasado."]}
```

El cliente debe tolerar `detail` como texto y objetos/listas de errores de
campo. No asumir que toda respuesta no exitosa contiene `detail`. Códigos más
frecuentes:

| Código | Tratamiento recomendado |
|---|---|
| `400` | Mostrar validación y conservar los valores del formulario. |
| `401` | Intentar una sola renovación si el refresh sigue vigente; si falla, cerrar sesión. |
| `403` | Mostrar falta de permiso/rol; no repetir la petición automáticamente. |
| `404` | El recurso no existe o no es visible para este usuario. |
| `409` | Estado de negocio incompatible (por ejemplo, transición no permitida o pago duplicado); actualizar datos antes de reintentar. |
| `429` | Esperar antes de reintentar; el endpoint puede incluir `Retry-After`. |
| `502` / `503` | Falla temporal de un proveedor externo; ofrecer reintento controlado. |

Para evitar solicitudes duplicadas por doble clic, deshabilitar el botón
correspondiente mientras se procesa una operación de creación/acción/pago.

## 3. Registro, cuenta y perfil

Todas las rutas siguientes usan `/api/auth/`.

### Registrar cliente

`POST /register/` es público. Todos los siguientes campos son parte del contrato:

| Campo | Tipo | Requerido | Notas |
|---|---|---:|---|
| `email` | string | Sí | Correo único; identificador de login. |
| `first_name`, `last_name` | string | Sí | Nombres normalizados por el backend. |
| `rut` | string | Sí | RUT chileno válido; formato normalizado/validado con módulo 11. |
| `password` | string | Sí | Mínimo 8 caracteres y validadores Django. |
| `role` | string | Sí | `CLIENT` o `PROFESSIONAL`; nunca `ADMIN`. |
| `privacy_policy_accepted` | boolean | Sí | Debe ser `true`. |
| `privacy_policy_version` | string | Sí | Máximo 30 caracteres. |
| `username` | string | No | Si falta, se usa el email. |
| `phone`, `address`, `commune` | string | No | Datos de contacto; dirección obligatoria para profesional. |

Ejemplo:

```json
{
  "email":"cliente@example.cl",
  "first_name":"Ana",
  "last_name":"Prueba",
  "rut":"12345678-5",
  "phone":"+56912345678",
  "address":"Av. Ejemplo 123",
  "commune":"Santiago",
  "role":"CLIENT",
  "password":"CambiarClaveSegura123!",
  "privacy_policy_accepted":true,
  "privacy_policy_version":"2026.1"
}
```

Respuesta `201`:

```json
{"id":12,"email":"cliente@example.cl","role":"CLIENT"}
```

Errores comunes: email/RUT duplicado o inválido, contraseña débil, rol no
permitido o falta de aceptación (`400`).

### Registrar profesional

Usar los campos comunes de registro, `role: "PROFESSIONAL"`, `address` y un
objeto `professional_profile`. Actualmente el backend requiere al menos una
comuna y al menos un oficio. Forma aceptada:

```json
{
  "email":"profesional@example.cl",
  "first_name":"Pedro",
  "last_name":"Ejemplo",
  "rut":"12345678-5",
  "address":"Av. Ejemplo 123",
  "commune":"Santiago",
  "role":"PROFESSIONAL",
  "password":"CambiarClaveSegura123!",
  "privacy_policy_accepted":true,
  "privacy_policy_version":"2026.1",
  "professional_profile":{
    "coverage_communes":["Santiago","Ñuñoa"],
    "categories":[
      {"category":1,"years_experience":5,"description":"Instalaciones domiciliarias","specialties":[2]}
    ],
    "specialties":[2],
    "bio":"Experiencia en reparaciones domiciliarias",
    "headline":"Gasfíter residencial",
    "visit_fee":"10000",
    "work_days":["lunes","martes","miércoles","jueves","viernes"],
    "work_start":"09:00",
    "work_end":"18:00",
    "is_available":true
  }
}
```

`categories` acepta una lista de IDs o una lista de objetos; el objeto puede
usar `category` como ID o nombre, `years_experience`, `description` y
`specialties` como IDs. Los campos que el backend conserva en el perfil inicial
son `coverage_communes`, `categories`/`trades`, `specialties`, `visit_fee`,
`bio`, `headline`, `contact_preference`, `certifications`, `work_days`,
`work_start`, `work_end`, `is_available`, `service_latitude` y
`service_longitude`. Oficios/especialidades inexistentes no se crean mediante
esta operación; cargar primero el catálogo y enviar IDs existentes.

La cuenta profesional queda con verificación pendiente y no aparecerá en el
catálogo público hasta que un administrador la apruebe y tenga suscripción
vigente. Después del registro, usar el endpoint de [documentos de verificación](#carga-de-cédula-profesional).

### Consultar y modificar el perfil propio

- `GET /me/` devuelve el perfil autenticado.
- `PATCH /me/` modifica parcialmente los campos editables; admite JSON o
  `multipart/form-data`.

Campos recibidos/devueltos: `id`, `email`, `username`, `first_name`,
`last_name`, `phone`, `rut`, `address`, `commune`, `role`, `profile_photo`,
`bio`, `headline`, `visit_fee`, `contact_preference`, `certifications`,
`professional_profile_id`, `verification_status`, `client_rating_avg`.
Email, username, nombres, RUT y rol son de solo lectura. Los atributos
profesionales son aplicables si el usuario tiene perfil profesional.

Carga de archivo con `FormData`:

```js
const form = new FormData();
form.append("profile_photo", file); // JPG/PNG, hasta 5 MB
form.append("bio", "Gasfíter residencial");
await apiRequest("/auth/me/", {
  method: "PATCH",
  accessToken,
  body: form
});
```

`profile_photo`: JPG/PNG hasta 5 MB. `certifications`: PDF/JPG/PNG hasta 5 MB.
El resto de campos se puede enviar en el mismo `PATCH`. Una imagen de cédula
privada no es un campo editable de este endpoint.

### Carga de documentos de cédula profesional

Los documentos de cédula se cargan por separado del registro y del perfil
público. Las rutas requieren JWT y rol `PROFESSIONAL`.

| Método y ruta | Uso |
|---|---|
| `GET /api/auth/verification/documents/` | Consulta si existe cada lado y el estado de verificación. |
| `POST /api/auth/verification/documents/` | Carga o reemplaza uno o ambos lados con `multipart/form-data`. |

Ejemplo:

```js
const form = new FormData();
form.append("id_card_front", frontFile); // JPEG/JPG o PNG (5 MB) o PDF (10 MB)
if (backFile) form.append("id_card_back", backFile); // opcional en esta petición
const state = await apiRequest("/auth/verification/documents/", {
  method: "POST",
  accessToken,
  body: form
});
```

Los nombres admitidos son `id_card_front` y `id_card_back`; debe incluirse al
menos uno. Se admiten imágenes JPEG/PNG de hasta 5 MB y 25 megapíxeles, o PDF
de hasta 10 MB. Imágenes se validan por formato real, resolución y extensión;
PDF por firma y marca final del archivo. Esta validación no certifica que los
datos del carnet sean legibles o auténticos: la revisión es manual. Enviar el
`FormData` directamente: no establecer manualmente `Content-Type`, para que el
navegador agregue el `boundary`.

Respuesta de `GET` y `POST` (`200`):

```json
{
  "professional_profile_id": 7,
  "verification_status": "PENDING",
  "documents": {
    "front_uploaded": true,
    "back_uploaded": false
  }
}
```

La respuesta no incluye rutas ni URLs de descarga. Al reemplazar cualquier
lado, el perfil vuelve a `PENDING` y debe pasar por una nueva revisión. Un
administrador solo puede aprobar cuando ambos lados estén cargados. Para
revisión, el endpoint administrativo entrega el archivo como descarga privada
(incluidos PDFs). El backend no hace OCR ni extrae datos de la cédula.

### Contraseñas

| Ruta | Cuerpo | Resultado |
|---|---|---|
| `POST /password/change/` (autenticada) | `{"current_password":"...","new_password":"..."}` | `204`; requiere contraseña actual y política Django. El frontend debe cerrar la sesión local, porque el backend invalida la sesión Django, no devuelve tokens nuevos. |
| `POST /password/reset/` (pública) | `{"email":"cliente@example.cl"}` | `202` con mensaje genérico, exista o no el correo. Envía un código al correo registrado. |
| `POST /password/reset/confirm/` (pública) | `{"email":"cliente@example.cl","code":"123456","new_password":"..."}` | `200` al cambiar la contraseña; `400` ante código inválido/vencido/reutilizado o contraseña no permitida. |

El formulario debe solicitar correo, código recibido y nueva contraseña. Enviar
la confirmación:

```js
await apiRequest("/auth/password/reset/confirm/", {
  method: "POST",
  body: JSON.stringify({ email, code, new_password: newPassword })
});
```

El código numérico de seis dígitos se almacena como hash, vence a los 10 minutos,
se invalida después de cinco intentos fallidos y solo puede usarse una vez. Se
permite como máximo un envío por minuto por cuenta; además, el inicio limita a
5 solicitudes por hora y la confirmación a 10 por hora por IP. Las respuestas
no revelan si el correo está registrado. Se aplican los validadores de
contraseña del backend. Al confirmar, se revocan los refresh tokens emitidos
para esa cuenta; los access tokens previos pueden seguir válidos hasta su
expiración (15 minutos como máximo). Manejar `429` sin reintentos automáticos.

En desarrollo el correo puede ir a consola. La respuesta genérica no revela si
el correo existe. En producción, configurar un backend de correo saliente
funcional.

### Mensajes de verificación profesional

| Método y ruta | Contrato |
|---|---|
| `GET /api/auth/verification/messages/` | Solo profesional; devuelve array de `{id,professional,message,admin_response,resolved_at,created_at}`. |
| `POST /api/auth/verification/messages/` | Solo profesional; cuerpo `{"message":"..."}`; respuesta `201` del mensaje creado. |

`professional`, respuesta administrativa y timestamps son de solo lectura.
Usar esta ruta para comunicarse respecto de la verificación; no asumir que
envía imágenes o documentos adjuntos.

## 4. Catálogo y búsqueda pública

Estas rutas no requieren JWT.

| Método y ruta | Query | Resultado |
|---|---|---|
| `GET /api/catalog/categories/` | — | Array `{id,name,keywords,home_zones}`; `home_zones` contiene IDs. |
| `GET /api/catalog/specialties/` | `category_id` opcional | Array `{id,name,category_id}`. |
| `GET /api/catalog/zones/` | — | Array `{id,name}`. |
| `GET /api/catalog/communes/` | — | Array JSON de nombres de comunas con profesionales visibles. |
| `GET /api/catalog/professionals/` | filtros y paginación abajo | Resultados paginados. |
| `GET /api/catalog/professionals/{profile_id}/` | — | Perfil profesional visible más `opinions`. |
| `GET /api/professionals/search/` | mismos filtros | Alias de búsqueda. |

Las categorías oficiales de oficios se cargan en la base de datos mediante
migraciones y se administran desde Django Admin. Consultar este endpoint como
fuente de verdad; no duplicar la lista fija en el frontend.

La búsqueda admite filtros combinables:

| Parámetro | Tipo | Efecto |
|---|---|---|
| `keyword` | string | Busca nombre/apellido, oficio, especialidad y palabras clave. |
| `zone_id` | entero | Filtra por zona del hogar asociada al oficio. |
| `category_id` | entero | Filtra por categoría/oficio activo. |
| `specialty_id` | entero | Filtra por especialidad activa. |
| `commune` | string | Filtra por cobertura de comuna. |
| `latitude`, `longitude`, `radius` | decimal, decimal, entero | Deben enviarse los tres juntos. Coordenadas dentro de latitud `[-90,90]` y longitud `[-180,180]`; radios permitidos `1000`, `5000` o `10000` metros. Requiere PostgreSQL/PostGIS. |
| `page` | entero | Página, desde 1. |
| `page_size` | entero | 20 por defecto, máximo 50. |

Ejemplo:

```http
GET /api/catalog/professionals/?keyword=gasfiter&commune=Santiago&page=1&page_size=20
```

La respuesta paginada DRF tiene esta forma:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 7,
      "name": "Pedro Ejemplo",
      "first_name": "Pedro",
      "last_name": "Ejemplo",
      "specialties": ["Gasfitería domiciliaria"],
      "categories": ["Gasfitería"],
      "visit_fee": "10000",
      "rating_avg": "4.50",
      "verification_status": "APPROVED",
      "trades": [],
      "profile_photo": null,
      "commune": null,
      "bio": "Experiencia residencial",
      "coverage": ["Santiago"],
      "work_days": ["lunes"],
      "work_start": "09:00:00",
      "work_end": "18:00:00",
      "rut": null,
      "address": null
    }
  ]
}
```

El ejemplo ilustra la forma, no datos garantizados. `trades` contiene elementos
con `id`, `category_id`, `category`, `years_experience`, `description` y
`specialties` (`id`, `name`). `profile_photo` puede ser una URL absoluta o
relativa según la configuración de Django. Los campos `commune`, `rut` y
`address` son `null` para el público; no construir UI suponiendo que estos datos
se exponen.

Detalle añade `opinions`: objetos con `quality`, `punctuality`, `treatment`,
`comment`, `created_at`, `author_name`. Solo profesionales con cuenta activa,
verificación aprobada y suscripción vigente aparecen en búsqueda/detalle.

## 5. Funciones del perfil profesional autenticado

Solo rol `PROFESSIONAL`, bajo cualquiera de estos prefijos:

- `/api/professionals/me/...`
- `/api/catalog/professionals/me/...`

Preferir un solo prefijo consistentemente en el frontend. Las operaciones
disponibles:

| Método y ruta | Contrato |
|---|---|
| `GET /api/professionals/me/availability/` | Devuelve `work_days`, `work_start`, `work_end`, `is_available`, `coverage_communes`. |
| `PATCH /api/professionals/me/availability/` | PATCH parcial de los campos anteriores; también acepta `latitude` y `longitude` juntos. |
| `GET /api/professionals/me/trades/` | Array de oficios propios. |
| `POST /api/professionals/me/trades/` | Crea oficio; respuesta `201`. |
| `PATCH /api/professionals/me/trades/{trade_id}/` | Actualiza años, descripción y especialidades. |
| `DELETE /api/professionals/me/trades/{trade_id}/` | Desactiva el oficio; respuesta `204`, no lo borra físicamente. |

Payload de disponibilidad:

```json
{
  "work_days":["lunes","martes","miércoles"],
  "work_start":"09:00",
  "work_end":"18:00",
  "is_available":true,
  "coverage_communes":["Santiago","Ñuñoa"],
  "latitude":-33.4489,
  "longitude":-70.6693
}
```

`work_days` es array de etiquetas de día. La validación de solicitud admite
etiquetas en español/inglés o índices de día, pero se recomienda usar nombres en
español. Coordenadas deben enviarse juntas. La vista comprueba que sean
numéricas y estén en rango; errores de validación se devuelven como `400`.

Crear oficio:

```json
{
  "category_id": 1,
  "years_experience": 5,
  "description": "Reparaciones e instalaciones",
  "specialties": [2, 3]
}
```

Respuesta incluye `id`, `category_id`, `years_experience`, `description`,
`certification`, `certification_verified`, `is_active`. `specialties` se acepta
en escritura y es lista de IDs. Las especialidades deben pertenecer a la
categoría seleccionada para ser asociadas. Un profesional no puede crear una
segunda relación para la misma categoría.

## 6. Solicitudes de visita

Se requiere JWT. `GET /api/requests/` lista solo las solicitudes del usuario:
para cliente, las creadas; para profesional, las recibidas. La respuesta es un
array JSON (este ListAPIView no configura paginación). `POST /api/requests/`
solo está permitido a clientes.

### Crear solicitud

```http
POST /api/requests/
Authorization: Bearer <access>
Content-Type: application/json
```

```json
{
  "professional": 7,
  "specialty": 2,
  "problem_description": "El calefont no enciende y no hay agua caliente.",
  "tentative_schedule": "Sábado por la mañana",
  "visit_date": "2026-11-21",
  "visit_time": "10:00 - 12:00",
  "commune": "Santiago",
  "home_zone": 3,
  "visit_address": "Av. Ejemplo 123"
}
```

Requeridos efectivos: `professional`, `specialty`, `problem_description`,
`visit_date`, `visit_time`, `visit_address`. `commune` y `home_zone` son
opcionales en serializer/modelo; si se envía comuna y el profesional configuró
cobertura, debe estar dentro de ella. `tentative_schedule` es opcional.

Reglas que el formulario debe anticipar:

- El profesional debe estar aprobado, suscrito, disponible y ofrecer la
  especialidad indicada.
- La fecha no puede estar en el pasado y debe coincidir con `work_days`.
- El profesional debe tener `work_start`/`work_end` configurados.
- `visit_time` debe ser `HH:MM` o un intervalo `HH:MM - HH:MM` dentro del
  horario de atención y con fin posterior al inicio.
- No se permite más de una solicitud `PENDING` del mismo cliente al mismo
  profesional.

Respuesta `201` es el objeto solicitud. Campos principales:

`id`, `client`, `client_name`, `professional`, `professional_name`, `specialty`,
`specialty_name`, `category_name`, `problem_description`, `tentative_schedule`,
`visit_date`, `visit_time`, `commune`, `home_zone`, `visit_address`, `status`,
`rejection_reason`, `cancelled_by`, `cancel_reason`, `client_confirmed_at`,
`professional_confirmed_at`, `completed_at`, `expires_at`, `phone`, `address`,
`contact_commune`, `created_at`.

`client`, estado, datos de rechazo/cancelación y timestamps de ciclo son de solo
lectura. Contacto `phone`, `address`, `contact_commune` viene como `null` hasta
que la solicitud esté aceptada/finalizada/completada; los datos visibles
pertenecen a la contraparte.

### Acciones sobre solicitud

Todas son `POST /api/requests/{id}/{action}/`, devuelven el objeto actualizado,
excepto que ocurra error:

| Acción | Quién | Cuerpo | Reglas |
|---|---|---|---|
| `accept` | Profesional dueño | `{}` | Solo `PENDING`; pasa a `ACCEPTED`. |
| `reject` | Profesional dueño | `{"reason":"No tengo disponibilidad"}` | Motivo requerido, máximo 500; solo `PENDING`. |
| `cancel` | Cliente dueño | `{"reason":"Cambio de planes"}` (opcional) | Solo `PENDING` o `ACCEPTED`; reason máximo 500 al guardar. |
| `cancel_professional` | Profesional dueño | `{"reason":"..."}` | Solo `ACCEPTED`; motivo de 1 a 500 caracteres. |
| `finish` | Profesional dueño | `{}` | Solo `ACCEPTED`; marca que profesional terminó. |
| `confirm` | Cliente dueño | `{}` | Solo `ACCEPTED` o `PROFESSIONAL_FINISHED`; junto a confirmación del profesional completa la solicitud. |

Estados: `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED`, `EXPIRED`,
`PROFESSIONAL_FINISHED`, `COMPLETED`, `FORCED_CLOSED`. No codificar el flujo
como un orden de pantalla rígido: cliente y profesional pueden confirmar el
término en distinto orden. Acción inválida generalmente devuelve `409`; rol o
propiedad incorrectos, `403`/`404`.

## 7. Calificaciones, reclamos, soporte, notificaciones y contenidos

Todas las rutas de esta sección requieren JWT. Las listas devuelven arrays JSON
sin paginación configurada.

### Calificaciones

`POST /api/ratings/` crea una calificación:

```json
{"visit":42,"quality":5,"punctuality":4,"treatment":5,"comment":"Buen servicio"}
```

`quality`, `punctuality` y `treatment`: enteros de 1 a 5; `comment` opcional.
Solo las partes de una visita `COMPLETED`, dentro de 30 días de su cierre, y
una calificación por autor/visita. `target` se determina automáticamente como
la contraparte. Respuesta `201`: `{id,visit,quality,punctuality,treatment,comment,created_at}`.

### Reclamos posventa

| Método/ruta | Uso |
|---|---|
| `GET /api/claims/` | Admin ve todos; cliente/profesional ve los reclamos de sus solicitudes. |
| `POST /api/claims/` | Cliente de una visita completada crea reclamo. |
| `POST /api/claims/{id}/respond/` | Profesional dueño responde reclamo abierto. |
| `POST /api/claims/{id}/escalate/` | Una de las partes escala el reclamo. |
| `POST /api/claims/{id}/resolve/` | Admin resuelve. |

Crear:

```json
{"visit":42,"description":"El problema persiste después de la reparación."}
```

Acciones usan cuerpo `{"response":"..."}` para `respond` y
`{"resolution":"..."}` para `resolve`; `escalate` no requiere campos. Respuesta:
`{id,visit,description,professional_response,admin_resolution,status,created_at,resolved_at}`.
Estados: `OPEN`, `PROFESSIONAL_RESPONDED`, `ESCALATED`, `RESOLVED`. Solo se
permite un reclamo por visita completada.

### Tickets de soporte

- `GET /api/tickets/`: admin ve todos; usuario ve los propios. Filtro opcional
  `?status=OPEN`, `IN_REVIEW` o `RESOLVED`.
- `POST /api/tickets/`:

```json
{"visit":42,"subject":"Consulta sobre solicitud","description":"Necesito ayuda con la coordinación."}
```

`visit` y `subject` son requeridos por el serializer; `subject` máximo 160,
`description` máximo 500. La visita debe pertenecer al usuario (cliente o
profesional). Respuesta contiene `id`, `visit`, `subject`, `description`,
`response`, `status`, `created_at`, `updated_at`.
- `POST /api/tickets/{id}/resolve/`: solo admin, cuerpo
  `{"response":"..."}` requerido; devuelve ticket actualizado.

### Notificaciones

- `GET /api/notifications/`: array propio con `id`, `title`, `message`,
  `related_visit`, `is_read`, `created_at`.
- `POST /api/notifications/{id}/read/`: marca como leída; respuesta del objeto.
  Acceder a notificación ajena da `404`.

### Centro profesional

- `GET /api/professional-center/content/`: solo profesional; array con `id`,
  `title`, `description`, `module`, `url`, `is_external`, `order`. Módulos:
  `TAX`, `SAFETY`, `MANAGEMENT`. Los videos, canales y lista de reproducción
  de seguridad iniciales se cargan desde migraciones y se administran desde
  Django Admin. Abrir los enlaces externos de YouTube; el backend no aloja el
  contenido multimedia.
- `POST /api/professional-center/progress/`: solo profesional:
  `{"content":12}`. `content` es ID del contenido. Respuesta `201` con
  `{id,content,completed_at}`. No se puede duplicar progreso del mismo
  contenido.

## 8. Overil

`POST /api/assistant/chat/`, JWT requerido:

```json
{"message":"La llave del lavaplatos gotea, ¿qué especialista necesito?"}
```

`message` requerido, entre 1 y 1500 caracteres. Respuesta normal o rechazo:

```json
{"reply":"..."}
```

No hay endpoint para recuperar historial; el backend no almacena mensajes.
Límite DRF: 5 solicitudes por hora por usuario; además, 10 respuestas Gemini
por usuario/día y 50 globales/día. Los rechazos fuera de tema o de seguridad no
usan cuota diaria de Gemini, pero sí pasan por el throttle horario.

- `429`: throttle o cuota excedida. Mostrar mensaje y no reintentar en bucle.
- `503`: clave/proveedor Gemini no disponible.
- Los límites de respuesta son del servidor (300 tokens); no hay configuración
  de tokens desde frontend.

## 9. Pagos Webpay Plus (sandbox)

El pago siempre se inicia en backend. El frontend no determina importe, no
confirma autorización y no debe reutilizar un token de Webpay.

### Suscripción profesional

- `GET /api/payments/professional-subscription/` (profesional autenticado):

```json
{
  "professional_profile_id":7,
  "status":"ACTIVE",
  "amount":"10000",
  "plan":{
    "code":"professional-monthly",
    "name":"Suscripción profesional mensual",
    "duration_months":1
  },
  "expires_at":"2026-12-13T23:59:59-03:00",
  "latest_payment":{
    "id":31,"visit_id":null,"professional_profile_id":7,
    "amount":"10000","buy_order":"ov-...","status":"AUTHORIZED",
    "created_at":"...","updated_at":"..."
  }
}
```

Estados de suscripción: `INACTIVE`, `ACTIVE`, `EXPIRED`. `latest_payment` puede
ser `null`.
`amount` y `plan` describen el plan actualmente activo en la base de datos; el
importe no es una constante del frontend.

- `POST /api/payments/professional-subscription/transbank/` con `{}` inicia
  un pago del plan activo; solo profesionales. El cliente no envía monto ni
  duración. Respuesta `201`:

```json
{
  "id":31,
  "visit_id":null,
  "professional_profile_id":7,
  "amount":"10000",
  "buy_order":"ov-...",
  "status":"PENDING",
  "created_at":"...",
  "updated_at":"...",
  "url":"https://webpay3gint.transbank.cl/...",
  "token":"<token-webpay>",
  "environment":"sandbox"
}
```

El plan inicial es `professional-monthly`, por $10.000 CLP y un mes. Un
administrador puede cambiar monto/duración desde Django Admin; no existe un
endpoint API para modificarlo. Los datos del plan y su duración se copian a la
transacción al iniciarla, así los pagos pendientes conservan sus condiciones.
Si no hay plan activo, la creación responde `409 Conflict` y la consulta de
estado `503 Service Unavailable`.
Las especialidades existentes no cambian con esta operación; se deben consultar
desde `GET /api/catalog/specialties/` y no asumir que cada nueva categoría ya
tiene especialidades asociadas.

Navegación a Webpay: crear un formulario HTML y enviarlo por **POST** con
`token_ws` al valor `url` recibido. No navegar con GET ni agregar el token a una
URL. Ejemplo:

```js
function submitToWebpay(url, token) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = url;
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "token_ws";
  input.value = token;
  form.append(input);
  document.body.append(form);
  form.submit();
}
```

Transbank vuelve al callback configurado en backend. El backend confirma el
resultado y redirige al `PAYMENT_RESULT_URL` configurado para la aplicación con
query params:

```text
?status=authorized&professional_profile_id=7
```

o `status=rejected`, `status=cancelled` o `status=error`. La UI **no debe
considerar la query string prueba definitiva del pago**. Al volver, consultar
`GET /api/payments/professional-subscription/` con JWT para mostrar vigencia
persistida. La suscripción se renueva manualmente por un mes tras confirmación
exitosa; no hay cobro recurrente.

El callback público que recibe Transbank es
`GET` o `POST /api/payments/transbank/return/`; no debe invocarlo el frontend.
El backend lee los campos `token_ws`, `TBK_TOKEN` y `TBK_ORDEN_COMPRA` desde la
query string o el body, procesa la confirmación o cancelación y redirige al
`PAYMENT_RESULT_URL`.

### Pago de visita

- `POST /api/payments/visits/{visit_id}/transbank/` (cliente dueño, visita
  `ACCEPTED`): cuerpo vacío `{}`; el backend toma la tarifa del profesional.
  Respuesta `201` usa la misma forma de inicio, con `visit_id` y
  `professional_profile_id: null`.
- `GET /api/payments/visits/{visit_id}/` devuelve la transacción más reciente
  del usuario pagador, con `id`, `visit_id`, `professional_profile_id`,
  `amount`, `buy_order`, `status`, `created_at`, `updated_at`.

Estados de transacción: `PENDING`, `AUTHORIZED`, `REJECTED`, `FAILED`. Un pago
pendiente dura hasta 30 minutos; no se inicia otro para el mismo objetivo
mientras siga pendiente. La API puede responder `404` si la solicitud/pago no
existe, `409` si el estado no permite pago, `403` si el rol no corresponde o
`502` cuando Transbank falla al iniciar.

La URL de retorno debe ser accesible desde Transbank para completar la prueba.
`localhost`/`127.0.0.1` no reciben callbacks externos. Este backend está fijado
a sandbox; la suite automatizada simula el SDK y no sustituye una prueba
integrada con Transbank.

## 10. Operaciones administrativas disponibles por API

Son funciones de backoffice; exigen JWT y rol `ADMIN`. El endpoint de descarga
privada también requiere que la cuenta tenga `is_staff=true` (permiso Django
`IsAdminUser`). El frontend de administración debe ocultar estas acciones a
otros roles, pero el backend también valida permiso.

| Método/ruta | Cuerpo / respuesta |
|---|---|
| `POST /api/auth/verification/{profile_id}/approve/` | Cuerpo opcional `{"reason":"..."}`; respuesta `{"status":"APPROVED"}`. |
| `POST /api/auth/verification/{profile_id}/reject/` | `{"reason":"Motivo obligatorio"}`; respuesta `{"status":"REJECTED"}`. |
| `POST /api/auth/admin/accounts/{user_id}/status/` | `{"status":"ACTIVE|SUSPENDED|BLOCKED|DEACTIVATED","reason":"..."}`; devuelve `id` y `account_status`. |
| `GET /api/admin/verifications/{profile_id}/document/?side=front` | Descarga privada como adjunto; `side=front` por defecto o `back`. Requiere admin y `is_staff`. |

El backend también contiene operaciones de resolución de reclamos/tickets
descritas arriba. Los endpoints administrativos de Django Admin son páginas
HTML y no parte del contrato REST.

## 11. Flujos recomendados del frontend

### Cliente: encontrar profesional y pedir visita

1. Cargar categorías, especialidades y zonas desde endpoints públicos.
2. Buscar profesionales con filtros; conservar el `id` del perfil, no el id de
   usuario.
3. Consultar detalle y mostrar tarifa, horarios y cobertura antes de continuar.
4. Autenticar o registrar cliente.
5. Crear la solicitud con IDs de profesional/especialidad y fecha/hora
   compatibles con horario/cobertura.
6. Consultar `GET /api/requests/` para refrescar estado. Esperar aceptación para
   mostrar pago y datos de contacto.
7. El cliente puede iniciar pago, calificar tras `COMPLETED`, abrir reclamo o
   ticket según corresponda.

### Profesional: habilitar perfil

1. Registrar rol profesional con cobertura y oficio.
2. Autenticar; obtener `professional_profile_id` y estado de verificación desde
   `GET /api/auth/me/`.
3. Consultar `GET /api/auth/verification/documents/` y subir ambos lados de la
   cédula con `POST /api/auth/verification/documents/`.
4. Configurar disponibilidad, horario y cobertura.
5. Seguir verificación con `GET /api/auth/verification/messages/` y, si
   corresponde, enviar un mensaje.
6. Iniciar y completar suscripción sandbox.
7. Refrescar estado de suscripción y perfil. Solo con verificación aprobada y
   suscripción vigente queda visible en el catálogo.
8. Consultar solicitudes recibidas, actuar sobre ellas y luego marcar
   finalización; el cliente debe confirmar para alcanzar `COMPLETED`.

### Respuesta visual para errores

- Mantener mensajes de validación junto al campo cuando el error corresponde a
  un campo; para errores globales mostrar `detail` o un mensaje genérico.
- En `401`, no descartar el formulario. Renovar una vez y repetir una sola vez
  solo si el endpoint es seguro/idempotente; para un POST de pago/creación no
  repetir sin verificar el estado.
- En callback de pagos, consultar estado real desde la API antes de desbloquear
  beneficios.
- `GET /api/requests/` puede expirar solicitudes pendientes de más de 30 días;
  el listado puede reflejar un estado cambiado por esa operación.

## 12. Límites de la API que el frontend debe conocer

Estos límites son importantes para no implementar integraciones contra
funciones inexistentes:

1. Los documentos de cédula se cargan y su estado se consulta mediante
   `/api/auth/verification/documents/`. No existe una ruta de descarga para el
   profesional; solo el backoffice puede leer los archivos privados.
2. No hay endpoint para obtener historial de conversación Overil.
3. No hay API de renovación automática, cancelación de suscripción recurrente,
   reembolso o listado general de pagos. La renovación es manual.
4. Los pagos son sandbox y el backend no confirma pagos a partir de datos
   enviados por el cliente.
5. La mayoría de listas no tienen paginación. La búsqueda de profesionales es
   la excepción y usa `count`, `next`, `previous`, `results`.
6. No existe contrato documentado de OpenAPI/Swagger en la configuración
   actual; esta guía es manual y debe revisarse contra código al cambiar rutas o
   serializers.
7. Los endpoints de API permiten CORS global en la configuración actual de
   desarrollo. Antes de despliegue, backend debe limitar CORS a los orígenes
   reales del frontend y servir HTTPS.
8. La carga de fotos de perfil/certificaciones existe vía `PATCH /auth/me/`;
   no usarla como reemplazo para la carga de cédula privada.

## 13. Checklist de integración y pruebas manuales

- [ ] Configurar base URL por entorno; no incluir claves privadas del backend en
  el bundle del frontend.
- [ ] Registrar cliente, iniciar JWT, consultar `/auth/me/`, renovar y cerrar
  sesión.
- [ ] Verificar expiración/error `401`, rol incorrecto `403` y formulario con
  errores `400`.
- [ ] Probar búsqueda sin resultados, paginación, filtros, perfil y respuesta
  cuando no hay coordenadas/PostGIS.
- [ ] Probar solicitud válida y cada transición con los roles correctos e
  incorrectos.
- [ ] Probar carga de foto/certificación y ambos lados de cédula con
  `FormData`, imágenes inválidas/mayores de 5 MB, PDFs inválidos/mayores de
  10 MB y descarga administrativa privada.
- [ ] Probar inicio de recuperación con correo existente e inexistente y
  confirmar contraseña con código válido, incorrecto, vencido, bloqueado tras
  cinco intentos y ya utilizado.
- [ ] Probar calificación, reclamo, ticket, lectura de notificación y progreso.
- [ ] Probar cuotas de Overil y manejar `429`/`503` sin reintentos agresivos.
- [ ] Completar un flujo Webpay sandbox y validar el resultado consultando la
  API, no confiando solo en el redirect.
- [ ] Verificar UI con perfil no verificado, suscripción inactiva/vencida,
  solicitud expirada y pago pendiente.

Para detalles de arquitectura, modelos, seguridad, instalación y pruebas
automatizadas, ver el [manual técnico integral](manual-tecnico-integral-backend.md).
