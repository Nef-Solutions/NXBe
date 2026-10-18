# Evaluación explicada del Definition of Done

**Documento revisado:** `documento_definition_of_done_version_ajustada.md`  
**Fecha de revisión:** 17/10/2026

## 1. Qué significa cada estado

### Parcial

Hay código relacionado y alguna parte funciona, pero todavía falta completar uno o más puntos de la historia. Por ejemplo, puede faltar el frontend, una validación, una prueba, una regla de seguridad o una integración.

### Pendiente

La historia todavía no tiene una implementación funcional verificable.

### Fuera de alcance

La historia no se implementa ahora porque pertenece a una de las áreas que el equipo decidió postergar.

### Fase 2

Una parte marcada como Fase 2 no se evalúa como obligatoria en esta etapa. Si existe código relacionado, se mantiene; no se elimina.

## 2. Resultado general

| Estado | Cantidad | Qué quiere decir |
| :--- | ---: | :--- |
| Parcial | 35 | Existe una base funcional, pero falta completar la historia. |
| Pendiente | 3 | Aún no existe una implementación funcional. |
| Fuera de alcance | 8 | El equipo decidió postergarla. |
| Completa | 0 | Ninguna cumple todos los criterios técnicos y de negocio. |

Hay 38 historias dentro del alcance actual. De ellas, 35 tienen una base implementada y 3 aún deben desarrollarse.

## 3. Evaluación por área

### 3.1 Cuentas y acceso

| ID | Historia | Estado | Explicación |
| :--- | :--- | :---: | :--- |
| 4.1 | Registrar clientes | Parcial | El registro funciona con correo, contraseña, RUT, datos personales y privacidad. Faltan pruebas completas y frontend. |
| 4.2 | Registrar profesionales | Parcial | Se crea un profesional pendiente de verificación. Falta completar oficios, certificaciones y sus validaciones. |
| 4.3 | Aceptar privacidad | Parcial | Se guarda la versión y fecha aceptadas. Falta publicar los textos legales desde la API. |
| 4.4 | Iniciar sesión | Parcial | Funciona con correo y contraseña y hay bloqueo después de tres fallos. Falta la redirección del frontend. |
| 4.5 | Cerrar sesión | Parcial | Existe el cierre mediante Django. Falta la interfaz y la comprobación desde navegador. |
| 4.6 | Recuperar contraseña | Parcial | Existe la solicitud sin revelar si el correo está registrado. Falta configurar el envío real de correos. |
| 4.7 | Ver perfil cliente | Parcial | Se puede consultar el perfil propio. Falta incluir historial, solicitudes, puntuación y foto. |
| 4.8 | Editar perfil cliente | Parcial | Se cambian teléfono, dirección y comuna; los datos sensibles quedan protegidos. Falta la foto y más pruebas. |

### 3.2 Verificación y perfiles profesionales

| ID | Historia | Estado | Explicación |
| :--- | :--- | :---: | :--- |
| 4.9 | Solicitar verificación | Parcial | Existen estados y documentos de identidad. Falta OCR, cifrado específico, reenvío y protección completa de archivos. |
| 4.10 | Mensajear al administrador | Parcial | El profesional puede enviar mensajes. Falta una bandeja administrativa completa y reglas por estado. |
| 4.11 | Resolver verificaciones | Parcial | El administrador puede aprobar o rechazar con motivo, notificar y auditar. Falta recuperar perfiles eliminados. |
| 4.12 | Ver perfil profesional | Parcial | Existe perfil público con oficios, experiencia, tarifa y opiniones. La suscripción es Fase 2; faltan disponibilidad y cobertura. |
| 4.13 | Editar perfil profesional | Parcial | Existe el modelo de oficios con experiencia, certificación declarada y baja lógica. Falta el endpoint de edición y validar archivos. |
| 4.14 | Navegar como cliente | Parcial | Se puede buscar y abrir perfiles sin datos privados. Falta frontend, menú y diseño responsive. El chatbot es Fase 2. |

### 3.3 Catálogo y búsqueda

| ID | Historia | Estado | Explicación |
| :--- | :--- | :---: | :--- |
| 4.15 | Buscar por categoría | Parcial | Se filtra por categoría y zona del hogar. Falta el flujo progresivo por ubicación, comuna y especialidad. |
| 4.16 | Buscar por palabra clave | Parcial | La API busca en nombres, oficios, especialidades y keywords. Falta la barra visual, sugerencias e índices. |
| 4.17 | Listar profesionales | Parcial | Existe listado paginado de profesionales verificados. Faltan ordenamiento completo y disponibilidad. |
| 4.18 | Ver perfil completo | Parcial | Existe detalle público con oficios, experiencia y opiniones sin datos privados. El mapa es Fase 2. |

### 3.4 Fuera del alcance geográfico y de IA

| ID | Historia | Estado | Motivo |
| :--- | :--- | :---: | :--- |
| 4.19 | Seleccionar cobertura | Fuera de alcance | Requiere cobertura geográfica real. |
| 4.20 | Filtrar por cobertura | Fuera de alcance | Requiere ubicación, radios y cálculo geográfico real. |
| 4.21 | Ampliar zona | Fuera de alcance | Requiere comunas cercanas y cobertura geográfica real. |
| 4.22 | Usar chatbot | Fuera de alcance | La integración de diagnóstico con IA fue postergada. |

