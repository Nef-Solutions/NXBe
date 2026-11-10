# Propuesta de Proyecto y Especificación de Requisitos de Software
**DUOC UC - Escuela de Informática y Telecomunicaciones**  
**Proyecto:** Overol  
**Revisión:** 02  
**Fecha:** 15/10/2026  
**Documento:** Product Backlog  

---

## 1. Ficha del Documento

| Fecha | Revisión | Autor | Modificación |
| :--- | :--- | :--- | :--- |
| 05/10/2026 | 01 | Ximena Andrea Campos García<br>Benjamín Cristóbal Osses Vergara<br>Nefi Andrés Apablaza Olivares | Primera Revisión |
| 17/10/2026 | 02 | Ximena Andrea Campos García<br>Benjamín Cristóbal Osses Vergara<br>Nefi Andrés Apablaza Olivares | Actualización con el Product Backlog |

**Documento validado por las partes en fecha:** 15/10/2026

---

## 2. Integrantes

| Nombre Integrante del Equipo | Rol Definido |
| :--- | :--- |
| Ximena Campos García | Product Owner |
| Nefi Apablaza Olivares | Desarrollador Back-end |
| Benjamín Osses Vergara | Desarrollador Front-end |

---

## 3. Historias de Usuario

### FASE 1

#### 3.1 Registrar cliente y crear perfil
* **Definición:** Como persona que necesita contratar un servicio quiero registrarme como cliente para acceder a las funcionalidades destinadas a clientes y tener mi perfil de Overol.
* **Criterios de Aceptación:**
  * El sistema debe permitir seleccionar cliente.
  * El sistema solicita nombre, apellido, rut, correo electrónico, teléfono, dirección, comuna y contraseña.
  * El sistema validará los campos obligatorios que estén completos y que el Rut y el correo electrónico tengan un formato válido.
  * El sistema impedirá crear más de una cuenta con el mismo Rut o el mismo correo electrónico, sin exponer datos de las cuentas ya existentes.
  * El sistema creará el perfil de cliente y permitirá iniciar sesión posteriormente con el correo electrónico y contraseña.

#### 3.2 Registrar trabajador y crear perfil
* **Definición:** Como trabajador que ofrece servicios para el hogar quiero registrarme como profesional y crear mi perfil para ofrecer mis servicios dentro de Overol.
* **Criterios de Aceptación:**
  * El sistema permitirá seleccionar profesional / trabajador.
  * El sistema solicita nombre, apellido, rut, correo electrónico, teléfono, número de contacto, comuna donde presta servicios, dirección, comuna y contraseña.
  * El sistema permitirá ingresar 1 o más oficios, descripción del trabajo, años de experiencia por oficio, especialidades y galería de fotos.
  * El sistema impedirá crear más de una cuenta con el mismo Rut o el mismo correo electrónico, sin exponer datos de las cuentas ya existentes.

#### 3.3 Iniciar sesión
* **Definición:** Como Usuario registrado quiero iniciar sesión con mi correo electrónico y contraseña para acceder a las funcionalidades de mi perfil.
* **Criterios de Aceptación:**
  * El sistema permitirá ingresar con el correo electrónico y la contraseña.
  * Ante credenciales incorrectas muestra un mensaje genérico, sin indicar cuál dato falló.
  * Redirige según el tipo de usuario (cliente, profesional o administrador).
  * En caso de 3 intentos fallidos consecutivos, el sistema debe bloquear temporalmente el acceso por 6 horas.
  * Una cuenta dada de baja no puede iniciar sesión.

#### 3.4 Cerrar sesión
* **Definición:** Como usuario con sesión iniciada quiero cerrar sesión para proteger mi cuenta, especialmente en equipos compartidos.
* **Criterios de Aceptación:**
  * El sistema tendrá una opción visible de cerrar sesión.
  * Al cerrar, la sesión se invalida y no se puede volver con el botón atrás.
  * La sesión permite recordar los accesos para permanecer abierta.

