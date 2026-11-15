# Manual técnico integral del backend de Overol

Este manual describe el backend que existe en el repositorio: arquitectura,
configuración, reglas, modelos, rutas HTTP, flujos, pruebas y límites conocidos.
Está dirigido a desarrollo, QA y operación local. Cuando una capacidad depende
de un servicio externo o no está implementada, se indica explícitamente.

> Para implementar el cliente web sin inferir contratos, consultar también la
> [guía de integración frontend/API](guia-integracion-frontend-api.md), que reúne
> payloads, respuestas, permisos, flujos de usuario y límites por endpoint.
> El [esquema de base de datos](esquema-base-datos.md) muestra las entidades y
> relaciones actuales en Mermaid.

> **Alcance de pagos:** Webpay Plus está configurado exclusivamente para
> integración/sandbox. El plan profesional inicial cuesta **$10.000 CLP por un
> mes**, editable desde Django Admin. La renovación es manual; no se realizan
> cobros reales ni renovaciones automáticas.

## 1. Resumen ejecutivo

El proyecto es una API REST monolítica modular implementada en Django y Django
REST Framework. Conecta clientes con profesionales de oficios del hogar y
mantiene sus perfiles, catálogo, solicitudes, posventa y soporte. Incluye:

- Autenticación por JWT y sesión Django, perfiles de cliente/profesional y
  controles de cuenta.
- Verificación administrativa de profesionales y almacenamiento privado de
  imágenes/PDFs de cédula para revisión manual.
- Catálogo de oficios, especialidades, zonas del hogar, búsqueda y disponibilidad.
- Solicitudes de visita con estados, reglas de agenda y vencimiento.
- Calificaciones, reclamos, tickets, notificaciones y contenidos profesionales.
- Overil, un asistente en español de Chile limitado al dominio de Overol, conectado
  a Gemini y protegido con filtros, límites de uso y control de salida.
- Transacciones Webpay Plus sandbox para visitas y suscripción profesional
  mensual manual.
- Django Admin, una vista local de demostración y una consola HTML de pruebas API
  local ignorada por Git.

No hay historial conversacional almacenado, cobro de suscripción recurrente
automático ni pagos reales.

## 2. Componentes y organización

```text
backend/
├── apps/
│   ├── authentication/   usuarios, perfiles, JWT, verificación y seguridad
│   ├── catalog/          oficios, especialidades, búsqueda y disponibilidad
│   ├── visits/           solicitudes, calificaciones, posventa y soporte
│   ├── assistant/        política de Overil, cuotas y Gemini
│   └── payments/         transacciones de visita y suscripciones sandbox
├── core/                 configuración Django y enrutamiento raíz
├── documentacion/        documentación del backend
├── docker-compose.yml    PostgreSQL/PostGIS
└── manage.py
```

### Tecnologías principales

| Componente | Uso |
|---|---|
| Django 6.1.1 | Aplicación, ORM, administración y migraciones. |
| Django REST Framework 3.18.3 | Endpoints REST, serializers, permisos y throttling. |
| Simple JWT 5.5.1 | Tokens de acceso/renovación y lista de revocación. |
| PostgreSQL/PostGIS | Persistencia principal y consultas geográficas. |
| Google Gen AI SDK | Generación de respuestas de Overil con Gemini. |
| Transbank SDK 6.1.0 | Webpay Plus en integración/sandbox. |
| Pillow | Procesamiento y validación de imágenes. |
| django-cors-headers | Cabeceras CORS. |

Las dependencias Python y sus versiones están en
[`requirements.txt`](requirements.txt); el archivo no instala ni fija la
versión del intérprete. La validación actual se ejecutó con CPython 3.14.8.
El backend usa la zona horaria `America/Santiago` y almacena datetimes con
soporte de zona horaria.

## 3. Arranque y configuración local

Ejecuta los comandos desde `backend/` en PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r documentacion\requirements.txt
docker compose up -d
python manage.py migrate
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

La API local queda en `http://127.0.0.1:8000/`. Django Admin está en
`/admin/`; el panel local de demostración está en `/local-dashboard/`.
`local-dashboard` requiere un usuario staff porque usa `staff_member_required`.

### Variables de entorno

La plantilla está en [`.env.example`](../.env.example). Django carga variables
con `python-dotenv`.

| Variable | Propósito | Valor de desarrollo en la plantilla |
|---|---|---|
| `DEBUG` | Modo de depuración Django. | `True`; cambiar antes de cualquier despliegue. |
| `SECRET_KEY` | Secreto de Django. | Marcador de posición; reemplazar por secreto aleatorio. |
| `ALLOWED_HOSTS` | Hosts permitidos por Django. | `localhost,127.0.0.1`. |
| `POSTGRES_DB` | Base PostgreSQL. | `overol_db`. |
| `POSTGRES_USER` | Usuario PostgreSQL. | `overol_user`. |
| `POSTGRES_PASSWORD` | Contraseña local PostgreSQL. | Marcador de posición. |
| `POSTGRES_HOST` | Host PostgreSQL. | `localhost`. |
| `POSTGRES_PORT` | Puerto PostgreSQL. | `5432`. |
| `GEMINI_API_KEY` | Credencial privada de Google AI Studio. | Vacía; necesaria para que Overil use Gemini. |
| `GEMINI_MODEL` | Identificador de modelo Gemini. | `gemini-3.5-flash-lite`. |
| `TRANSBANK_RETURN_URL` | URL que recibe el retorno de Webpay. | Callback local en el puerto 8000. |
| `PAYMENT_RESULT_URL` | Destino de redirección después del callback. | `http://localhost:3000/payment-result`. |
| `EMAIL_BACKEND` | Backend de correo Django. | Si no se define, se usa el backend de consola. |
| `PRIVATE_MEDIA_ROOT` | Carpeta privada para documentos de verificación. | `backend/private_media`. |

