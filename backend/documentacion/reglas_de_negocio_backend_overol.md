# 🛠️ Registro Definitivo de Reglas de Negocio y Arquitectura Backend REST

**Proyecto:** Overol — Plataforma de Servicios para el Hogar  
**Fecha de actualización:** 01/11/2026  
**Documento:** Especificación Técnica de Backend (Django REST Framework / PostgreSQL + PostGIS)

---

## 1. 🔒 Privacidad y Visibilidad del Catálogo

* **Catálogo y Detalle Público (`GET /api/catalog/professionals/{id}/`):**
  * Retorna datos generales del trabajador: `first_name`, `last_name`, foto de perfil, oficios activos, puntuación general del profesional, comunas de su zona de cobertura y tarifa de visita.

* **Resguardo de Datos Sensibles (RUT y Dirección Exacta):**
  * Los campos `rut` y `address` de los profesionales son **estrictamente de lectura exclusiva para el rol `ADMIN`**.
  * En los payloads retornados para usuarios tipo `CLIENT` o `VISITOR`, la ubicación se expone únicamente como la lista de comunas declaradas dentro de su zona de cobertura.

---

## 2. 📅 Reserva de Visitas y Validación Estricta de Agenda (`POST /api/visits/`)

* **Validación Estricta de Horarios y Días de Atención:**
  * El backend valida obligatoriamente la fecha y hora enviadas por el cliente contra la configuración de disponibilidad del profesional (días hábiles y rangos horarios estipulados en su perfil).
  * Si la fecha u hora ingresada cae fuera de los días u horarios habilitados por el trabajador (por ejemplo, fin de semana o fuera de jornada), el serializer en `POST /api/visits/` **rechaza automáticamente la petición** retornando una respuesta `400 Bad Request` con un mensaje indicando que la solicitud está fuera del horario de atención del profesional.

---

## 3. ⭐ Sistema de Reputación General Único e Inmutable

* **Valoración Centrada en la Persona:**
  * La calificación se asigna directamente al **profesional (persona)** y no a los oficios de forma individual. La puntuación refleja la evaluación general del trabajador sin importar cuántos oficios ofrezca en la plataforma.
  * El campo `rating_avg` en `ProfessionalProfile` se calcula como el promedio global de las valoraciones recibidas por la persona.

* **Tratamiento de Servicios Sin Valoración:**
  * Si un cliente decide no calificar al profesional tras finalizar el servicio, la valoración del trabajador **no se ve influenciada** (ni positiva ni negativamente); la visita simplemente no se contabiliza en el recálculo del promedio.

* **Inmutabilidad de las Reseñas:**
  * Una vez que la valoración es emitida y guardada en la base de datos, **no podrá ser modificada ni editada** por el usuario.

* **Ventana Temporal para Calificar:**
  * Se permite emitir la valoración hasta un plazo máximo de **30 días posteriores a la fecha de finalización** del servicio (`completed_at`). Transcurrido este plazo, la opción de calificar se inhabilita.

---

## 4. ⏱️ Ciclo de Vida y Expiración de Solicitudes

* **Regla Definitiva de Vencimiento:**
  * Una solicitud de visita en estado `PENDING` vence automáticamente al transcurrir **1 mes (30 días)** desde su envío sin recibir respuesta (aceptación o rechazo) por parte del trabajador.

* **Transición de Estado:**
  * Cumplido el mes sin gestión, la solicitud pasa automáticamente al estado `EXPIRED` (Vencida), liberando al cliente para solicitar un servicio a otro profesional y generando las notificaciones internas correspondientes.

---

## 5. 📍 Cobertura por Comunas y Búsqueda Geoespacial por Radio (PostGIS)

* **Zona de Cobertura del Profesional (Selección Múltiple):**
  * Los profesionales seleccionan explícitamente una o varias comunas donde prestan servicios (ej. Maipú, Pudahuel, Quilicura), sin exigirse que sean contiguas.

* **Búsqueda por Radio desde Punto del Cliente (`ST_DWithin`):**
  * Para las búsquedas por proximidad, el backend toma el punto de referencia ingresado por el cliente y aplica filtros de radio geoespacial de **1.000 m, 5.000 m o 10.000 m** mediante la función `ST_DWithin` de PostGIS.
  * Se evalúa la coincidencia entre la zona de cobertura del trabajador y el radio de búsqueda seleccionado por el cliente, **protegiendo en todo momento las direcciones exactas de ambas partes**.

---

## 6. 🛡️ Almacenamiento Seguro de Medios Sensibles (Cédula de Identidad)

* **Aislamiento en Sistema de Archivos:**
  * Las imágenes cargadas para verificación de identidad se almacenan en un directorio privado aislado fuera del directorio de acceso público (`MEDIA_ROOT`).

* **Acceso Controlado por API:**
  * El único canal de acceso a estos archivos es a través del endpoint protegido:
    `GET /api/admin/verifications/{id}/document/`
  * Dicho endpoint requiere autenticación por token JWT y permisos explícitos de rol `IsAdminUser`.

* **Cumplimiento Normativo:**
  * Esta arquitectura cumple con la normativa chilena de protección de datos personales (Ley N° 19.628 / N° 21.719) a costo $0 y sin sobrecargar la infraestructura con cifrado en capa de aplicación.