#### 3.5 Recuperación de contraseña
* **Definición:** Como usuario que olvidó su contraseña quiero recuperar el acceso a mi cuenta para volver a utilizar la plataforma.
* **Criterios de Aceptación:**
  * El sistema tendrá la opción "Olvidé mi contraseña" en el inicio de sesión.
  * El sistema envía un enlace de recuperación al correo electrónico registrado.
  * El enlace expira tras un tiempo definido y es de un solo uso.
  * El mensaje no revela si el correo ingresado existe o no en el sistema.

#### 3.6 Ver perfil de cliente
* **Definición:** Como cliente quiero ver mi perfil para revisar la información que tengo registrada y el estado de mis solicitudes.
* **Criterios de Aceptación:**
  * El sistema permite ver nombre, apellido, foto de perfil, correo electrónico, teléfono, dirección y comuna.
  * Muestra mis solicitudes con su estado y mi historial de servicios.
  * Muestra mi puntuación como cliente según las valoraciones recibidas, o "Sin historial" si aún no tengo.
  * Solo el usuario puede ver el perfil completo.

#### 3.7 Modificar perfil de cliente
* **Definición:** Como cliente quiero modificar mis datos personales para mantener mi información actualizada.
* **Criterios de Aceptación:**
  * El sistema permite modificar teléfono, dirección, foto de perfil, comuna y contraseña.
  * No se puede modificar nombre ni RUT.
  * Para cambiar la contraseña se solicita la contraseña actual.
  * Los cambios se reflejan inmediatamente.

#### 3.8 Ver Perfil Profesional
* **Definición:** Como profesional quiero ver mi perfil para revisar cómo me ven los clientes y el estado de mi cuenta.
* **Criterios de Aceptación:**
  * Muestra mis datos personales, oficios, experiencia, especialidades, certificaciones, cobertura, disponibilidad y monto de visita.
  * Muestra su puntuación por perfil.

#### 3.9 Modificar perfil Profesional
* **Definición:** Como profesional quiero modificar la información de mi perfil para mantener actualizados mis datos y servicios.
* **Criterios de Aceptación:**
  * Puedo modificar teléfono, correo, comuna, disponibilidad, horario y monto de visita en pesos chilenos.
  * Puedo agregar oficios, que quedan disponibles inmediatamente, y solicitar eliminarlos con una advertencia y confirmación.
  * Al eliminar un oficio, su puntuación, historial y demás datos pasan a estado inactivo sin borrarse; solo el administrador puede recuperarlos.
  * Puedo actualizar experiencia y especialidades por oficio y adjuntar certificaciones (formatos y tamaño máximo definidos), que se muestran como "declaradas" hasta que el administrador las verifique.
  * No puedo modificar directamente nombre ni RUT.
  * Los cambios se aplican inmediatamente.

#### 3.10 Navegar como cliente
* **Definición:** Como cliente quiero navegar por la plataforma para encontrar fácilmente los servicios y profesionales que necesito.
* **Criterios de Aceptación:**
  * Un cliente con sesión iniciada accede desde un menú a su perfil, sus solicitudes, sus notificaciones, el buscador.
  * Un visitante sin sesión puede explorar profesionales, pero no ver datos personales ni de contacto.
  * Si un visitante intenta solicitar una visita o ver datos de contacto, se le invita a iniciar sesión o registrarse y luego vuelve al perfil donde estaba.
  * La interfaz se adapta a celular, Tablet y escritorio.

#### 3.11 Buscar por categoría
* **Definición:** Como cliente quiero navegar por ubicación del problema, zona del hogar y especialidad para llegar rápido al tipo de profesional que necesito.
* **Criterios de Aceptación:**
  * Se podrá elegir progresivamente oficio, especialidad, zona de cobertura y ordenar por mejor evaluado.
  * En cada paso solo se mostrará opciones con profesionales disponibles.
  * Se podrá cambiar los filtros en cualquier momento y los resultados se actualizan.

#### 3.12 Visualizar perfiles de los profesionales
* **Definición:** Como cliente quiero ver los perfiles completos de los profesionales de una categoría.
* **Criterios de Aceptación:**
  * El sistema para cada resultado muestra datos personales, foto, oficios y puntuación.
  * Solo aparecerán profesionales Verificados, con oficio activo y suscripción vigente.
  * El listado está paginado y permite ordenar por puntuación; los profesionales sin valoraciones se ubican después de los valorados.
  * No se muestran datos restringidos.