Los límites diarios de Overil y la cantidad máxima de tokens se definen en
`core/settings.py`, no en variables de entorno: 10 consultas por usuario/día,
50 globales/día y 300 tokens de salida. Los endpoints de recuperación limitan
el inicio a 5 y la confirmación a 10 solicitudes por hora y dirección IP.

### Persistencia local

`docker-compose.yml` inicia:

- `overol_db`: imagen `postgis/postgis:16-3.4`, puerto `5432`, volumen
  persistente `postgres_data`.

PostgreSQL es la base normal. `DATABASE_ENGINE=sqlite3` selecciona SQLite para
pruebas locales especiales; por defecto se usa PostgreSQL. La búsqueda por radio
requiere PostgreSQL con PostGIS.

## 4. Arquitectura HTTP, autenticación y errores

Las rutas de aplicación se registran en [`core/urls.py`](../core/urls.py):

| Prefijo | Módulo |
|---|---|
| `/api/auth/` | Cuentas, JWT, perfiles, verificación y administración. |
| `/api/catalog/` | Catálogo público y perfiles/búsqueda profesional. |
| `/api/professionals/` | Alias de búsqueda y administración del perfil propio. |
| `/api/` | Solicitudes, calificaciones, reclamos, tickets, notificaciones y centro profesional. |
| `/api/assistant/` | Chat Overil. |
| `/api/payments/` | Pagos de visitas y suscripción mensual profesional. |
| `/api/admin/verifications/` | Acceso administrativo a documentos privados. |

Salvo excepciones indicadas en la tabla de endpoints, se espera JSON y se usan
las clases de autenticación globales: JWT primero y sesión Django después. Los
endpoints autenticados esperan:

```http
Authorization: Bearer <access-token>
```

Los errores de validación de DRF suelen responder `400` con los campos
rechazados. Los errores de autorización suelen ser `401` o `403`, según falte
autenticación o falte permiso/rol. La respuesta puede incluir `detail`.

### JWT

- Solicitar par de tokens: `POST /api/auth/token/`.
- Access token: 15 minutos.
- Refresh token: 7 días.
- Se rota el refresh token; el token anterior se añade a blacklist.
- Para renovar: `POST /api/auth/token/refresh/`.
- Para verificar: `POST /api/auth/token/verify/`.
- Para cerrar sesión, se puede enviar el refresh token a
  `POST /api/auth/logout/`, que lo revoca.

`POST /api/auth/login/` es un flujo de sesión Django distinto: devuelve id,
correo y rol, no el par JWT. Para integración de frontend basada en bearer token,
usar `/api/auth/token/`.

### Seguridad de inicio de sesión

El modelo `User` maneja estados `ACTIVE`, `SUSPENDED`, `BLOCKED` y
`DEACTIVATED`. Un usuario cuyo estado no sea `ACTIVE` no puede obtener un token.
Tras tres intentos fallidos se bloquea temporalmente la cuenta por cinco minutos.
Las credenciales rechazadas se presentan con mensajes genéricos.

En registro y cambio de contraseña se aplican los validadores de Django, mínimo
de ocho caracteres y reglas contra contraseñas comunes o similares a los datos
del usuario. El registro requiere aceptación explícita de política/condiciones
y versión de esa política.

### Configuración que debe endurecerse antes de producción

Los valores actuales son de desarrollo, no un perfil de despliegue seguro:

- `DEBUG` tiene valor predeterminado `True`; establecerlo en `False`.
- `SECRET_KEY` tiene un valor de fallback de desarrollo; reemplazarlo y nunca
  reutilizarlo.
- Las credenciales PostgreSQL de ejemplo son marcadores de posición.
- `CORS_ALLOW_ALL_ORIGINS = True`; restringir a los dominios reales del frontend.
- El email predeterminado imprime mensajes en consola.
- Webpay está deliberadamente fijado a sandbox.
- `TRANSBANK_RETURN_URL` debe ser accesible desde Transbank para completar
  callbacks; `127.0.0.1` no es accesible desde Internet.
- Configurar HTTPS, hosts, almacenamiento de medios, logging, backups, límites de
  tasa y secretos con los procedimientos del entorno de despliegue.

## 5. Datos y relaciones

### Identidad y profesional

`authentication.User` extiende `AbstractUser` e incluye correo único como
identificador de inicio de sesión, rol, RUT opcional único, teléfono, dirección,
comuna, foto, estado de cuenta, aceptación de privacidad, contadores de intentos
de acceso y fecha de bloqueo. Los roles son `CLIENT`, `PROFESSIONAL` y `ADMIN`.
El método `save()` valida y normaliza nombre, apellido y RUT.

`ProfessionalProfile` está relacionado uno-a-uno con `User`. Guarda RUT único,
documentos frontal/trasero de cédula, estado de verificación (`PENDING`,
`APPROVED`, `REJECTED`), tarifa de visita, expiración de suscripción, promedio de
calificación, presentación, certificación, disponibilidad, horario, cobertura
por comuna y coordenadas. `has_active_subscription` compara la expiración con
la hora actual.

`VerificationCaseMessage` representa mensajes del profesional sobre su
verificación y respuesta/resolución administrativa.

