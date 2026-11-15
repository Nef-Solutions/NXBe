# Pruebas manuales contra el backend real

Las pruebas automáticas usan una imitación del backend. Estas se hacen a mano, con el backend Django de verdad y un navegador.
Anota en cada caso ✅ o ❌ y lo que viste.

**Etapa B:** login, bloqueo, registro, completar perfil, Mi perfil, contraseñas y sesión recordada (casos 1 a 24).
**Etapa C:** Cobertura y solicitudes (casos C1 a C17).
**Etapa C2:** suscripción con Webpay, cédula, recuperación con código, oficios del backend y asistente (casos S1 a S12).
**Etapa D:** valoraciones, reclamos y tarifa informativa (casos D1 a D7).
**Etapa E:** notificaciones y tickets de soporte (casos E1 a E5).
**Etapa F:** perfil, reputación, oficios y desarrollo profesional (casos F1 a F6).
**Etapa G:** panel del admin (casos G1 a G6, al final).

## Preparación (una vez)

```powershell
# 1. Backend (desde la carpeta backend del repositorio)
cd "C:\Users\benja\Documents\NXBe_repo\backend"
docker compose up -d                          # solo Postgres/PostGIS (Redis ya no se usa)
$env:PYTHONDONTWRITEBYTECODE = "1"
$py = "C:\Users\benja\Documents\Overol_envs\backend_venv\Scripts\python.exe"
& $py -m pip install -r documentacion\requirements.txt   # trae google-genai y transbank-sdk
& $py manage.py migrate
& $py manage.py seed_demo
& $py manage.py runserver 127.0.0.1:8000     # déjala abierta

# 2. Front (otra ventana)
cd "C:\Users\benja\Documents\NXBe_repo\Overol Front"
& "C:\Users\benja\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe" app.py
```

**Usuarios de `seed_demo`:** contraseña `OverolDemo123!`.

| Rol | Correo |
|---|---|
| Cliente | `cliente1@demo.overol.cl`, `cliente2@demo.overol.cl` |
| Profesional | `profesional1@demo.overol.cl` a `profesional3@demo.overol.cl` |
| Admin | `admin@demo.overol.cl` (también entra a `/admin/` de Django) |

**`backend/.env`:** además de lo de Postgres, define `PAYMENT_RESULT_URL=http://localhost:8501/` (para que Webpay vuelva al front) y, si quieres respuestas reales del asistente, la clave de Gemini. Sin esa clave, el asistente responde «no disponible» y todo lo demás funciona.

**Suscripción de los profesionales de demo:** el catálogo y las solicitudes exigen una suscripción vigente y `seed_demo` no la trae. Arranca con `scripts\demo_api.ps1 -DemoListo` (les da horario y un mes de suscripción), o en `/admin/` → Professional profiles pon a `profesional1` a `profesional3` una fecha futura en «Suscripción vigente hasta» (o págala en el caso S3).

**Atajo:** `powershell -ExecutionPolicy Bypass -File scripts\demo_api.ps1 -DemoListo` hace la preparación de abajo (Docker, dependencias, `migrate`, `seed_demo`, `runserver` y el front).

**Antes de empezar:** confirma que la carpeta del front **no** tiene `overol.db`, o bórralo. Al terminar, revisa que siga sin existir.