#### 3.13 Consultar perfil profesional
* **Definición:** Como cliente quiero consultar el perfil completo de un profesional para evaluar si es adecuado para el servicio que necesito.
* **Criterios de Aceptación:**
  * El sistema mostrará oficios, experiencia, especialidades, certificaciones (declaradas o verificadas), cobertura y disponibilidad.
  * El sistema mostrará la puntuación y las opiniones, de la más reciente a la más antigua, o "Sin valoraciones aún".
  * El sistema mostrará la zona de cobertura por comuna.
  * No es visible a visitantes.
  * El RUT y la dirección exacta solo son visibles para el administrador.
  * El cliente accede a los datos de contacto únicamente después de que el profesional acepte su solicitud.

#### 3.14 Seleccionar zona de cobertura
* **Definición:** Como profesional quiero seleccionar las comunas donde trabajo para recibir solo solicitudes que pueda atender.
* **Criterios de Aceptación:**
  * El sistema podrá seleccionar una o varias comunas desde una lista.
  * Los cambios se aplican de inmediato en las búsquedas.
  * El sistema mostrará un resumen de mi cobertura actual.
  * No se exige mi dirección exacta para ofrecer mis servicios.

#### 3.15 Realizar filtro
* **Definición:** Como cliente quiero filtrar los profesionales por zona para ver solo a quienes pueden atenderme.
* **Criterios de Aceptación:**
  * El sistema permite ingresar comunas de trabajo.
  * Puedo buscar por comuna o por radio de 1.000, 5.000 o 10.000 metros.
  * Por comuna, el listado incluye solo profesionales que declaran cubrirla.
  * Por radio, el listado incluye solo profesionales ubicados dentro del radio elegido.
  * La ubicación del profesional se representa como una zona sombreada en el mapa, nunca como una dirección o un punto exacto.
  * Puedo ordenar los resultados por cercanía, sin que se revelen ubicaciones exactas.
  * No se guardan coordenadas exactas sin mi consentimiento.

#### 3.16 Calificar al Profesional
* **Definición:** Como cliente quiero calificar al profesional al finalizar el servicio para reflejar mi experiencia y ayudar a otros usuarios.
* **Criterios de Aceptación:**
  * Solo se habilita cuando el servicio está Finalizado.
  * Califico calidad, puntualidad y trato en una escala de 1 a 5, con un comentario opcional.
  * Solo puedo valorar una vez por servicio y hasta 1 mes después de la aceptación de la solicitud.
  * La valoración se asocia al oficio del servicio y actualiza el promedio de ese oficio, independiente de los demás.
  * El perfil del profesional muestra el promedio, la cantidad de valoraciones y las opiniones por oficio.

#### 3.17 Calificar al cliente
* **Definición:** Como profesional quiero calificar al cliente para dejar constancia de cómo fue la interacción.
* **Criterios de Aceptación:**
  * Solo se habilita cuando el servicio está Finalizado.
  * Los criterios de calificación se definen con el equipo (por ejemplo, trato y cumplimiento de acuerdos), con un comentario opcional.
  * Solo puedo valorar una vez por servicio y hasta 1 mes después de la aceptación de la solicitud.
  * Al recibir una solicitud, veo el promedio y la cantidad de valoraciones del cliente, o "Sin historial".

#### 3.18 Solicitar Visita
* **Definición:** Como cliente registrado quiero solicitar una visita a un profesional para contratar sus servicios.
* **Criterios de Aceptación:**
  * Puedo seleccionar un profesional y el oficio correspondiente.
  * Debo describir el problema y puedo indicar fecha u horario tentativo y la dirección de la visita (la registrada u otra).
  * La solicitud queda registrada con estado Pendiente y el profesional la recibe.
  * No puedo solicitar visitas a profesionales no verificados, con oficio inactivo o con el perfil sin visualización.
  * Puedo ver mis solicitudes con su estado (Pendiente, Aceptada, Rechazada, Finalizada, Cancelada o Vencida) y el motivo si fue rechazada.