Los documentos de cédula se guardan bajo `PRIVATE_MEDIA_ROOT`, separado de
`MEDIA_ROOT` público. Su endpoint de lectura exige autenticación administrativa.

### Catálogo

- `HomeZone`: zona del hogar (p. ej., cocina o baño).
- `TradeCategory`: oficio/categoría; puede asociarse a varias zonas y contiene
  palabras clave.
- `Specialty`: especialidad vinculada a una categoría y a profesionales.
- `ProfessionalTrade`: oficio que declara un profesional, años de experiencia,
  descripción, certificado, estado activo y si la certificación fue verificada.
  La combinación profesional/categoría es única.

### Solicitudes y posventa

- `VisitRequest`: cliente, profesional, especialidad, descripción de problema,
  fecha/hora, comuna, dirección, zona opcional, estado y fechas de confirmación.
- `Rating`: calidad, puntualidad y trato (1 a 5), comentario, autor y persona
  evaluada; un autor solo califica una vez una visita.
- `AfterSalesClaim`: reclamo único por visita, descripción, respuesta del
  profesional, resolución administrativa y estado.
- `SupportTicket`: ticket del usuario, descripción, visita opcional, respuesta y
  estado.
- `Notification`: aviso privado a un usuario, opcionalmente relacionado con una
  visita, con bandera de leído.
- `ProfessionalContent` y `ContentProgress`: contenido publicado por módulo
  (tributario, seguridad o gestión) y avance único por profesional/contenido.
  Las migraciones iniciales cargan el catálogo oficial de oficios y los
  recursos de seguridad de YouTube; los contenidos se administran en Django
  Admin.
- `AdminAuditLog`: administrador, acción, motivo, tipo e id del objeto afectado.

### Overil y pagos

- `AssistantDailyUsage`: contador por fecha para cada usuario y contador global.
  No contiene el texto de la conversación.
- `ProfessionalSubscriptionPlan`: código, nombre, monto, duración en meses y
  estado activo de un plan de suscripción. La base permite como máximo un plan
  activo; la migración inicial crea `professional-monthly` por $10.000 CLP y
  un mes.
- `PaymentTransaction`: pago Webpay con orden, sesión, importe, estado,
  respuesta de Transbank y hash del token. Se enlaza exactamente con una visita
  **o** con un perfil profesional; una restricción de base de datos impide cero o
  dos objetivos simultáneos. Los pagos de suscripción conservan referencia al
  plan y una copia de la duración aplicable al iniciar el pago; `amount` conserva
  el importe efectivamente enviado. Así un cambio posterior del plan no altera
  pagos ya iniciados. El token de Webpay no se persiste en claro.

## 6. Autenticación, perfiles y verificación

Todas las rutas de esta sección usan el prefijo `/api/auth/`.

| Método y ruta | Acceso | Comportamiento |
|---|---|---|
| `POST /register/` | Público | Crea cliente o profesional. Devuelve id, correo y rol (`201`). |
| `POST /login/` | Público | Inicia sesión Django y devuelve id, correo y rol. |
| `POST /token/` | Público | Obtiene access y refresh JWT. |
| `POST /token/refresh/` | Público con refresh válido | Rota y entrega token de acceso/refresco. |
| `POST /token/verify/` | Público con token | Verifica la firma/validez de un JWT. |
| `POST /logout/` | Autenticado | Blacklist de refresh enviado; `204` al cerrar. |
| `GET /me/` | Autenticado | Devuelve perfil propio. |
| `PATCH /me/` | Autenticado | Actualiza campos editables y, si corresponde, datos profesionales. Acepta JSON o multipart. |
| `POST /password/change/` | Autenticado | Comprueba contraseña actual, cambia clave y termina sesión Django. |
| `POST /password/reset/` | Público | Envía código por correo; responde `202` de forma genérica. |
| `POST /password/reset/confirm/` | Público | Valida código, aplica validadores y cambia contraseña. |
| `GET /verification/documents/` | Profesional | Devuelve estado de verificación y flags de archivos presentes, sin enlaces. |
| `POST /verification/documents/` | Profesional | Carga/reemplaza frontal y/o trasera de cédula vía multipart. |
| `GET /verification/messages/` | Profesional | Lista mensajes propios de verificación. |
| `POST /verification/messages/` | Profesional | Envía un mensaje de verificación. |
| `POST /verification/{profile_id}/approve/` | Rol `ADMIN` | Aprueba profesional solo con ambos documentos cargados, notifica, audita y resuelve el último mensaje. |
| `POST /verification/{profile_id}/reject/` | Rol `ADMIN` | Rechaza; requiere `reason`, notifica y audita. |
| `POST /admin/accounts/{user_id}/status/` | Rol `ADMIN` | Cambia estado con motivo; notifica y audita. |

El alta requiere `email`, `first_name`, `last_name`, `rut`, contraseña, rol,
aceptación de privacidad y versión. No se permite registrarse como admin. RUT
validado por Módulo 11; para profesional también es obligatorio `address` y
`professional_profile` con al menos una comuna de cobertura y un oficio.

Ejemplo mínimo de registro cliente:

```json
{
  "email": "cliente@example.cl",
  "first_name": "Ana",
  "last_name": "Prueba",
  "rut": "12345678-5",
  "password": "CambiarClaveSegura123!",
  "role": "CLIENT",
  "privacy_policy_accepted": true,
  "privacy_policy_version": "2026.1"
}
```