## Casos

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| 1 | Registro de cliente | «Ingresar o registrarme» → «Crear cuenta» → Cliente, datos válidos y RUT nuevo → «Crear cuenta» | Aviso «Cuenta creada correctamente». En `/admin/` → Users aparece la cuenta, con rol `CLIENT`, teléfono, dirección y comuna |
| 2 | Registro de profesional con un oficio que el backend no tiene | Profesional, oficio **Pintura**, comunas Santiago y Ñuñoa | Error: «El oficio «Pintura» todavía no está disponible…», con la lista de oficios del backend. No se crea ninguna cuenta |
| 3 | Registro de profesional | Igual, con oficio **Gasfitería** y 4 años de experiencia | Cuenta creada. En `/admin/` → Professional profiles: `coverage_communes` = Santiago y Ñuñoa, estado `PENDING`. En Professional trades: un oficio Gasfitería con 4 años |
| 4 | Contraseña débil | Registro con la contraseña `password123` | Error «La contraseña no cumple las reglas de seguridad del servidor:» con la lista de reglas |
| 5 | Correo repetido | Registro con `cliente1@demo.overol.cl` | Error «Correo: …ya existe…» |
| 6 | Login correcto | `cliente1@demo.overol.cl` con «Mantener mi sesión» marcado | Entra como cliente. La barra muestra Inicio, Buscar profesionales, Mi perfil y Quiénes somos |
| 7 | Clave incorrecta | `cliente2@demo.overol.cl` con una clave equivocada | «Correo o contraseña incorrectos. Tras 3 intentos fallidos, la cuenta se bloquea por seguridad durante 5 minutos.» |
| 8 | Bloqueo | 3 claves equivocadas seguidas y después la clave correcta | «Cuenta bloqueada por intentos fallidos. Intenta de nuevo en 5 minutos» (o 4, según el tiempo). Pasados 5 minutos, entra |
| 9 | Completar perfil | En `/admin/` → Users, borra el teléfono y la dirección de `cliente2` → entra con esa cuenta | Pide «Completa tu perfil» antes de mostrar la barra. Al guardar teléfono, dirección y comuna, entra. En `/admin/` quedan guardados |
| 10 | Mi perfil del cliente | Cliente → Mi perfil → cambia la dirección → Guardar | Aviso «Tus datos fueron actualizados». En `/admin/` la dirección cambió. No aparece «Preferencia de contacto», porque el backend no la guarda para clientes |
| 11 | Mi perfil del profesional | `profesional1` → Mi perfil → preferencia «Correo electrónico», un titular y una presentación → Guardar | En `/admin/` → Professional profiles: `contact_preference`, `headline` y `bio` actualizados. Arriba dice «Tu identidad está verificada» |
| 12 | Profesional pendiente | Entra con el profesional del caso 3 | Aviso «Tu cuenta está pendiente de verificación» y no aparece en «Buscar profesionales». Apruébalo en `/admin/` (Professional profiles → `verification_status` = APPROVED) y aparece en el catálogo |
| 13 | Cambiar contraseña | Mi perfil → «Cambiar contraseña» con la actual equivocada, y después con la correcta | Primero: «La contraseña actual no es correcta». Después: «Contraseña actualizada», y la nueva clave sirve para entrar |
| 14 | Recuperar contraseña | Ver el caso S6 (ahora es con un código de 6 dígitos) | — |
| 15 | Recargar con la sesión recordada | Con el caso 6 abierto, recarga la página (F5) | Sigue dentro, sin pedir la contraseña |
| 16 | La cookie no lleva tokens | F12 → Application → Cookies → `localhost:8501` | Hay una sola cookie `overol_session`, con un valor aleatorio largo, SameSite = Lax. **No** contiene `eyJ…` (un token JWT), ni el correo ni el nombre |
| 17 | Cerrar sesión | «Cerrar sesión» en la barra lateral → recarga la página | Vuelve a la vista de visitante y al recargar no entra solo. La cookie `overol_session` desaparece |
| 18 | Cerrar y reabrir el navegador | Entra con «Mantener sesión», cierra el navegador entero y vuelve a abrir `localhost:8501` | Sigue dentro |
| 19 | Reinicio del servidor del front | Con la sesión recordada, detén el front (Ctrl+C), arráncalo de nuevo y recarga | Pide iniciar sesión otra vez (el token vivía en la memoria del servidor). La cookie vieja se borra |
| 20 | Sin «Mantener sesión» | Entra con la casilla desmarcada → recarga la página | Al recargar vuelve a la vista de visitante |
| 21 | Cuenta desactivada | Con un cliente adentro, en `/admin/` → Users desmarca **Active** (o `account_status` = DEACTIVATED con Active desmarcado) → espera 1 minuto y haz clic en cualquier sección | Se cierra la sesión con el aviso «Tu sesión terminó». Si intenta entrar: «Correo o contraseña incorrectos» |
| 21b | Cuenta suspendida | Igual, pero solo `account_status` = SUSPENDED (Active marcado) | **Limitación conocida del backend:** la sesión abierta sigue funcionando hasta que vence el token de renovación, porque SimpleJWT solo revisa `is_active`. Un ingreso nuevo sí se rechaza. Está en el pedido a Nefi |
| 22 | Admin | Entra con `admin@demo.overol.cl` | Ver la etapa G (casos G1 a G6) |
| 23 | Backend apagado | Detén runserver y recarga el front | La portada abre sin cifras ni destacados. «Profesionales» muestra «No se pudo cargar el catálogo». Al intentar ingresar: «No se pudo conectar con el servidor de Overol» |
| 24 | Sin SQLite | Al terminar todo lo anterior | La carpeta del front sigue **sin** `overol.db` |