#### 3.19 Eliminar visita pendiente
* **Definición:** Como cliente quiero eliminar una solicitud que aún no fue respondida para evitar que el profesional la atienda si ya no la necesito.
* **Criterios de Aceptación:**
  * Solo puedo eliminar solicitudes en estado Pendiente.
  * El sistema pide confirmación.
  * La solicitud queda en estado Cancelada, se considera vencida y deja de estar disponible para el profesional, que es notificado.

#### 3.20 Aceptar solicitud
* **Definición:** Como profesional quiero aceptar una solicitud de visita para atender al cliente.
* **Criterios de Aceptación:**
  * Existe una sección de solicitudes de visitas donde veo cada solicitud con su detalle.
  * Puedo aceptar una solicitud, que pasa a "Solicitudes aceptadas" y deja de estar pendiente.
  * Antes de aceptar, ninguna de las partes ve los datos de contacto de la otra.
  * Al aceptar, se habilitan los datos de contacto del profesional para el cliente (teléfono y WhatsApp) y los del cliente para el profesional, solo para esa solicitud.
  * No puedo aceptar una solicitud ya respondida, cancelada o vencida.

#### 3.21 Rechazar una solicitud
* **Definición:** Como profesional quiero rechazar una solicitud de visita que no puedo atender para que el cliente pueda buscar otra alternativa.
* **Criterios de Aceptación:**
  * Puedo rechazar una solicitud pendiente.
  * Debe escribir un motivo.
  * La solicitud rechazada aparece en "Trabajos rechazados" y el cliente es notificado con el motivo.

#### 3.22 Finalizar servicio
* **Definición:** Como profesional quiero marcar un servicio como finalizado para informar que el trabajo fue realizado.
* **Criterios de Aceptación:**
  * Existe un botón "Finalizar servicio" en los servicios aceptados.
  * El sistema registra la confirmación del profesional.
  * El cliente recibe una solicitud de confirmación.
  * El servicio no se considera finalizado hasta que ambas partes confirmen.

---

### FASE 2

#### 3.23 Aceptación de políticas de privacidad
* **Definición:** Como persona registrada quiero conocer y aceptar las políticas de privacidad y los términos de uso para saber cómo se tratan mis datos personales.
* **Criterios de Aceptación:**
  * El registro exige aceptar explícitamente la política de privacidad y los términos de uso.
  * Los documentos se pueden leer antes de aceptar.
  * Se guarda la fecha y la versión aceptada.
  * El texto considera la normativa chilena de protección de datos personales.

#### 3.24 Buscar por palabra clave
* **Definición:** Como cliente o visitante quiero escribir una palabra clave en una barra de búsqueda para encontrar profesionales más rápido.
* **Criterios de Aceptación:**
  * La barra de búsqueda es visible en la página principal.
  * El sistema busca coincidencias en oficios y especialidades.
  * Si no hay resultados, sugiere categorías relacionadas.

#### 3.25 Solicitar verificación
* **Definición:** Como profesional quiero enviar mi documento de identidad para validar mi identidad y poder ofrecer mis servicios en la plataforma.
* **Criterios de Aceptación:**
  * Permite capturar o cargar una fotografía del documento de identidad.
  * Procesa la información del documento y la compara con los datos registrados.
  * Registra el resultado y muestra el estado: Pendiente de verificación, En revisión, Verificado, Rechazado, Suspendido o Bloqueado.
  * Si no se puede validar automáticamente, deriva la solicitud a revisión manual.
  * Si es rechazada, muestra el motivo y permite corregir los datos y volver a enviar la documentación.
  * La fotografía se almacena cifrada, no es accesible por URL pública y solo el administrador puede verla.
  * Solo los profesionales Verificados aparecen en búsquedas y pueden aceptar solicitudes.

#### 3.26 Enviar mensaje al administrador
* **Definición:** Como profesional en estado Pendiente de verificación, En revisión o Rechazado quiero enviar un mensaje al administrador explicando mi caso para que lo revise y me ayude a resolverlo.
* **Criterios de Aceptación:**
  * La opción de enviar un mensaje está disponible en los estados Pendiente, En revisión y Rechazado.
  * El mensaje permite describir mi situación y el problema.
  * El administrador recibe el mensaje junto con los datos de mi caso.
  * Puedo ver el estado de mi caso y la respuesta del administrador dentro de la plataforma.
  * En esos estados no tengo acceso a otras funciones de trabajador.