Para foto de perfil se acepta JPEG o PNG de hasta 5 MB; para certificación,
PDF/JPEG/PNG de hasta 5 MB. El archivo debe enviarse como `multipart/form-data`.
El perfil no permite modificar por `PATCH` el correo, username, nombres,
apellidos, RUT o rol. Datos sensibles como RUT y dirección profesional se
ocultan de la vista pública; el serializer de catálogo solo los devuelve a
usuarios cuyo rol sea admin.

### Cédulas y verificación

`GET /api/admin/verifications/{profile_id}/document/?side=front|back` devuelve el
archivo privado. Requiere usuario autenticado con rol `ADMIN` y permisos Django
de staff; `side` admite `front` o `back`. Si falta el archivo responde `404`;
si el parámetro no es válido, `400`.

La decisión administrativa y el cambio de cuenta escriben `AdminAuditLog` y
crean notificación. La vista local de demostración permite simular varios flujos
con actores locales; no sustituye permisos ni rutas de producción.

El profesional carga documentos con `POST /api/auth/verification/documents/`
(`multipart/form-data`) usando uno o ambos campos `id_card_front` y
`id_card_back`. Se aceptan JPEG/JPG o PNG, máximo 5 MiB y 25 megapíxeles, o
PDF con firma/cierre reconocibles de máximo 10 MiB por archivo. El PDF se
almacena para descarga y revisión administrativa manual; no se realiza OCR ni
extracción de datos. La respuesta expone
únicamente el estado y booleanos `front_uploaded`/`back_uploaded`; los archivos
no se sirven desde `MEDIA_URL` y se almacenan bajo `PRIVATE_MEDIA_ROOT`. Una
reposición deja el perfil en `PENDING`; la acción administrativa de aprobación
rechaza perfiles que no tengan ambos archivos. El endpoint de lectura
administrativa devuelve binario y exige rol `ADMIN` más `is_staff`.
En despliegue, restringir permisos del directorio privado y sus respaldos al
servicio backend y al personal autorizado; no exponerlo como carpeta estática ni
servir esos archivos desde el host web público.

El inicio `POST /api/auth/password/reset/` recibe `{"email":"..."}` y envía un
código aleatorio de seis dígitos. La respuesta es `202` genérica para evitar
enumeración de cuentas. El hash del código se almacena; vence a los 10 minutos,
se permite un envío por minuto por cuenta y se invalida tras cinco intentos
incorrectos. La confirmación recibe
`{"email":"...","code":"123456","new_password":"..."}` y aplica validadores
configurados. El código se consume tras un cambio exitoso. Los refresh tokens
vigentes se añaden a blacklist; access tokens previamente emitidos pueden
seguir válidos hasta su expiración JWT. El throttle por IP es 5 inicios y 10
confirmaciones por hora. En producción es obligatorio configurar correo saliente.

## 7. Catálogo, profesionales y geografía

### Catálogo público

Todas estas rutas usan `/api/catalog/` y son públicas:

| Método y ruta | Parámetros / salida |
|---|---|
| `GET /categories/` | Lista categorías con ids de zonas relacionadas. |
| `GET /specialties/` | Lista especialidades; admite `category_id`. |
| `GET /zones/` | Lista zonas del hogar. |
| `GET /communes/` | Lista comunas únicas cubiertas por profesionales visibles. |
| `GET /professionals/` | Busca profesionales visibles; ver filtros abajo. |
| `GET /professionals/{profile_id}/` | Perfil y opiniones del profesional visible. |

La migración `catalog.0005_seed_official_trade_catalog` carga las categorías
oficiales (66 categorías, con nombres normalizados) en una base nueva o
existente al aplicar migraciones. Los registros existentes no se reemplazan ni
se duplican si coincide el nombre. La lista se administra desde Django Admin y
el frontend debe obtenerla de `GET /api/catalog/categories/`, sin mantener una
lista paralela codificada en la interfaz.
No se añaden especialidades para esos oficios: se mantienen las especialidades
que ya existen en el catálogo, administrables desde Django Admin.

La búsqueda admite `keyword`, `zone_id`, `category_id`, `specialty_id`,
`commune` y, para radio, el conjunto `latitude`, `longitude`, `radius`. La
paginación entrega 20 resultados por página; `page_size` puede elevarse hasta
50. Los radios permitidos son 1000, 5000 y 10000 metros. Coordenadas deben estar
dentro de latitud [-90,90] y longitud [-180,180]. Las tres variables geográficas
deben presentarse juntas.

Los resultados públicos incluyen nombre, categorías, especialidades, tarifa de
visita, promedio, presentación, disponibilidad/cobertura y oficios activos.
RUT, dirección y comuna privada no se exponen a visitantes anónimos; RUT,
dirección y comuna se revelan únicamente a usuarios admin a través del serializer
de perfil.

La búsqueda/perfil/comunas filtran profesionales con verificación `APPROVED`,
cuenta `ACTIVE` y suscripción cuyo `subscription_expires_at` sea posterior al
momento actual. Si expira, no aparece en búsqueda ni detalle y no admite nuevas
solicitudes. La búsqueda por radio requiere PostGIS; sin PostGIS responde error
de validación, no realiza una aproximación silenciosa.

### Rutas para profesionales autenticados

`/api/professionals/` es un prefijo alternativo:

| Método y ruta | Rol | Comportamiento |
|---|---|---|
| `GET /api/professionals/search/` | Público | Mismo servicio de búsqueda que catálogo. |
| `GET /api/professionals/me/availability/` | Profesional | Lee horario, disponibilidad y cobertura. |
| `PATCH /api/professionals/me/availability/` | Profesional | Actualiza esos campos y coordenadas opcionales. |
| `GET /api/professionals/me/trades/` | Profesional | Lista oficios propios. |
| `POST /api/professionals/me/trades/` | Profesional | Añade un oficio, categoría existente y especialidades opcionales. |
| `PATCH /api/professionals/me/trades/{trade_id}/` | Propietario | Actualiza años, descripción y especialidades. |
| `DELETE /api/professionals/me/trades/{trade_id}/` | Propietario | Desactivación lógica (`is_active=false`), no elimina el registro. |

Las mismas operaciones de disponibilidad/oficios están disponibles bajo
`/api/catalog/professionals/me/...`. En disponibilidad, `latitude` y `longitude`
deben enviarse juntas; ambos valores se validan y guardan como coordenadas del
servicio.

## 8. Solicitudes de visita, ratings y postventa

Estas rutas están bajo `/api/` y requieren autenticación.

### Solicitudes

| Método y ruta | Rol / efecto |
|---|---|
| `GET /api/requests/` | Cliente ve sus solicitudes; profesional ve las recibidas. También ejecuta expiración de pendientes antiguos. |
| `POST /api/requests/` | Cliente crea una solicitud; el estado inicial es `PENDING`. |
| `POST /api/requests/{id}/accept/` | Profesional dueño acepta una pendiente. |
| `POST /api/requests/{id}/reject/` | Profesional dueño rechaza; requiere `reason`. |
| `POST /api/requests/{id}/cancel/` | Cliente dueño cancela una pendiente o aceptada; `reason` es opcional. |
| `POST /api/requests/{id}/cancel_professional/` | Profesional dueño cancela una aceptada con motivo obligatorio (máximo 500). |
| `POST /api/requests/{id}/finish/` | Profesional marca como finalizada. |
| `POST /api/requests/{id}/confirm/` | Cliente confirma que terminó el servicio. |

Al crear se requieren profesional, especialidad, descripción del problema,
fecha, hora, comuna y dirección. El serializer también valida:

- Cliente con rol `CLIENT`.
- Profesional aprobado, con suscripción vigente, disponible y con la especialidad seleccionada.
- Fecha no pasada, día de atención configurado y hora en formato `HH:MM` o
  intervalo `HH:MM - HH:MM` dentro del horario del profesional.
- Sin otra solicitud `PENDING` del mismo cliente al mismo profesional.
- Si se configura cobertura por comuna, la comuna solicitada debe estar incluida.

Se asigna vencimiento a 30 días. El acceso a teléfono/dirección/comuna de
contacto se habilita solo a las dos partes de una visita `ACCEPTED`,
`PROFESSIONAL_FINISHED` o `COMPLETED`.

Estados: `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED`, `EXPIRED`,
`PROFESSIONAL_FINISHED`, `COMPLETED`, `FORCED_CLOSED`. Para completar, cliente y
profesional deben confirmar; el orden de ambas confirmaciones puede variar.
Cuando se ejecuta una acción con estado o rol inválido, normalmente se responde
`409` o `403`.

Las transiciones `accept`, `reject`, `cancel`, `cancel_professional`, `finish` y
`confirm` notifican a la contraparte cuando la vista de acción las ejecuta.

### Expiración

El método `expire_pending_requests()` marca `EXPIRED` las solicitudes `PENDING`
con antigüedad de 30 días o más y crea una notificación al cliente. Se ejecuta al
listar solicitudes y al validar una solicitud nueva. También puede dispararse
manualmente:

```powershell
python manage.py expire_visit_requests
```

No hay un scheduler periódico configurado en este proyecto; en producción debe
programarse si se requiere expiración puntual independiente de actividad API.

### Calificaciones

`POST /api/ratings/` crea una calificación de la visita, con `quality`,
`punctuality` y `treatment` entre 1 y 5 y comentario opcional. Solo la pueden
calificar cliente o profesional involucrados, con visita `COMPLETED`, dentro de
los 30 días posteriores a `completed_at`. Se permite una calificación por autor
y visita. La persona evaluada es automáticamente la contraparte. Si se evalúa al
profesional se actualiza su promedio a partir de calidad, puntualidad y trato.

### Reclamos

| Método y ruta | Permiso |
|---|---|
| `GET /api/claims/` | Admin ve todos; otros usuarios ven reclamos donde son parte. |
| `POST /api/claims/` | Cliente de una visita completada crea un reclamo; uno por visita. |
| `POST /api/claims/{id}/respond/` | Profesional dueño responde un reclamo abierto. |
| `POST /api/claims/{id}/escalate/` | Cliente o profesional participante escala. |
| `POST /api/claims/{id}/resolve/` | Admin resuelve con `resolution`; registra auditoría. |

Estados de reclamo: `OPEN`, `PROFESSIONAL_RESPONDED`, `ESCALATED`,
`RESOLVED`. La respuesta del profesional notifica al cliente.

### Tickets de soporte

- `GET /api/tickets/`: admin ve todos; usuario ve los propios. Admite filtro
  opcional `?status=OPEN|IN_REVIEW|RESOLVED`.
- `POST /api/tickets/`: requiere asunto, descripción (máximo 500) y una visita
  que pertenezca al usuario según el serializer.
- `POST /api/tickets/{id}/resolve/`: solo admin, requiere `response`, actualiza
  estado, audita y notifica al usuario.

Estados: `OPEN`, `IN_REVIEW`, `RESOLVED`.

### Notificaciones y centro profesional

