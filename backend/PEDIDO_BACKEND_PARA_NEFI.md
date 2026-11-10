# Overol — Qué necesita el backend para igualar al front (Streamlit)

Para: Nefi · De: Benjamín · Revisado sobre `Overol.zip` (backend Django 6.1 + DRF + SimpleJWT)

El front ya tiene todas estas funciones funcionando con SQLite. Esta lista dice **qué falta en el backend** para poder conectarlas, ordenada por prioridad.
Los nombres de campos son una propuesta; si prefieres otros, avísame y me adapto.

---

## Prioridad 1 — Sin esto el front no puede conectarse

### 1.1 Endpoints de catálogo (hoy no existen)
El buscador y el formulario de solicitud necesitan listar opciones. Hoy solo existe `/api/catalog/professionals/`.

| Endpoint | Devuelve |
| :--- | :--- |
| `GET /api/catalog/categories/` | `id, name, keywords, home_zones[ {id,name} ]` |
| `GET /api/catalog/specialties/?category_id=` | `id, name, category_id` |
| `GET /api/catalog/zones/` | `id, name` (zonas del hogar) |
| `GET /api/catalog/communes/` | lista de comunas de cobertura (o un campo fijo en el front, a definir) |

### 1.2 Serializer de profesionales
- `ProfessionalResultSerializer` incluye `'trades'` en `fields` y define `get_trades`, pero **no declara el campo**: DRF devuelve solo una lista de IDs. Declarar `trades = serializers.SerializerMethodField()`.
- Agregar al listado y detalle público: `years_experience` total, `coverage` (comunas), `work_days`, `work_start`, `work_end`, `bio`/presentación, `profile_photo` (URL), `commune`.
- Agregar en cada oficio: `category_id`, `specialties` del oficio y su `rating_avg` (el front muestra **la valoración por oficio**).
- En el detalle, cada opinión debe incluir `author_name` (primer nombre + inicial) y `category` (oficio evaluado).

### 1.3 Solicitudes: el serializer no entrega lo que el front muestra
`VisitRequestSerializer` solo devuelve ids. Falta, en lectura:
- `client_name`, `professional_name`, `specialty_name`, `category_name`.
- **Datos de contacto** (`phone`, `address`, `commune`) de la contraparte, **solo cuando el estado es `ACCEPTED`, `PROFESSIONAL_FINISHED` o `COMPLETED`**. Antes de eso, no deben viajar (regla de privacidad del front).
- `cancelled_by` (`CLIENT`/`PROFESSIONAL`) y `cancel_reason`.
- `client_confirmed_at` y `professional_confirmed_at` (para mostrar «esperando confirmación de la otra parte»).
- `expires_at` (ver 2.1).

### 1.4 Fecha y hora de la visita
El modelo tiene `tentative_schedule` como texto libre. El front envía **fecha + franja horaria** (ej. `2026-11-03`, `09:00 - 10:00`) y valida contra la disponibilidad.
- Reemplazar/añadir: `visit_date` (DateField) y `visit_time` (CharField o dos TimeField).
- Agregar `commune` y `home_zone` a la solicitud (el front los pide).

### 1.5 Aprobación de profesionales para la demo
Los profesionales nuevos quedan `PENDING` y no aparecen en el catálogo. Necesito **3 profesionales aprobados + 2 clientes + 1 admin de demostración** (un comando `python manage.py seed_demo` o fixture), con oficios, especialidades, cobertura y horarios cargados.

---

## Prioridad 2 — Reglas de negocio que el front ya cumple

### 2.1 Vencimiento de solicitudes a **72 horas** (hoy: 30 días y solo manual)
- Cambiar el umbral de `expire_visit_requests` a 72 h.
- Que corra solo: o bien Celery/cron con Redis (ya está en el docker-compose), o bien **vencimiento perezoso** al listar/crear solicitudes (más simple para la entrega).

### 2.2 Bloqueo de login: **3 intentos → 5 minutos** (hoy: 6 horas)
- Cambiar `timedelta(hours=6)` a `timedelta(minutes=5)` en `LoginSerializer` y `OverolTokenObtainPairSerializer`.
- Al estar bloqueado, responder **HTTP 429** con `{"detail": "...", "retry_after": segundos}` en vez de «Credenciales inválidas», para que el front muestre la cuenta regresiva.
- Opcional: devolver `attempts_left` en el 401.