#### 3.27 Solucionar Verificación
* **Definición:** Como administrador quiero revisar las solicitudes de verificación y los mensajes de los profesionales para decidir si quedan verificados o resolver su caso.
* **Criterios de Aceptación:**
  * Existe un listado de solicitudes En revisión y de casos con mensaje de profesionales en estado Pendiente, En revisión o Rechazado.
  * Puedo ver los datos ingresados junto a la fotografía del documento.
  * Puedo aprobar o rechazar; al rechazar debo indicar un motivo.
  * Puedo resolver un caso eliminando el perfil e ingresándolo nuevamente como corresponde, tras validar los criterios exigidos.
  * Puedo recuperar los datos asociados al perfil eliminado y asignarlos al nuevo perfil.
  * Cada decisión queda registrada con el administrador, la fecha y el motivo, y el profesional es notificado dentro de la plataforma.

#### 3.28 Permitir ampliar la zona de cobertura
* **Definición:** Como cliente quiero ampliar la zona de búsqueda cuando no hay resultados para encontrar más opciones.
* **Criterios de Aceptación:**
  * Se ofrece ampliar la búsqueda cuando no hay resultados, a comunas cercanas o a un radio mayor.
  * El sistema indica en qué comuna cubre cada profesional mostrado.
  * Puedo volver a la búsqueda original.

#### 3.29 Vencer solicitudes
* **Definición:** Como cliente quiero que las solicitudes sin respuesta venzan tras un plazo para poder generar una nueva.
* **Criterios de Aceptación:**
  * Una solicitud pendiente vence cuando el profesional no acepta ni rechaza, cuando pasa 72 horas desde su envío.
  * En ese caso, el cliente recibe una notificación dentro de la plataforma que le informa el tiempo máximo transcurrido sin que nadie tomara la solicitud, para que genere una nueva.
  * El cliente puede volver a solicitar a otro profesional.

#### 3.30 Confirmar la finalización del servicio
* **Definición:** Como cliente quiero confirmar que el servicio terminó para cerrar formalmente la solicitud.
* **Criterios de Aceptación:**
  * Puedo confirmar la finalización y el sistema registra mi confirmación.
  * Cuando ambas partes confirman, el estado cambia a Finalizado y se habilita la valoración.
  * Si no confirmo tras 5 días, recibo un recordatorio dentro de la plataforma.
  * Pasados otros 7 días hábiles sin confirmación, el servicio queda visible para revisión del administrador.

#### 3.31 Ver centro de desarrollo
* **Definición:** Como profesional quiero acceder a una sección de capacitación para mejorar la formalización y estabilidad de mi actividad.
* **Criterios de Aceptación:**
  * Disponible solo para profesionales con acceso a funciones de trabajador.
  * Los contenidos están organizados por módulos: tributario, seguridad y gestión.
  * Cada módulo lista videos y guías propios y enlaces a entidades oficiales (SII, mutuales de seguridad), indicando claramente cuáles son externos.
  * Puedo marcar los contenidos como vistos y ver mi avance por módulo.

#### 3.32 Solicitar ticket
* **Definición:** Como usuario quiero solicitar un ticket cuando tengo un problema con la plataforma para que el administrador lo revise y me ayude a resolverlo.
* **Criterios de Aceptación:**
  * Puedo crear un ticket indicando el motivo y describiendo el problema, con fotografías opcionales.
  * Puedo hacerlo hasta 3 meses después de la solicitud o del desperfecto de la plataforma que lo origina.
  * El administrador recibe el ticket con los datos de contexto (usuario y solicitud o servicio relacionado).
  * Puedo ver el estado del ticket (Abierto, En revisión o Resuelto) y la respuesta del administrador.
  * Recibo una notificación dentro de la plataforma cuando el ticket cambia de estado.