- `GET /api/notifications/`: solo notificaciones propias.
- `POST /api/notifications/{id}/read/`: marca como leída; no permite acceder a
  notificaciones de otro usuario.
- `GET /api/professional-center/content/`: requiere rol profesional y lista
  contenido visible ordenado por módulo/orden.
- La migración `visits.0004_seed_safety_resources` carga nueve recursos (seis
  videos, dos canales y una lista de reproducción de YouTube) en el módulo
  `SAFETY`. Se gestionan desde Django Admin como contenido externo; el backend
  guarda enlaces y descripciones, no descarga ni aloja los videos.
- `POST /api/professional-center/progress/`: rol profesional, registra avance
  del contenido; un contenido solo puede tener una marca por profesional.

## 9. Overil: asistente de hogar

### Contrato

`POST /api/assistant/chat/` requiere JWT y cuerpo:

```json
{
  "message": "El calefont no enciende y no tengo agua caliente, ¿qué especialista necesito?"
}
```

El mensaje debe tener entre 1 y 1500 caracteres. Respuesta normal:

```json
{
  "reply": "..."
}
```

Overil solo responde sobre mantenimiento/reparación del hogar, oficios y
funcionamiento de Overol. No atiende recetas, tareas escolares, programación,
política, deportes, matemáticas ni temas ajenos; rechaza intentos reconocidos de
cambiar su rol o ignorar instrucciones.

### Defensas en capas

1. **Filtro de entrada:** normaliza acentos y mayúsculas; identifica patrones de
   jailbreak, solicitudes fuera de dominio, emergencias de gas/electricidad e
   instrucciones técnicas riesgosas. Los rechazos se responden sin llamar a Gemini.
2. **Instrucción de sistema:** fija identidad y propósito de Overil, límites de
   dominio, límites de seguridad, tono chileno, no divulgar instrucciones y no
   inventar políticas o datos.
3. **Filtro de salida:** inspecciona el texto generado para rechazar contenido
   fuera de dominio o instrucciones peligrosas. Además, elimina una presentación
   inicial repetida (“Hola, soy Overil…”) porque la bienvenida corresponde al
   inicio de la conversación/interfaz, no a cada respuesta.

Ante olor a gas, fuego, explosión, chispas o descarga, la política prioriza
alejarse, no manipular la instalación, evacuar si existe riesgo y contactar
emergencias/proveedor o profesional certificado. No se deben tratar respuestas
de IA como diagnóstico profesional.

### Modelo, cuota y privacidad

- Proveedor: Google Gemini a través de `google-genai`; no se usa OpenAI.
- Modelo configurado por defecto: `gemini-3.5-flash-lite`.
- Máximo de salida: 300 tokens.
- Throttle DRF: 5 solicitudes por hora por usuario autenticado.
- Límite persistente adicional: 10 llamadas por usuario por día y 50 llamadas
  globales por día.
- La reserva de cuota se serializa con transacciones/bloqueos en base de datos.
- El texto del usuario se transmite a Google. No se conserva historial de chat en
  la base de datos; sí se guarda el contador diario de uso.
- Una solicitud fuera de tema o de seguridad no consume cuota diaria de Gemini,
  aunque está sujeta al throttle por hora del endpoint.
- La cuota global limita todo el entorno/base de datos que comparta esos
  registros; no equivale a una cuota por navegador.
- Si falta `GEMINI_API_KEY` o el proveedor no está disponible, se devuelve error
  de servicio `503`. Si se supera el límite diario, `429`.

Configurar clave en `.env`; nunca colocarla en frontend, pruebas públicas,
documentación o repositorio. El tratamiento de datos queda sujeto a los términos
vigentes de Google AI Studio; evitar enviar información sensible.

La consola local presenta una bienvenida propia al abrir el chat. La API es
stateless: una petición no contiene ni recupera el contexto de mensajes previos.

## 10. Pagos Transbank sandbox

### Entorno y seguridad de transacción

La app `payments` usa el SDK oficial para Webpay Plus en integración/sandbox.
Utiliza credenciales de integración públicas del SDK, no credenciales de
producción. Se almacenan orden de compra, session id, monto, estado y hash SHA-256
del token temporal. La respuesta de Transbank se confirma en el servidor; el
frontend no puede declarar un pago autorizado ni proponer su monto.

Estados de transacción: `PENDING`, `AUTHORIZED`, `REJECTED`, `FAILED`. Un pago
pendiente de más de 30 minutos se marca `FAILED` al intentar crear otro pago del
mismo objetivo. Se rechaza iniciar un segundo pago mientras haya otro pendiente.

### Suscripción profesional

| Método y ruta | Rol | Descripción |
|---|---|---|
| `POST /api/payments/professional-subscription/transbank/` | Profesional autenticado | Inicia pago por el plan activo; recibe cuerpo vacío `{}`. |
| `GET /api/payments/professional-subscription/` | Profesional autenticado | Devuelve `INACTIVE`, `ACTIVE` o `EXPIRED`, vigencia, plan activo e importe actual. |

Flujo:

1. El profesional inicia sesión y solicita iniciar pago.
2. El backend obtiene el único plan activo desde la base de datos; no acepta
   monto, código de plan ni duración enviados por el cliente. Si no hay plan
   activo, el inicio falla con `409`.
3. El servidor crea transacción `PENDING` con importe y duración copiados del
   plan, obtiene de Webpay `url` y `token` y los entrega al frontend.
4. El frontend debe hacer un formulario HTTP `POST` a la URL de Webpay con el
   campo `token_ws`.