## Etapa C: Cobertura y solicitudes

**Antes de empezar:** hoy `seed_demo` no carga horario (pedido 5.1), así que ningún profesional de demo puede recibir solicitudes. El caso C1 lo arregla para `profesional1`.

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| C1 | Cobertura | `profesional1` → «📍 Cobertura» → días Lun a Vie, de 09:00 a 18:00, comunas Santiago y Ñuñoa, disponible, tarifa 15000 → Guardar | Aviso «Cobertura, días, horario y tarifa actualizados». En `/admin/` → Professional profiles: `work_days` = ["Lunes", …, "Viernes"] (con **nombre completo**), `work_start` 09:00, `work_end` 18:00, `visit_fee` 15000 |
| C2 | Cobertura se recarga | Sal y vuelve a «Cobertura» | Muestra lo guardado en C1 (días abreviados Lun…Vie) |
| C3 | Formulario de solicitud | `cliente1` → Buscar profesionales → perfil de `profesional1` | Formulario con oficio, **especialidad** (las del profesional), comuna (solo su cobertura), fecha (un día hábil), franjas entre 09:00 y 18:00, y la dirección de `cliente1` bloqueada |
| C4 | Solicitar | Describe el trabajo → «Solicitar visita» | Aviso «Solicitud enviada». En `/admin/` → Visit requests: una solicitud PENDING con la especialidad, la fecha, la franja y la dirección |
| C5 | Duplicada | Repite C4 con el mismo profesional | Error «…Ya tienes una solicitud pendiente para este profesional.» (sin `non_field_errors` ni texto técnico) |
| C6 | Día no laboral | Elige un sábado y envía (con otro profesional configurado, o cancela antes la de C4) | Error «Fecha: La solicitud está fuera de los días de atención del profesional.» |
| C7 | Profesional sin horario | Perfil de `profesional2` (sin C1) | Aviso «todavía no configuró su horario» y sin botón «Solicitar visita» |
| C8 | Mis solicitudes | `cliente1` → «📋 Mis solicitudes» | La solicitud aparece como **Pendiente**, con «vence el …» igual a `expires_at` del backend (hoy, 30 días después de creada), y **sin** datos de contacto |
| C9 | Pestañas del profesional | `profesional1` → «📋 Solicitudes» | Pestaña «Pendientes (1)» con la solicitud y sin datos de contacto del cliente |
| C10 | Rechazar con motivo | Rechazar → motivo «Otro» sin detalle → luego con detalle | Primero pide explicar el motivo. Después queda **Rechazada**. `cliente1` ve el motivo completo y en `/admin/` está en `rejection_reason` |
| C11 | Aceptar y contacto | Nueva solicitud de `cliente1` → `profesional1` la acepta | Queda **Aceptada**. Cada uno ve el teléfono y la dirección del otro |
| C12 | Finalizar (profesional primero) | `profesional1` → «Confirmar finalización» → `cliente1` → «Confirmar finalización» | Tras el profesional: el cliente ve **Esperando confirmación** y «Falta tu confirmación». Tras el cliente: **Finalizada** para ambos (`COMPLETED` en `/admin/`) |
| C13 | Finalizar (cliente primero) | Otra solicitud aceptada: primero confirma el cliente, después el profesional | Tras el cliente sigue **Aceptada**, con «Ya confirmaste…». Tras el profesional: **Finalizada** |
| C14 | Cancelación del profesional | Solicitud aceptada → «Cancelar solicitud» sin motivo → con motivo | Primero pide el motivo. Después queda **Cancelada** y el cliente ve el motivo |
| C15 | Cancelación del cliente | Solicitud pendiente → «Cancelar solicitud» → advertencia → **mantén presionado** el botón | Queda **Cancelada** y en `/admin/` `cancelled_by` = CLIENT. «No, mantener mi solicitud» no cancela |
| C16 | Estado cerrado por Overol | En `/admin/` cambia una solicitud a FORCED_CLOSED | El cliente la ve como **Cerrada por Overol** y el profesional, en la pestaña de cerradas |
| C17 | Profesional nuevo recibe solicitudes | Registra un profesional de **Gasfitería** marcando las especialidades «Fugas de agua» y «Destapes» (sin especialidades, el formulario no deja enviar) → en `/admin/` apruébalo (`verification_status` = APPROVED) → entra con él y configura «Cobertura» (C1) → `cliente1` abre su perfil | En `/admin/` → Professional profiles → Specialties: «Fugas de agua» y «Destapes». En el perfil, «Especialidad» ofrece esas dos y «Solicitar visita» crea la solicitud (PENDING) |