#### 3.33 Resolución de ticket
* **Definición:** Como administrador quiero revisar y resolver los tickets de los usuarios para solucionar los problemas que tienen con la plataforma.
* **Criterios de Aceptación:**
  * Existe un listado de tickets filtrable por estado y antigüedad.
  * Puedo ver el detalle, los datos de contexto y las fotografías.
  * Puedo responder, cambiar el estado y cerrar el ticket indicando la resolución.
  * La resolución queda registrada en la bitácora y el usuario es notificado.

#### 3.34 Contratar suscripción
* **Definición:** Como profesional verificado quiero suscribirme mensualmente para acceder a las funciones de trabajador.
* **Criterios de Aceptación:**
  * Se informa claramente el monto de la suscripción ($10.000 CLP mensuales) y lo que incluye.
  * La orden de pago se genera automáticamente en el momento en que la identidad del profesional queda verificada.
  * El profesional cuenta con 7 días de prueba gratuita desde su verificación, con acceso a las funciones de trabajador.
  * El pago se realiza mediante una pasarela de pago (en pruebas, entorno sandbox).
  * Recibo la confirmación del pago, y la suscripción queda vigente por un mes con las funciones de trabajador activas.

#### 3.35 Gestionar vencimiento y renovación de suscripción
* **Definición:** Como administrador quiero ver el estado de suscripción de los profesionales y corregir casos excepcionales.
* **Criterios de Aceptación:**
  * Puedo consultar y filtrar por estado de suscripción.
  * Puedo activar o suspender manualmente una suscripción indicando un motivo, con registro en la bitácora.
  * El sistema notifica dentro de la plataforma, 5 días antes del vencimiento (también al término de la prueba), que la suscripción está próxima a vencer y que el perfil quedará sin visualización.
  * La orden de pago de cada renovación mensual se genera 5 días antes del vencimiento, junto con el aviso.
  * Ante un pago fallido, se permite reintentar.
  * Si la suscripción vence, el perfil deja de ser visible para otros usuarios y queda guardado, sin eliminar sus datos, hasta que se genere el pago.
  * Al confirmarse el pago, el perfil vuelve a ser visible.

#### 3.36 Cancelar suscripción
* **Definición:** Como profesional quiero cancelar mi suscripción cuando lo estime pertinente para no ser cobrado en el próximo período.
* **Criterios de Aceptación:**
  * Puedo cancelar mi suscripción en cualquier momento, cuando lo estime pertinente.
  * Se solicita confirmación.
  * Mantengo el acceso hasta el fin del período pagado.
  * Puedo volver a suscribirme.

#### 3.37 Notificar
* **Definición:** Como usuario quiero recibir notificaciones dentro de la plataforma para no perder información importante sobre mis solicitudes, servicios y cuenta.
* **Criterios de Aceptación:**
  * El profesional es notificado de verificación aprobada o rechazada, respuesta del administrador, nuevas solicitudes, solicitudes eliminadas y vencimiento próximo de su suscripción.
  * El cliente es notificado cuando su solicitud es aceptada, rechazada o vencida.
  * Ambas partes son notificadas de la confirmación de finalización pendiente, del cierre forzoso y de los cambios en sus tickets.
  * Existe un acceso visible con el número de notificaciones sin leer; puedo marcarlas como leídas y cada una me lleva al elemento relacionado.
  * Las notificaciones aparecen solo dentro de la plataforma; no se envían por correo electrónico.

#### 3.38 Acceder al panel de administración
* **Definición:** Como administrador quiero ingresar a un panel exclusivo para gestionar los procesos que requieren intervención.
* **Criterios de Aceptación:**
  * Solo los usuarios con rol administrador acceden al panel.
  * El panel muestra accesos a verificaciones, usuarios, solicitudes y servicios, tickets, suscripciones, moderación, contenidos e indicadores.
  * Los intentos de acceso no autorizado se rechazan y se registran.