5. Transbank devuelve el control a `TRANSBANK_RETURN_URL`.
6. El backend confirma el token con el SDK y verifica orden, sesión e importe.
   Solo con estado autorizado extiende `subscription_expires_at` por la
   duración guardada en la transacción.
7. El callback redirige a `PAYMENT_RESULT_URL`, incluyendo estado e id del
   perfil profesional.

Si la suscripción sigue vigente, renovar suma a la expiración la duración en
meses comprada; si ya venció o nunca estuvo activa, suma esa duración desde la
confirmación del pago. El cálculo es calendario y limita el día al último día
del mes de destino. Un callback repetido para un pago ya autorizado no duplica
meses.

El plan se gestiona en Django Admin (`ProfessionalSubscriptionPlan`); no existe
endpoint público para cambiar precio o duración. El panel permite a lo más un
plan activo, protegido además por una restricción única de base de datos. Para
cambiar a otro plan, desactivar primero el actual y luego activar el nuevo. La
duración y el monto de los pagos iniciados quedan guardados en la transacción.

Webpay Plus de esta integración no cobra automáticamente cada mes. El
profesional debe iniciar un nuevo pago manual; si vence, el perfil se oculta del
catálogo y no acepta nuevas solicitudes hasta renovar.

La consulta de estado devuelve además el plan actualmente activo:

```json
{
  "professional_profile_id": 7,
  "status": "ACTIVE",
  "amount": "10000",
  "plan": {
    "code": "professional-monthly",
    "name": "Suscripción profesional mensual",
    "duration_months": 1
  },
  "expires_at": "2026-12-13T23:59:59-03:00",
  "latest_payment": null
}
```

Si no existe un plan activo, la consulta responde `503`; no se inicia un pago y
la ruta de inicio responde `409`.

Respuesta de inicio (ejemplo):

```json
{
  "id": 42,
  "visit_id": null,
  "professional_profile_id": 7,
  "amount": "10000",
  "buy_order": "ov-...",
  "status": "PENDING",
  "url": "https://webpay3gint.transbank.cl/...",
  "token": "...",
  "environment": "sandbox"
}
```

### Pagos de visita existentes

El pago de visita es distinto a la suscripción y no la reemplaza:

| Método y ruta | Rol | Reglas |
|---|---|---|
| `POST /api/payments/visits/{visit_id}/transbank/` | Cliente dueño | Visita debe estar `ACCEPTED`; monto se toma de `visit_fee`. |
| `GET /api/payments/visits/{visit_id}/` | Cliente que pagó | Devuelve el pago más reciente propio de esa visita. |

No se recibe el importe desde el cliente. No se acepta visita no aceptada,
profesional sin tarifa válida o pago ya autorizado. El retorno es el mismo
`GET` o `POST /api/payments/transbank/return/` que se usa para la suscripción.

### Callback común

`GET` y `POST /api/payments/transbank/return/` son públicos porque los invoca
Transbank:

- Con `token_ws`, confirma el pago con el SDK y valida `buy_order`, `session_id`
  e importe contra la transacción local.
- Los campos `token_ws`, `TBK_TOKEN` y `TBK_ORDEN_COMPRA` se aceptan desde la
  query string o el body. Sin `token_ws`, toma `TBK_ORDEN_COMPRA` como retorno
  cancelado y actualiza la transacción pendiente correspondiente.
- Redirige a `PAYMENT_RESULT_URL` con `status`; pagos de visita agregan
  `visit_id`, pagos de suscripción agregan `professional_profile_id`.
- Respuesta de error/cancelación también se expresa como query string; el
  frontend debe interpretar el resultado y consultar la API si necesita el
  estado persistido.

Para pruebas reales de sandbox con retorno, el backend debe estar expuesto a
Transbank mediante URL pública HTTPS (por ejemplo, un túnel de desarrollo
controlado). Una URL localhost permite iniciar la transacción, pero no recibir
un callback externo por sí sola. La suite automatizada simula el SDK; no es una
compra real.

## 11. Herramientas, administración y datos de prueba

### Django Admin

`/admin/` utiliza el modelo de usuario personalizado y registra perfiles,
verificaciones, visitas, ratings, reclamos, soporte, notificaciones, contenidos,
avance y auditoría. Permite consultar la fecha de vencimiento de suscripción en
el perfil profesional. Las rutas administrativas de API validan el rol `ADMIN`;
la vista de documento también requiere permiso staff de Django.

### Panel local de demostración

`/local-dashboard/` es una vista de desarrollo protegida por `staff_member_required`.
Permite seleccionar actores locales y probar alta, solicitudes y acciones,
calificaciones, tickets, reclamos y avance de contenido. Las operaciones
modifican la base activa. No usar como panel público de producción.

### Carga de datos demo

```powershell
python manage.py seed_demo
```

El comando crea catálogo/usuarios de muestra para desarrollo. El código asigna
una contraseña de demostración conocida y los perfiles se marcan aprobados; no
es una herramienta de producción. Los perfiles seed actuales no reciben
automáticamente una suscripción vigente, por lo que, con las reglas nuevas, no
aparecen en búsquedas y no reciben nuevas solicitudes hasta pagar o hasta
configurar vigencia de prueba en una base local.

### Consola local de endpoints

Existe una página autónoma en `backend/local-api-tester/index.html`, ignorada por
Git. Desde `backend/`, se puede servir con:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory local-api-tester
```

Abrir `http://127.0.0.1:8765/`. La consola ofrece acceso a endpoints con JWT,
chat Overil, consulta/renovación de suscripción y pagos sandbox. Los tokens del
navegador se guardan en `sessionStorage` de esa pestaña. Varias operaciones del
explorador escriben datos en la base real conectada: usar usuarios, ids y
contenido de prueba; no ingresar datos sensibles.