## Etapa C2: suscripción, cédula, recuperación con código, oficios y asistente

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| S1 | Suscripción vigente | `profesional1` (con fecha futura en `/admin/`) → «💳 Suscripción» | Estado **Vigente**, la fecha de vencimiento, monto $10.000 y el botón «Renovar con Webpay» |
| S2 | Sin suscripción | Borra la fecha en `/admin/` → recarga «Suscripción». Luego `cliente1` busca profesionales | Estado **Sin suscripción** y el aviso «no apareces en el catálogo». El cliente ya no lo ve en la búsqueda |
| S3 | Pagar con Webpay (sesión recordada) | Entra con «Mantener mi sesión» → «Pagar con Webpay» → «Ir a Webpay para pagar» → en Webpay paga con la tarjeta de prueba de Transbank para el ambiente de integración (la que indica su documentación) | Pasa a Webpay en la misma pestaña. Al terminar vuelve a `localhost:8501`, abre «Suscripción» y dice «Pago confirmado…». En `/admin/` → Payment transactions: AUTHORIZED, y la fecha de vencimiento avanzó un mes. **Anota si Transbank logra volver a `127.0.0.1:8000`** (la guía del backend advierte que podría no hacerlo) |
| S4 | Pago anulado | Repite S3 y en Webpay anula la compra | Vuelve con «El pago no se completó (estado: rechazado)» y la suscripción no cambia |
| S5 | Vuelta sin sesión | Repite S3 **sin** «Mantener mi sesión» | Al volver pide iniciar sesión, con el aviso «Volviste de Webpay». Tras ingresar, muestra el resultado |
| S6 | Recuperar contraseña con código | «¿Olvidaste tu contraseña?» → `cliente1@demo.overol.cl` → «Enviar código» → copia el código de 6 dígitos que se imprime en la **ventana de runserver** → escríbelo con una contraseña nueva | Primero «recibirás un código». Con un código equivocado: «El código no es válido o ha expirado.». Con el correcto: «Contraseña restablecida» y la nueva clave sirve. Las sesiones abiertas de esa cuenta se cierran |
| S7 | Subir la cédula | Profesional nuevo (caso 3 o C17) → «🪪 Verificación» → frente PNG y reverso PDF → «Enviar documentos» | «Documentos enviados». Ambos lados figuran ✅. En `/admin/` el perfil queda PENDING con los dos archivos |
| S8 | Archivo inválido | Sube un `.png` que en realidad sea otro tipo, o una imagen de más de 5 MB | El front lo rechaza antes de enviar |
| S9 | Mensaje de verificación | En «Verificación» escribe un mensaje → «Enviar mensaje». En `/admin/` → Verification case messages, responde | El mensaje aparece en el hilo y luego la respuesta de Overol |
| S10 | Oficios del backend | Registro de profesional | La lista tiene los **66 oficios** del backend. Con «Soldador» (sin especialidades) avisa que no recibirá solicitudes hasta tenerlas y deja registrarse; con «Gasfitería» pide especialidades |
| S11 | Asistente | `cliente1` → «🤖 Asistente» → pregunta por una llave que gotea (con la clave de Gemini configurada) | Aviso de no escribir datos personales. Responde Overil. Al recargar sin «Mantener sesión», el historial se pierde |
| S12 | Límite y caída del asistente | Envía 6 consultas en una hora. Luego quita la clave de Gemini y reinicia runserver | La sexta: «Llegaste al límite de consultas…». Sin la clave: «El asistente no está disponible en este momento» |