### 2.3 Cancelaciones
- **Cliente:** poder cancelar solicitudes `PENDING` **y `ACCEPTED`** (hoy solo `PENDING`).
- **Profesional (nuevo):** `POST /api/requests/{id}/cancel_professional/` con `{"reason": "..."}`:
  - solo si está `ACCEPTED`, motivo obligatorio, **máximo 500 caracteres**;
  - guarda `cancelled_by=PROFESSIONAL` y `cancel_reason`; notifica al cliente.
- Validar largo máximo de 500 en el rechazo también (`RejectSerializer`).

### 2.4 Disponibilidad del profesional (hoy no existe nada)
Campos en `ProfessionalProfile` + endpoint propio:
- `work_days` (lista: Lunes…Domingo), `work_start`, `work_end` (HH:MM), `is_available` (bool), `coverage_communes` (lista de comunas).
- `GET/PATCH /api/professionals/me/availability/`.
- `VisitRequestSerializer.validate` debe **rechazar** solicitudes fuera de los días/horas del profesional o a una fecha pasada, y duplicados (mismo cliente + mismo profesional con una solicitud `PENDING`).

### 2.5 Oficios múltiples por profesional (gestión)
El modelo `ProfessionalTrade` existe pero no hay API. Falta:
- `GET/POST /api/professionals/me/trades/` (crear oficio con `category`, `years_experience`, `description`, especialidades).
- `PATCH /api/professionals/me/trades/{id}/` y **desactivar** (`is_active=false`), nunca borrar.
- Las especialidades hoy se asignan solo desde el admin de Django (`Specialty.professionals`). Debe poder hacerlo el propio profesional por API, y al registrarse.

### 2.6 Registro de profesional
`RegistrationSerializer` solo guarda `id_card_front`, `id_card_back` y `visit_fee`. Falta aceptar y guardar:
- `address` (ya existe en `User`, pero hacerlo **obligatorio para PROFESSIONAL**, hoy solo lo exige para cliente en la doc),
- `coverage_communes`, `trade/categories`, `specialties`, `years_experience`, `bio`.

---

## Prioridad 3 — Para igualar perfiles y soporte

### 3.1 Perfil tipo LinkedIn
- `PATCH /api/auth/me/` hoy solo acepta `phone`, `address`, `commune`. Agregar: `bio`/presentación (≤ 500), `profile_photo` (multipart), `contact_preference`, y para profesional: `headline`, `visit_fee`, `certifications` (subida de archivo con validación de tipo y tamaño ≤ 5 MB).
- El front valida por firma de archivo (JPG/PNG/PDF); el backend debería validar extensión **y** contenido.

### 3.2 Mensajes a soporte sobre una solicitud
`SupportTicket` existe, pero:
- Limitar `description` a **500 caracteres**.
- Que `visit` sea **obligatorio** (el soporte del front es por solicitud) y que valide que la solicitud pertenezca al usuario.
- Que el usuario pueda ver la respuesta (`response`) — ya está — y que llegue notificación.
- **Admin:** `GET /api/tickets/?status=OPEN` debe listar **todos** los tickets si el usuario es `ADMIN` (hoy el queryset es siempre `user=request.user`, así que el admin no los ve por API). Lo mismo con `/api/claims/` (hoy el admin no ve reclamos).

### 3.3 Valoraciones
- El front califica **por oficio** (la valoración de cada oficio es independiente). Agregar `trade`/`category` a `Rating` y recalcular el promedio por `ProfessionalTrade`, no solo `rating_avg` global.
- Valoración del profesional hacia el cliente: ya existe como `Rating` con `target=cliente`; falta exponer `client_rating_avg` en el perfil del cliente que ve el profesional.
- `rating_avg` hoy usa `Avg` triple con `sum(scores.values())/3`; si no hay valores previos puede fallar con `None`. Proteger ese caso.

### 3.4 Sesión persistente
JWT de 15 min + refresh de 7 días ya sirve. Pedido mínimo: `ROTATE_REFRESH_TOKENS=True` y `BLACKLIST_AFTER_ROTATION=True` (+ app `token_blacklist`) y un `POST /api/auth/logout/` que invalide el refresh enviado (hoy hace `logout()` de sesión Django, que no afecta al JWT).

### 3.5 Visibilidad por rol
- Los endpoints de catálogo son públicos (`AllowAny` implícito). El front muestra **perfil completo y agenda solo a clientes con sesión**; los visitantes ven solo la tarjeta. Opción: `/api/catalog/professionals/{id}/` devuelve versión reducida si no hay token o el rol no es `CLIENT`.