### 3.5 Solicitudes y ciclo del servicio

| ID | Historia | Estado | Explicación |
| :--- | :--- | :---: | :--- |
| 4.23 | Solicitar visita | Parcial | El cliente puede crear solicitudes para profesionales verificados y especialidades válidas. |
| 4.24 | Cancelar solicitud | Parcial | El cliente puede cancelar solicitudes pendientes y se notifica al profesional. |
| 4.25 | Aceptar solicitud | Parcial | El profesional puede aceptar solicitudes pendientes y se avisa al cliente. Falta liberar contactos de forma controlada. |
| 4.26 | Rechazar solicitud | Parcial | El profesional rechaza indicando un motivo y se notifica al cliente. |
| 4.27 | Vencer solicitudes | Parcial | Un comando marca como vencidas las solicitudes de más de 30 días. Falta programar su ejecución automática. |
| 4.28 | Finalizar servicio | Parcial | El profesional puede indicar que terminó el servicio. Falta completar interfaz y notificaciones. |
| 4.29 | Confirmar servicio | Parcial | El servicio se completa después de ambas confirmaciones. Faltan recordatorios y revisión posterior. |

### 3.6 Calificaciones, capacitación y soporte

| ID | Historia | Estado | Explicación |
| :--- | :--- | :---: | :--- |
| 4.30 | Calificar profesional | Parcial | Se guardan calidad, puntualidad, trato y comentario y se calcula un promedio. Faltan plazo y promedio por oficio. |
| 4.31 | Calificar cliente | Parcial | El profesional puede valorar al cliente después del servicio. Faltan criterios específicos y plazo máximo. |
| 4.32 | Centro profesional | Parcial | Hay contenidos por módulos y registro de avance. Falta un resumen de progreso. |
| 4.33 | Crear ticket | Parcial | El usuario puede crear tickets relacionados con una visita. Faltan fotografías y plazo de tres meses. |
| 4.34 | Resolver ticket | Parcial | El administrador puede responder, cerrar, notificar y auditar. Falta una bandeja con filtros. |

### 3.7 Suscripciones y pagos

| ID | Historia | Estado | Motivo |
| :--- | :--- | :---: | :--- |
| 4.35 | Contratar suscripción | Fuera de alcance | Suscripciones y pasarela de pago fueron excluidas. |
| 4.36 | Renovar suscripción | Fuera de alcance | Suscripciones y pagos fueron excluidos. |
| 4.37 | Cancelar suscripción | Fuera de alcance | Suscripciones y pagos fueron excluidos. |

### 3.8 Notificaciones y administración

| ID | Historia | Estado | Explicación |
| :--- | :--- | :---: | :--- |
| 4.38 | Consultar notificaciones | Parcial | Se pueden consultar y marcar como leídas. Falta contador de no leídas y cubrir todos los eventos. |
| 4.39 | Panel administrativo | Parcial | Existe Django Admin y endpoints protegidos por rol. Falta un panel específico con todos los módulos. |
| 4.40 | Gestionar usuarios | Parcial | Se pueden cambiar estados con motivo, notificar y registrar la acción. Falta baja completa y recuperación. |
| 4.41 | Recuperar datos | Pendiente | No existe papelera, selección ni reasignación de datos eliminados. |
| 4.42 | Moderar contenidos | Parcial | Se gestionan contenidos, certificaciones y estados desde Admin. Faltan reportes y moderación completa de reseñas. |
| 4.43 | Cerrar servicios forzosamente | Pendiente | Existe el estado reservado, pero no el endpoint ni el flujo administrativo. |
| 4.44 | Gestionar suscripciones | Fuera de alcance | Depende del módulo de suscripciones excluido. |
| 4.45 | Ver indicadores | Pendiente | No existe todavía un endpoint ni panel de métricas. |
| 4.46 | Registrar auditoría | Parcial | Existe `AdminAuditLog` y se registran decisiones. Falta consulta filtrable e inmutabilidad de base de datos. |

## 4. Fase 2

Estas partes se mantienen fuera de la implementación actual porque están marcadas como Fase 2:

- Suscripción del profesional en 4.12.
- Chatbot y contenido ampliado de inicio en 4.14.
- Mapa y reglas geográficas avanzadas en 4.18.
- Radios de 100, 500 y 1.000 metros en 4.20.

No se eliminó código existente por estar relacionado con una parte Fase 2.

## 5. Evidencia revisada

Se revisaron los modelos, migraciones, serializers, vistas y URLs de `authentication`, `catalog` y `visits`, además de:

- [Contrato de API](api.md).
- [Diagrama de base de datos](base-de-datos.md).
- [Acta de pruebas](pruebas.md).

Las pruebas registradas incluyen `python manage.py check`, migraciones, 13 pruebas unitarias, compilación Python y el comando de vencimiento.

## 6. Conclusión

El backend tiene una base funcional para cuentas, catálogo, solicitudes, servicios, calificaciones, posventa, soporte, contenidos y administración básica.

Todavía no se puede declarar completamente terminado porque faltan partes funcionales, pruebas API, frontend, controles de seguridad, despliegue y evidencias que pertenecen al DoD técnico.