## Etapa D: valoraciones, reclamos y tarifa informativa

Necesitas una solicitud **Finalizada** entre `cliente1` y `profesional1` (casos C11 y C12).

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| D1 | Evaluar al profesional | `cliente1` → «Mis solicitudes» → solicitud finalizada → «Evaluar el servicio» → notas y comentario → Enviar | «Evaluación enviada». En `/admin/` → Ratings: la valoración con autor `cliente1`. El comentario aparece en el perfil público de `profesional1` |
| D2 | Evaluar dos veces | Cierra sesión, entra de nuevo e intenta evaluar el mismo servicio | «Ya habías evaluado este servicio» (el backend lo rechaza) |
| D3 | Calificar al cliente | `profesional1` → «Solicitudes» → Finalizadas → «Calificar al cliente» | «Calificación al cliente registrada». En `/admin/` → Ratings: autor `profesional1` y destinatario `cliente1` |
| D4 | Abrir un reclamo | `cliente1` → solicitud finalizada → «Abrir un reclamo de posventa» → describe el problema | «Reclamo #N enviado». Ya no ofrece reclamar de nuevo ese servicio. Aparece en «🛠️ Mis reclamos» como **Abierto** |
| D5 | El profesional responde | `profesional1` → «🛠️ Reclamos» (con el contador) → responde | Queda **Respondido por el profesional**. `cliente1` ve la respuesta y en `/admin/` → Notifications hay una «Respuesta de posventa» |
| D6 | Mediación y resolución | `cliente1` → «Pedir mediación de Overol». Luego `admin@demo.overol.cl` lo resuelve: en esta etapa, desde `/admin/` o con `POST /api/claims/{id}/resolve/` | Pasa a **En mediación** y, al resolverse, a **Resuelto** con la «Resolución de Overol» |
| D7 | Sin pago de visitas | `cliente1` → «Mis solicitudes» → una solicitud **Aceptada**. Luego abre el perfil público de `profesional1` | No hay ningún botón para pagar la visita. La tarjeta y el perfil (bajo «Tarifa de visita») dicen «La tarifa se paga directamente al profesional; Overol no cobra comisión por los servicios.» |