#### 3.39 Gestionar perfiles de usuarios
* **Definición:** Como administrador quiero gestionar los perfiles de clientes y profesionales para controlar a quienes infrinjan las normas o no puedan validar su identidad.
* **Criterios de Aceptación:**
  * Puedo buscar clientes y profesionales y ver su estado.
  * Puedo consultar la información completa de un profesional (RUT, dirección exacta y documento de verificación); cada consulta queda registrada con administrador, fecha y motivo.
  * Puedo suspender, bloquear o reactivar una cuenta indicando un motivo, y el usuario afectado es notificado.
  * Puedo dar de baja a un usuario completo indicando un motivo; se pierde la información asociada, salvo la que yo recupere.
  * Un profesional suspendido o bloqueado pierde el acceso a las funciones de trabajador; un usuario dado de baja no puede iniciar sesión ni aparece en búsquedas.

#### 3.40 Recuperar datos
* **Definición:** Como administrador quiero recuperar los datos asociados a un perfil dado de baja o eliminado para no perder información cuando un usuario se ingresa nuevamente o hubo un problema.
* **Criterios de Aceptación:**
  * Puedo consultar los datos asociados a un usuario dado de baja o a un perfil eliminado.
  * Puedo seleccionar qué datos recuperar y asignarlos a un nuevo usuario.
  * Solo el administrador puede recuperar valoraciones y puntuaciones inactivas (por ejemplo, las de un oficio eliminado) cuando existan problemas relacionados con trabajadores o usuarios.
  * Debo indicar el motivo; al recuperar valoraciones, los promedios y el historial se recalculan.
  * Las acciones quedan registradas en la bitácora.

#### 3.41 Moderar contenidos y accesos
* **Definición:** Como administrador quiero moderar lo que los usuarios publican o adjuntan para mantener la plataforma confiable y respetuosa.
* **Criterios de Aceptación:**
  * **Reseñas y valoraciones:** reviso las reportadas con su motivo, puedo mantenerlas o eliminarlas indicando un motivo, y los promedios se recalculan; también reviso las solicitudes de modificación o eliminación de una valoración.
  * **Certificaciones:** puedo aprobar o rechazar las que adjuntan los profesionales; las aprobadas se muestran como verificadas en el perfil.
  * **Centro de Desarrollo Profesional:** puedo crear, editar, ocultar y reordenar contenidos y agregar enlaces externos oficiales.
  * **Perfiles:** puedo suspender, bloquear o dar de baja perfiles que infringen las normas.
  * Cada decisión de moderación exige un motivo, queda en la bitácora y se notifica a las partes involucradas.

#### 3.42 Supervisar y cerrar
* **Definición:** Como administrador quiero ver las solicitudes y los servicios en curso para detectar casos que requieran intervención y cerrarlos cuando no se puedan cerrar de forma normal.
* **Criterios de Aceptación:**
  * Listado de solicitudes y servicios filtrable por estado y antigüedad, que destaca los servicios con confirmación pendiente.
  * Puedo abrir un servicio y ejecutar el cierre forzoso indicando un motivo.
  * El sistema registra que el cierre fue realizado por administración.
  * Al cerrarse forzosamente, se elimina la información del cliente asociado al servicio y no se habilita la valoración.
  * En el caso del profesional, puedo dar de baja al usuario completo.

#### 3.43 Ver indicadores de uso de la plataforma
* **Definición:** Como administrador quiero ver indicadores de uso para tomar decisiones sobre la plataforma.
* **Criterios de Aceptación:**
  * Muestra solicitudes por oficio y comuna, tasa de aceptación y promedio de valoraciones.
  * Muestra suscripciones vigentes y vencidas.
  * Muestra el desempeño del chatbot: sugerencias por especialidad y porcentaje de respuestas útiles.
  * Permite filtrar por período.

#### 3.44 Registro de bitácora
* **Definición:** Como administrador quiero que mis acciones queden registradas para poder auditarlas.
* **Criterios de Aceptación:**
  * Se registra quién, qué, cuándo y el motivo de cada acción administrativa.
  * La bitácora no puede modificarse ni eliminarse desde la aplicación.
  * Puedo consultarla y filtrarla por fecha, administrador o tipo de acción.