## 12. Pruebas y verificación

Ejecutar desde `backend/`:

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Cobertura automatizada existente:

- Registro, privacidad, RUT, sanitización de nombres, bloqueo, JWT, blacklist,
  carga y acceso administrativo a documentos privados, recuperación de
  contraseña mediante código, caducidad/reintentos/reutilización y
  auditoría/notificaciones
  administrativas.
- Búsqueda, filtros, paginación, profesionales vencidos, coordenadas y permisos
  de edición de oficio/disponibilidad.
- Reglas de fecha/horario, ciclo de solicitudes, vencimiento, contacto privado,
  rating, reclamo, ticket y contenido profesional.
- Overil fuera de tema, jailbreak, emergencias, filtros de salida, cuota diaria,
  configuración del modelo y eliminación de saludos repetidos.
- Inicio de pago, ownership, vencimiento de pendientes, verificación del callback,
  monto discrepante, activación y renovación de suscripción.

Las llamadas a Gemini y Transbank están simuladas en la suite para evitar
consumo externo y compras. La consulta en sandbox necesita credenciales/red y el
flujo completo de retorno necesita callback accesible desde Transbank.

## 13. Guía rápida de estados y errores comunes

| Situación | Resultado esperado |
|---|---|
| Endpoint protegido sin access token | `401 Unauthorized`. |
| Rol equivocado para operación | `403 Forbidden`. |
| JSON o campo inválido | `400 Bad Request` con detalle de validación. |
| Cédula con formato inválido, imagen >5 MiB/25 megapíxeles o PDF >10 MiB | `400 Bad Request`; no se guarda el archivo. |
| Aprobación profesional sin ambas caras de cédula | `400 Bad Request`; permanece `PENDING`. |
| Recuperación de clave con código inválido, expirado, bloqueado o reutilizado | `400 Bad Request`; no cambia la contraseña. |
| Throttle de inicio/confirmación de recuperación excedido | `429 Too Many Requests`. |
| Transición de visita no permitida | `409 Conflict`. |
| Profesional aprobado, pero suscripción ausente/vencida | Oculto en catálogo; nueva solicitud rechazada por validación. |
| Inicio de segundo pago mientras hay uno pendiente vigente | `409 Conflict`. |
| Intento de pago de visita no `ACCEPTED` | `409 Conflict`. |
| Límite horario de Overil | `429 Too Many Requests`. |
| Límite diario de Overil | `429 Too Many Requests`. |
| Falta clave Gemini o proveedor no disponible | `503 Service Unavailable`. |
| Error del SDK al iniciar pago | `502 Bad Gateway`. |
| Retorno Transbank no válido o discrepancia de monto/orden | Redirección a resultado con `status=error`; no se activa la suscripción. |

## 14. Límites conocidos y decisiones explícitas

- El contrato de pagos ofrece integración sandbox; no autoriza cobros reales.
- La renovación de suscripción es manual; no existe tokenización de tarjeta ni
  cobro recurrente.
- La fecha de vencimiento está almacenada en el perfil. Hay entidad de planes,
  pero no histórico de vigencias separado: las transacciones autorizadas son el
  historial de pagos y cada una conserva el monto y la duración comprados.
- No se ha implementado endpoint para cancelación de renovación automática,
  porque no hay renovación automática que cancelar.
- Los perfiles profesionales existentes migran con `subscription_expires_at`
  nulo y quedan inactivos hasta una suscripción válida.
- Overil no conserva contexto entre llamadas ni historial de mensajes.
- El texto enviado al asistente se procesa con Google; no enviar información
  personal sensible.
- El CORS global, `DEBUG`, claves por defecto, correo de consola y uso de
  almacenamiento local requieren configuración antes de producción.
- El backend no configura por sí mismo un scheduler para expirar solicitudes;
  la operación periódica debe planificarse.
- El buscador geográfico depende de PostGIS; no está disponible en SQLite.
- La consola HTML local está ignorada por Git y no forma parte del frontend
  desplegado.

## 15. Referencias de implementación

- Configuración y rutas: [`core/settings.py`](../core/settings.py),
  [`core/urls.py`](../core/urls.py).
- Autenticación y perfiles: [`apps/authentication/models.py`](../apps/authentication/models.py),
  [`apps/authentication/serializers.py`](../apps/authentication/serializers.py),
  [`apps/authentication/views.py`](../apps/authentication/views.py).
- Catálogo: [`apps/catalog/models.py`](../apps/catalog/models.py),
  [`apps/catalog/services.py`](../apps/catalog/services.py),
  [`apps/catalog/views.py`](../apps/catalog/views.py).
- Solicitudes y posventa: [`apps/visits/models.py`](../apps/visits/models.py),
  [`apps/visits/serializers.py`](../apps/visits/serializers.py),
  [`apps/visits/views.py`](../apps/visits/views.py).
- Overil: [`apps/assistant/policy.py`](../apps/assistant/policy.py),
  [`apps/assistant/quota.py`](../apps/assistant/quota.py),
  [`apps/assistant/services.py`](../apps/assistant/services.py).
- Pagos: [`apps/payments/models.py`](../apps/payments/models.py),
  [`apps/payments/services.py`](../apps/payments/services.py),
  [`apps/payments/views.py`](../apps/payments/views.py).
- Pruebas por app: `apps/*/tests.py`.