## Etapa E: notificaciones y tickets de soporte

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| E1 | Aviso de una acción | `profesional1` acepta una solicitud de `cliente1` → `cliente1` mira su barra | «🔔 Notificaciones (1)». En la pantalla: «Solicitud aceptada», marcada como **Nueva**, con el número de la solicitud |
| E2 | Marcar como leída | «Marcar como leída» en una y luego «Marcar todas como leídas» | El contador baja de inmediato. En `/admin/` → Notifications quedan con `is_read` |
| E3 | Abrir un ticket | `cliente1` → «Mis solicitudes» → «💬 Contactar a soporte» → asunto y mensaje → «Abrir ticket» | «Ticket #N abierto». Aparece **Abierto** dentro de la solicitud. En `/admin/` → Support tickets: con la solicitud y el usuario |
| E4 | Respuesta de soporte | Resuelve el ticket con `POST /api/tickets/{id}/resolve/` (o desde el panel del admin cuando esté la etapa G) | `cliente1` ve «Soporte Overol» con la respuesta, el ticket **Resuelto** y una notificación «Ticket resuelto» |
| E5 | Cada uno lo suyo | `profesional1` revisa la misma solicitud | No ve el ticket del cliente. Puede abrir el suyo |

## Etapa F: perfil, reputación, oficios y desarrollo profesional

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| F1 | Vista pública y reputación | `profesional1` (verificado y con suscripción) → «👤 Mi perfil» → «Vista pública y reputación» | Valoración promedio, cantidad de opiniones y su perfil como lo ven los clientes |
| F2 | Sin perfil público | Un profesional pendiente o sin suscripción → la misma pestaña | Explica que aparece al estar verificado y con suscripción vigente |
| F3 | Editar un oficio | «Oficios» → «Editar» → cambia los años y agrega una especialidad → Guardar | En `/admin/` → Professional trades cambian los años, y la especialidad queda en el perfil |
| F4 | Agregar un oficio | «Agregar un oficio» → Electricidad con una especialidad | Aparece en la lista y el profesional sale al filtrar por Electricidad en el catálogo |
| F5 | Desactivar un oficio | «Desactivar oficio» | Queda «⛔ desactivado» y deja de aparecer en ese filtro del catálogo. No se puede reactivar (falta en el backend) |
| F6 | Desarrollo profesional | «🎓 Desarrollo profesional» → abre un contenido → «Marcar como completado» | Contenidos por módulo (Tributario, Seguridad, Gestión), con los 9 de seguridad que trae la migración. Queda ✅ y en `/admin/` → Content progress se registra |

## Etapa G: panel del admin

Entra con `admin@demo.overol.cl` (rol ADMIN y `is_staff`, lo deja así `seed_demo`).

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| G1 | Barra | Entra como admin | Indicadores, Verificación, Usuarios, Reclamos, Soporte y Quiénes somos. **No** aparecen Moderación, Contenidos ni Trazabilidad (no tienen endpoint) |
| G2 | Indicadores | «📊 Indicadores» | Totales de reclamos y tickets, y gráficos por estado, iguales a lo que muestra `/admin/` |
| G3 | Verificación | «🪪 Verificación» → escribe el id del perfil del profesional del caso S7 (en `/admin/` → Professional profiles) → «Ver frente» y «Ver reverso» → «Aprobar» | Muestra o descarga la cédula. Sin los dos lados: «debe cargar ambos lados…». Al aprobar: el perfil pasa a APPROVED y el profesional recibe «Resultado de verificación». Rechazar exige motivo |
| G4 | Estado de una cuenta | «👥 Usuarios» → id de `cliente2` → **Desactivada** con motivo | En `/admin/` → Users: DEACTIVATED. `cliente2` no puede ingresar y recibe la notificación. Vuelve a dejarla Activa |
| G5 | Resolver un reclamo | «🛠️ Reclamos» → el reclamo del caso D4 → escribe la resolución → «Resolver reclamo» | Pasa a **Resuelto**. `cliente1` ve la «Resolución de Overol». En `/admin/` → Admin audit logs: `resolve_claim` |
| G6 | Bandeja de soporte | «💬 Soporte» → «Abiertos» → el ticket del caso E3 → responde | Pasa a **Resuelto** y el cliente recibe «Ticket resuelto». Aparece en el filtro «Resueltos» |