#### 3.45 Interactuar con un chatbot
* **Definición:** Como cliente que no sabe qué profesional necesita quiero describir mi problema a un asistente para que me recomiende la especialidad adecuada.
* **Criterios de Aceptación:**
  * Dispongo de un chat de texto libre, accesible desde la página principal, que responde en español.
  * El asistente identifica al menos una especialidad relacionada, explica por qué la sugiere y, si hay varias, las presenta ordenadas.
  * Si la descripción es insuficiente, hace preguntas breves, con un máximo antes de dar una sugerencia o una alternativa.
  * Un botón me lleva al listado filtrado por la especialidad sugerida, conservando mi comuna, y puedo volver al chat sin perder la conversación.
  * Si no logra identificar la especialidad, lo reconoce y ofrece navegar por categorías o buscar por palabra clave.
  * Ante situaciones de riesgo (fuga de gas, incendio, riesgo eléctrico), recomienda primero contactar a los servicios de emergencia.
  * No solicita RUT, claves ni datos de pago, y se define cuánto tiempo se conservan las conversaciones.
  * Puedo usarlo sin registrarme, con límites de uso para evitar abusos, e indicar si la sugerencia fue útil.

---

## 4. Backlog

### 4.1 Historias con su peso relativo

| Historia | Peso |
| :--- | :--- |
| **FASE 1** | |
| Registrar cliente y crear perfil | 1 día |
| Registrar trabajador y crear perfil | 2 días |
| Iniciar sesión | 1 día |
| Cerrar sesión | 1 día |
| Recuperación de contraseña | 1 día |
| Ver perfil de cliente | 1 día |
| Modificar perfil de cliente | 1 día |
| Ver perfil profesional | 2 días |
| Modificar perfil profesional | 1 día |
| Navegar como cliente | 1 día |
| Buscar por categoría | 2 días |
| Visualizar perfiles de los profesionales | 1 día |
| Consultar perfil profesional | 1 día |
| Seleccionar zona de cobertura | 2 días |
| Realizar filtro | 1 día |
| Calificar al profesional | 2 días |
| Calificar al cliente | 2 días |
| Solicitar visita | 1 día |
| Eliminar visita pendiente | 1 día |
| Aceptar solicitud | 1 día |
| Rechazar una solicitud | 1 día |
| Finalizar servicio | 1 día |
| **FASE 2** | |
| Aceptación de políticas de privacidad | No aplica |
| Buscar por palabra clave | No aplica |
| Solicitar verificación | No aplica |
| Enviar mensaje al administrador | No aplica |
| Solucionar verificación | No aplica |
| Permitir ampliar la zona de cobertura | No aplica |
| Vencer solicitudes | No aplica |
| Confirmar la finalización del servicio | No aplica |
| Ver centro de desarrollo | No aplica |
| Solicitar ticket | No aplica |
| Resolución de ticket | No aplica |
| Contratar suscripción | No aplica |
| Gestionar vencimiento y renovación de suscripción | No aplica |
| Cancelar suscripción | No aplica |
| Notificar | No aplica |
| Acceder al panel de administración | No aplica |
| Gestionar perfiles de usuarios | No aplica |
| Recuperar datos | No aplica |
| Moderar contenidos y accesos | No aplica |
| Supervisar y cerrar | No aplica |
| Ver indicadores de uso de la plataforma | No aplica |
| Registro de bitácora | No aplica |
| Interactuar con un chatbot | No aplica |

---

### 4.2 Backlog priorizado

| Historia | Sprint |
| :--- | :---: |
| **FASE 1** | |
| Registrar cliente y crear perfil | 1 |
| Registrar trabajador y crear perfil | 1 |
| Iniciar sesión | 1 |
| Cerrar sesión | 1 |
| Recuperación de contraseña | 1 |
| Ver perfil de cliente | 1 |
| Modificar perfil de cliente | 2 |
| Ver perfil profesional | 2 |
| Modificar perfil profesional | 2 |
| Navegar como cliente | 2 |
| Buscar por categoría | 2 |
| Visualizar perfiles de los profesionales | 3 |
| Consultar perfil profesional | 3 |
| Seleccionar zona de cobertura | 3 |
| Realizar filtro | 3 |
| Calificar al profesional | 3 |
| Calificar al cliente | 3 |
| Solicitar visita | 3 |
| Eliminar visita pendiente | 3 |
| Aceptar solicitud | 3 |
| Rechazar una solicitud | 3 |
| Finalizar servicio | 3 |