---

## Encontrado al conectar login, registro y perfil (Fases 1 y 2 del front)

### 4.1 Correo sin configurar → recuperación de contraseña con error 500
`settings.py` no define `EMAIL_BACKEND` ni `EMAIL_HOST`, así que Django usa SMTP en `localhost:25`. `POST /api/auth/password/reset/` probablemente falla con **500** si el correo existe y hay que enviarlo.
- Para desarrollo basta con `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` (el correo se imprime en la consola).
- Mientras tanto, el front **oculta** la recuperación de contraseña en modo `api`.

### 4.2 `GET /api/auth/me/` no devuelve `id`
`ProfileSerializer` no incluye `id`. El front enlaza su copia local por correo, pero lo va a necesitar para comparar con `professional`, `client`, `recipient`, etc. en solicitudes y notificaciones. Pedido: agregar `id` (solo lectura) y, para profesionales, el `id` de su `ProfessionalProfile` y su `verification_status`.

### 4.3 El registro no aplica los validadores de contraseña de Django
`RegistrationSerializer` solo exige `min_length=8`; no llama a `validate_password` como sí lo hace `PasswordChangeSerializer`. Comprobado contra el backend real: el registro con la clave `12345678` respondió **201**. Pedido: llamar a `validate_password(password)` en `validate()` y devolver los mensajes en el campo `password`.

### 4.4 Nombre con caracteres no permitidos → error 500
`sanitize_person_name` se ejecuta dentro de `User.save()` y lanza `django.core.exceptions.ValidationError`, que DRF no convierte en 400. Un nombre como «Ana-María» o con un número termina en **500**. Pedido: validar `first_name` y `last_name` en el serializer (`validate_first_name`/`validate_last_name`) para responder 400 con el mensaje.

*Comprobado contra el backend real (18-10-2026):* registrar `first_name: "Ana-María"` responde **HTTP 500**.

**Limitación temporal en el front:** mientras esto no se corrija, en modo `api` el formulario de registro solo acepta letras, espacios y apóstrofes en nombre y apellido (la misma regla de `sanitize_person_name`). Un nombre compuesto con guion («Ana-María») se rechaza con un mensaje y hay que escribirlo con espacio. Cuando el backend responda 400, conviene decidir si se permiten guiones (son comunes en nombres reales) y quitar esta validación del front.

### 4.5 Mensajes reales del inicio de sesión (`POST /api/auth/token/`)
Observado contra el backend real:
- Clave incorrecta o correo inexistente → `401 {"detail": "No se encontró una cuenta de usuario activa para las credenciales provistas"}` (mensaje por defecto de SimpleJWT).
- Cuenta bloqueada (tras 3 fallos), **incluso con la clave correcta** → `401 {"detail": "Credenciales inválidas."}`. Según el código, una cuenta no `ACTIVE` responde lo mismo.

El front **no** se apoya en esa diferencia de texto (depende del idioma y puede cambiar). En modo `api` muestra «Correo o contraseña incorrectos. Si ya te equivocaste 3 veces, tu cuenta puede estar bloqueada por seguridad hasta 6 horas.». Sigue en pie el pedido 2.2 (bloqueo de 5 min y **429** con `retry_after`).

### 4.6 `createsuperuser` crea un usuario con rol `CLIENT`
El modelo `User` no tiene un manager propio, así que el superusuario queda con `role=CLIENT` y sin RUT. Puede entrar a `/admin/`, pero en el front y en la API se comporta como cliente: los endpoints de administración revisan `role == ADMIN`, no `is_superuser`. Pedido: que `createsuperuser` asigne `role=ADMIN` (manager propio), o documentar que hay que cambiar el rol en `/admin/` después de crearlo.

---

## Lo que NO hace falta (fuera de alcance acordado)
Validación de identidad automática, administración avanzada, geolocalización real, pagos, IA.

## Notas técnicas para que pruebe rápido
- Credenciales de demo del front (SQLite): ver `README.md` del front. Para la API, crear equivalentes con el comando de seed del punto 1.5.
- El front va a consumir **solo** `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/me/`, `/api/catalog/*`, `/api/requests/*`, `/api/ratings/`, `/api/claims/`, `/api/tickets/`.
- CORS ya está abierto en desarrollo; no hay que tocarlo.
