# DUOC UC - Escuela de Informática y Telecomunicaciones

## Propuesta de Proyecto y Especificación de Requisitos de Software

### Proyecto: Overol

* **Documento:** Definition of Done
* **Revisión:** 02
* **Fecha:** 05/10/2026

---

## Contenido

* [2. Ficha del documento](#2-ficha-del-documento)
* [3. Integrantes](#3-integrantes)
* [4. Historias de Usuario](#4-historias-de-usuario)
  * [4.1 El sistema debe permitir registrar clientes y crear su perfil](#41-el-sistema-debe-permitir-registrar-clientes-y-crear-su-perfil)
  * [4.2 El sistema debe permitir registrar profesionales y crear su perfil](#42-el-sistema-debe-permitir-registrar-profesionales-y-crear-su-perfil)
  * [4.3 El sistema debe exigir la aceptación de la política de privacidad](#43-el-sistema-debe-exigir-la-aceptación-de-la-política-de-privacidad)
  * [4.4 El sistema debe permitir iniciar sesión](#44-el-sistema-debe-permitir-iniciar-sesión)
  * [4.5 El sistema debe permitir cerrar sesión](#45-el-sistema-debe-permitir-cerrar-sesión)
  * [4.6 El sistema debe permitir recuperar la contraseña](#46-el-sistema-debe-permitir-recuperar-la-contraseña)
  * [4.7 El sistema debe permitir al cliente ver su perfil](#47-el-sistema-debe-permitir-al-cliente-ver-su-perfil)
  * [4.8 El sistema debe permitir al cliente modificar su perfil](#48-el-sistema-debe-permitir-al-cliente-modificar-su-perfil)
  * [4.9 El sistema debe permitir al profesional enviar su solicitud de verificación](#49-el-sistema-debe-permitir-al-profesional-enviar-su-solicitud-de-verificación)
  * [4.10 El sistema debe permitir al profesional enviar un mensaje al administrador sobre su caso](#410-el-sistema-debe-permitir-al-profesional-enviar-un-mensaje-al-administrador-sobre-su-caso)
  * [4.11 El sistema debe permitir al administrador solucionar las solicitudes de verificación](#411-el-sistema-debe-permitir-al-administrador-solucionar-las-solicitudes-de-verificación)
  * [4.12 El sistema debe permitir al profesional ver su perfil](#412-el-sistema-debe-permitir-al-profesional-ver-su-perfil)
  * [4.13 El sistema debe permitir al profesional modificar su perfil](#413-el-sistema-debe-permitir-al-profesional-modificar-su-perfil)
  * [4.14 El sistema debe permitir navegar por la plataforma como cliente](#414-el-sistema-debe-permitir-navegar-por-la-plataforma-como-cliente)
  * [4.15 El sistema debe permitir buscar profesionales por categoría](#415-el-sistema-debe-permitir-buscar-profesionales-por-categoría)
  * [4.16 El sistema debe permitir buscar profesionales por palabra clave](#416-el-sistema-debe-permitir-buscar-profesionales-por-palabra-clave)
  * [4.17 El sistema debe permitir visualizar los perfiles de los profesionales por categoría](#417-el-sistema-debe-permitir-visualizar-los-perfiles-de-los-profesionales-por-categoría)
  * [4.18 El sistema debe permitir consultar el perfil completo del profesional](#418-el-sistema-debe-permitir-consultar-el-perfil-completo-del-profesional)
  * [4.19 El sistema debe permitir al profesional seleccionar su zona de cobertura](#419-el-sistema-debe-permitir-al-profesional-seleccionar-su-zona-de-cobertura)
  * [4.20 El sistema debe permitir visualizar profesionales con filtro de zona de cobertura](#420-el-sistema-debe-permitir-visualizar-profesionales-con-filtro-de-zona-de-cobertura)
  * [4.21 El sistema debe permitir ampliar la zona de cobertura de la búsqueda](#421-el-sistema-debe-permitir-ampliar-la-zona-de-cobertura-de-la-búsqueda)
  * [4.22 El sistema debe permitir interactuar con un chatbot para identificar la necesidad](#422-el-sistema-debe-permitir-interactuar-con-un-chatbot-para-identificar-la-necesidad)
  * [4.23 El sistema debe permitir solicitar una visita](#423-el-sistema-debe-permitir-solicitar-una-visita)
  * [4.24 El sistema debe permitir eliminar una visita solicitada](#424-el-sistema-debe-permitir-eliminar-una-visita-solicitada)
  * [4.25 El sistema debe permitir al profesional aceptar una solicitud](#425-el-sistema-de-permitir-al-profesional-aceptar-una-solicitud)
  * [4.26 El sistema debe permitir al profesional rechazar una solicitud](#426-el-sistema-debe-permitir-al-profesional-rechazar-una-solicitud)
  * [4.27 El sistema debe vencer las solicitudes sin respuesta](#427-el-sistema-debe-vencer-las-solicitudes-sin-respuesta)
  * [4.28 El sistema debe permitir al profesional finalizar un servicio](#428-el-sistema-debe-permitir-al-profesional-finalizar-un-servicio)
  * [4.29 El sistema debe permitir al cliente confirmar la finalización del servicio](#429-el-sistema-debe-permitir-al-cliente-confirmar-la-finalización-del-servicio)
  * [4.30 El sistema debe permitir al cliente calificar al profesional](#430-el-sistema-debe-permitir-al-cliente-calificar-al-profesional)
  * [4.31 El sistema debe permitir al profesional calificar al cliente](#431-el-sistema-debe-permitir-al-profesional-calificar-al-cliente)
  * [4.32 El sistema debe permitir visualizar el Centro de Desarrollo Profesional](#432-el-sistema-debe-permitir-visualizar-el-centro-de-desarrollo-profesional)
  * [4.33 El sistema debe permitir solicitar un ticket por problemas en la plataforma](#433-el-sistema-debe-permitir-solicitar-un-ticket-por-problemas-en-la-plataforma)
  * [4.34 El sistema debe permitir al administrador resolver los tickets de los usuarios](#434-el-sistema-debe-permitir-al-administrador-resolver-los-tickets-de-los-usuarios)
  * [4.35 El sistema debe permitir al profesional contratar la suscripción mensual](#435-el-sistema-debe-permitir-al-profesional-contratar-la-suscripción-mensual)
  * [4.36 El sistema debe gestionar el vencimiento y la renovación de la suscripción](#436-el-sistema-debe-gestionar-el-vencimiento-y-la-renovación-de-la-suscripción)
  * [4.37 El sistema debe permitir al profesional cancelar su suscripción](#437-el-sistema-debe-permitir-al-profesional-cancelar-su-suscripción)
  * [4.38 El sistema debe permitir recibir y consultar notificaciones dentro de la plataforma](#438-el-sistema-debe-permitir-recibir-y-consultar-notificaciones-dentro-de-la-plataforma)
  * [4.39 El sistema debe permitir al administrador acceder a un panel de administración](#439-el-sistema-debe-permitir-al-administrador-acceder-a-un-panel-de-administración)
  * [4.40 El sistema debe permitir al administrador gestionar los perfiles de usuario](#440-el-sistema-debe-permitir-al-administrador-gestionar-los-perfiles-de-usuario)
  * [4.41 El sistema debe permitir al administrador recuperar datos de los perfiles](#441-el-sistema-debe-permitir-al-administrador-recuperar-datos-de-los-perfiles)
  * [4.42 El sistema debe permitir al administrador moderar los contenidos y accesos de la plataforma](#442-el-sistema-debe-permitir-al-administrador-moderar-los-contenidos-y-accesos-de-la-plataforma)
  * [4.43 El sistema debe permitir al administrador supervisar solicitudes y servicios y cerrarlos forzosamente](#443-el-sistema-debe-permitir-al-administrador-supervisar-solicitudes-y-servicios-y-cerrarlos-forzosamente)
  * [4.44 El sistema debe permitir al administrador gestionar las suscripciones de los profesionales](#444-el-sistema-debe-permitir-al-administrador-gestionar-las-suscripciones-de-los-profesionales)
  * [4.45 El sistema debe permitir al administrador ver indicadores de uso de la plataforma](#445-el-sistema-debe-permitir-al-administrador-ver-indicadores-de-uso-de-la-plataforma)
  * [4.46 El sistema debe registrar las acciones administrativas en una bitácora](#446-el-sistema-debe-registrar-las-acciones-administrativas-en-una-bitácora)

---

## 2. Ficha del documento

| Fecha | Revisión | Autor | Modificación |
| :--- | :--- | :--- | :--- |
| 05/10/2026 | 01 | Ximena Andrea Campos García, Benjamín Cristóbal Osses Venegas, Nefi Andrés Apablaza Olivares | Primera Revisión |
| 17/10/2026 | 02 | Ximena Andrea Campos García, Benjamín Cristóbal Osses Venegas, Nefi Andrés Apablaza Olivares | Actualización con el Product Backlog rehecho |

**Documento validado por las partes en fecha:** ____________________

---

## 3. Integrantes

| Nombre Integrante del Equipo | Rol Definido |
| :--- | :--- |
| Ximena Campos García | Product Owner |
| Nefi Apablaza Olivares | Desarrollador Back-end |
| Benjamín Osses Vergara | Desarrollador Front-end |

---

## 4. Historias de Usuario

### 4.1 El sistema debe permitir registrar clientes y crear su perfil

#### Definición
Como persona que necesita contratar un servicio quiero registrarme como cliente para acceder a las funcionalidades destinadas a clientes y tener mi perfil en Overol.

#### DoD de Negocio
* El sistema debe permitir seleccionar el tipo de cuenta Usuario/Cliente al registrarse.
* El sistema debe solicitar nombre, apellido, RUT, correo electrónico, teléfono, dirección, comuna y contraseña.
* El sistema debe validar que los campos obligatorios estén completos y que el RUT y el correo electrónico tengan un formato válido.
* El sistema no debe permitir más de una cuenta con el mismo RUT o el mismo correo electrónico, ni exponer datos de la cuenta existente.
* El sistema debe crear el perfil de cliente y permitir iniciar sesión con el correo electrónico.
* En caso de datos inválidos o incompletos, el sistema debe indicar qué campo debe corregirse.

#### DoD Técnico
* El modelo de datos de usuarios y clientes, incluido el correo electrónico, se encuentra documentado en código.
* Las restricciones de unicidad de RUT y correo se encuentran implementadas en la base de datos.
* Las contraseñas se almacenan en la base de datos y las validaciones se ejecutan también en el servidor.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.

---

### 4.2 El sistema debe permitir registrar profesionales y crear su perfil

#### Definición
Como trabajador que ofrece servicios para el hogar quiero registrarme como profesional y crear mi perfil para ofrecer mis servicios dentro de Overol.

#### DoD de Negocio
* El sistema debe permitir seleccionar el tipo de cuenta Profesional/Trabajador al registrarse.
* El sistema debe solicitar nombre, apellido, RUT, correo electrónico, teléfono, número de contacto, dirección, comunas presta servicio, comuna personal y contraseña.
* El sistema debe permitir ingresar uno o más oficios con años de experiencia, certificaciones en PDF, JPG o PNG, especialidades y una descripción opcional.
* El sistema no debe permitir más de un perfil con el mismo RUT o el mismo correo electrónico.
* En caso de datos incompletos, el sistema no debe crear el perfil e indicará los campos faltantes (Fase 2).
* El sistema debe crear el perfil en estado Pendiente de verificación y solicitar la documentación de identidad.

#### DoD Técnico
* El modelo de datos de profesionales y oficios se encuentra documentado en video.
* El catálogo de oficios y especialidades se encuentra creado para muestra, luego se ingresarán oficios faltantes.
* El endpoint de registro y sus parámetros se encuentran documentados.
* El código se encuentra subido al GitHub.
* La base de datos debe soportar distintos tipos de archivos.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y documentadas en video.

---

### 4.3 El sistema debe exigir la aceptación de la política de privacidad

#### Definición
Como persona que se registra quiero conocer y aceptar la política de privacidad y los términos de uso para saber cómo se tratarán mis datos personales.

#### DoD de Negocio
* El sistema debe exigir la aceptación explícita de la política de privacidad y los términos de uso para completar el registro.
* El sistema debe permitir leer ambos documentos antes de aceptar.
* El sistema debe guardar la fecha y la versión aceptada.
* El sistema no debe permitir completar el registro sin la aceptación.

#### DoD Técnico
* El modelo de datos del registro de aceptaciones se debe documentar.
* Los textos legales se deben revisar por el equipo con la normativa chilena de protección de datos personales.
* El código se subirá al GitHub.
* Las pruebas funcionales de la historia se ejecutarán y documentarán en video.

---

### 4.4 El sistema debe permitir iniciar sesión

#### Definición
Como usuario registrado quiero iniciar sesión con mi correo electrónico y contraseña para acceder a las funcionalidades de mi perfil.

#### DoD de Negocio
* El sistema debe permitir ingresar con el correo electrónico y la contraseña.
* El sistema debe redirigir al usuario según su tipo (cliente, profesional o administrador).
* El sistema no debe indicar cuál dato falló cuando las credenciales son incorrectas.
* El sistema no debe permitir el acceso a una cuenta dada de baja.
* En caso de 3 intentos fallidos consecutivos, el sistema debe bloquear temporalmente el acceso por 6 horas.

#### DoD Técnico
* El mecanismo de autenticación y el manejo de sesión se encuentran documentados en video.
* Las rutas públicas y privadas, con su control de acceso por rol, se encuentran definidas y verificadas.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validadas.

---

### 4.5 El sistema debe permitir cerrar sesión

#### Definición
Como usuario con sesión iniciada quiero cerrar sesión para proteger mi cuenta, especialmente en equipos compartidos.

#### DoD de Negocio
* El sistema debe mostrar una opción visible para cerrar sesión.
* El sistema debe invalidar la sesión al cerrarla, sin permitir volver con el botón atrás.
* El sistema permite recordar los accesos para permanecer abierta.

#### DoD Técnico
* Las pruebas de acceso a rutas privadas después de cerrar sesión se encuentran ejecutadas y documentadas en video.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada.

---

### 4.6 El sistema debe permitir recuperar la contraseña

#### Definición
Como usuario que olvidó su contraseña quiero recuperar el acceso a mi cuenta para volver a utilizar la plataforma.

#### DoD de Negocio
* El sistema debe mostrar la opción "Olvidé mi contraseña" en el inicio de sesión.
* El sistema debe hacer que el enlace expire y sea de un solo uso.
* El sistema no debe revelar si el correo ingresado existe en el sistema.
* El sistema debe enviar un enlace de recuperación al correo electrónico registrado.

#### DoD Técnico
* El servicio de envío de correos se encuentra configurado y documentado en video.
* El modelo de datos de los enlaces de recuperación se encuentra documentado.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada.

---

### 4.7 El sistema debe permitir al cliente ver su perfil

#### Definición
Como cliente quiero ver mi perfil para revisar la información que tengo registrada y el estado de mis solicitudes.

#### DoD de Negocio
* El sistema debe mostrar nombre, apellido, foto de perfil, correo electrónico, teléfono, dirección y comuna.
* El sistema debe mostrar las solicitudes del cliente con su estado y su historial de servicios.
* El sistema debe mostrar la puntuación del cliente según las valoraciones recibidas, o "Sin historial" si aún no tiene.
* El sistema no debe permitir que otro usuario vea el perfil completo del cliente.

#### DoD Técnico
* El endpoint del perfil del cliente se encuentra documentado y restringido al propio usuario.
* La vista es responsiva (escritorio y móvil).
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada.

---

### 4.8 El sistema debe permitir al cliente modificar su perfil

#### Definición
Como cliente quiero modificar mis datos personales para mantener mi información actualizada.

#### DoD de Negocio
* El sistema debe permitir modificar teléfono, dirección, foto de perfil, comuna y contraseña.
* El sistema no debe permitir modificar nombre ni RUT.
* El sistema debe solicitar la contraseña actual para cambiar la contraseña.
* El sistema debe reflejar los cambios inmediatamente.

#### DoD Técnico
* El endpoint de actualización de datos se encuentra documentado.
* Se encuentra verificado en el servidor que los campos de solo lectura no pueden ser alterados.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validadas.

---

### 4.9 El sistema debe permitir al profesional enviar su solicitud de verificación

#### Definición
Como profesional quiero enviar mi documento de identidad para validar mi identidad y poder ofrecer mis servicios en la plataforma.

#### DoD de Negocio
* El sistema debe permitir capturar o cargar una fotografía del documento de identidad.
* El sistema debe procesar la información del documento y compararla con los datos registrados.
* El sistema debe registrar el resultado y mostrar el estado de la verificación al profesional.
* En caso de que no se pueda validar automáticamente, el sistema debe derivar la solicitud a revisión manual.
* En caso de rechazo, el sistema debe mostrar el motivo y permitir corregir los datos y volver a enviar la documentación.
* El sistema debe almacenar la fotografía de forma cifrada, sin acceso por URL pública y solo visible para el administrador.
* El sistema debe mostrar en búsquedas y permitir aceptar solicitudes solo a profesionales Verificados.

#### DoD Técnico
* La integración con el servicio de lectura del documento se debe documentar.
* El diagrama de estados de la verificación y el diagrama de secuencia del flujo se encuentran documentados.
* El almacenamiento cifrado y las pruebas de acceso no autorizado a la imagen se encuentran documentados.
* Las pruebas con documentos legibles, ilegibles y con datos no coincidentes se deben ejecutar y documentar.
* El código se subirá al GitHub.
* Las pruebas funcionales de la historia se deben ejecutar y documentar.

---

### 4.10 El sistema debe permitir al profesional enviar un mensaje al administrador sobre su caso

#### Definición
Como profesional en estado Pendiente de verificación, En revisión o Rechazado quiero enviar un mensaje al administrador explicando mi caso para que lo revise y me ayude a resolverlo.

#### DoD de Negocio
* El sistema debe habilitar el envío de mensajes en los estados Pendiente, En revisión y Rechazado.
* El sistema debe permitir describir la situación y el problema con la verificación.
* El sistema debe entregar el mensaje al administrador junto con los datos del caso.
* El sistema debe permitir al profesional ver el estado de su caso y la respuesta del administrador dentro de la plataforma.
* El sistema no debe permitir a esos profesionales acceder a otras funciones de trabajador.

#### DoD Técnico
* El modelo de datos de los mensajes de casos se debe documentar.
* La matriz de permisos por estado de verificación se definirá y verificará con pruebas en el servidor.
* El código se debe subir al GitHub.
* Las pruebas funcionales de la historia se deben ejecutar y documentar.

---

### 4.11 El sistema debe permitir al administrador solucionar las solicitudes de verificación

#### Definición
Como administrador quiero revisar las solicitudes de verificación y los mensajes de los profesionales para decidir si quedan verificados o resolver su caso.

#### DoD de Negocio
* El sistema debe mostrar un listado de solicitudes En revisión y de casos con mensaje de profesionales no verificados.
* El sistema debe permitir ver los datos ingresados junto a la fotografía del documento.
* El sistema debe permitir aprobar o rechazar, exigiendo un motivo al rechazar.
* El sistema debe permitir resolver un caso eliminando el perfil e ingresándolo nuevamente como corresponde, tras validar los criterios exigidos.
* El sistema debe permitir recuperar los datos asociados al perfil eliminado y asignarlos al nuevo perfil.
* El sistema debe registrar cada decisión con el administrador, la fecha y el motivo, y notificar al profesional dentro de la plataforma.
* El sistema no debe permitir el acceso a esta función a usuarios sin rol de administrador.

#### DoD Técnico
* Los criterios exigidos para el ingreso del profesional se encuentran definidos y documentados.
* El endpoint se encuentra restringido por rol y probado con usuarios sin rol de administrador.
* El registro de las decisiones en la bitácora se encuentra implementado y documentado.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.12 El sistema debe permitir al profesional ver su perfil

#### Definición
Como profesional quiero ver mi perfil para revisar cómo me ven los clientes y el estado de mi cuenta.

#### DoD de Negocio
* El sistema debe mostrar los datos personales, comunas de trabajo, número de contacto, oficios, experiencia, especialidades, certificaciones, cobertura, disponibilidad y monto de visita.
* El sistema debe mostrar la puntuación por oficio y las opiniones, o "Sin valoraciones aún".
* El sistema debe permitir reportar una reseña indebida indicando un motivo.
* **Fase 2:** El sistema debe mostrar el estado de la verificación y de la suscripción del profesional.

#### DoD Técnico
* El endpoint del perfil profesional se encuentra documentado.
* La vista es responsiva (escritorio y móvil).
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada.

---

### 4.13 El sistema debe permitir al profesional modificar su perfil

#### Definición
Como profesional quiero modificar la información de mi perfil para mantener actualizados mis datos y servicios.

#### DoD de Negocio
* El sistema debe permitir modificar teléfono, teléfono de contacto, correo, comuna, comuna de trabajo, disponibilidad, horario y monto de visita en pesos chilenos.
* El sistema debe permitir agregar oficios, que quedan disponibles inmediatamente.
* El sistema debe mostrar una advertencia y pedir confirmación antes de eliminar un oficio.
* El sistema debe dejar inactivos, sin borrarlos, la puntuación, el historial y los datos de un oficio eliminado; solo el administrador puede recuperarlos.
* El sistema debe permitir actualizar experiencia y especialidades por oficio y adjuntar certificaciones.
* El sistema debe soportar documentos en PDF, JPG y PNG.
* El sistema no debe permitir modificar directamente nombre ni RUT.
* En caso de archivo de certificación con formato o tamaño no permitido, el sistema debe rechazarlo con un mensaje claro.

#### DoD Técnico
* El borrado lógico de oficios se encuentra implementado y documentado.
* La validación de tipo y tamaño de archivo se encuentra implementada en el servidor.
* El endpoint de actualización del perfil y las pruebas de campos editables y no editables se encuentran documentados.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validadas.

---

### 4.14 El sistema debe permitir navegar por la plataforma como cliente

#### Definición
Como cliente quiero navegar por la plataforma para encontrar fácilmente los servicios y profesionales que necesito.

#### DoD de Negocio
* El sistema debe ofrecer al cliente con sesión un menú con su perfil, solicitudes, notificaciones, buscador.
* El sistema debe permitir a un visitante explorar profesionales, sin mostrarle datos personales ni de contacto.
* El sistema debe invitar al visitante a iniciar sesión o registrarse al intentar solicitar una visita o ver datos de contacto, y devolverlo después al perfil donde estaba.
* El sistema debe adaptar la interfaz a celular, tablet y escritorio.
* **Fase 2:**
  * El sistema debe explicar en la página de inicio qué es Overol y cómo funciona, y mostrar los oficios disponibles.
  * El sistema debe ofrecer al cliente con sesión un menú con su perfil, solicitudes, notificaciones, buscador y chatbot.

#### DoD Técnico
* Las rutas públicas y privadas se encuentran definidas, documentadas y con el control de acceso verificado.
* Los navegadores y resoluciones soportados se encuentran definidos por el equipo y probados.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validadas.

---

### 4.15 El sistema debe permitir buscar profesionales por categoría

#### Definición
Como cliente quiero navegar por ubicación del problema, comuna y especialidad para llegar rápido al tipo de profesional que necesito.

#### DoD de Negocio
* El sistema debe permitir elegir progresivamente ubicación del problema, comuna y especialidad.
* El sistema debe mostrar en cada paso solo las opciones que tienen profesionales disponibles.
* El sistema debe permitir cambiar los filtros en cualquier momento y actualizar los resultados.

#### DoD Técnico
* El modelo de datos de categorías y su relación con los oficios se encuentra documentado en video.
* Las pruebas con distintas combinaciones de filtros se encuentran ejecutadas y documentadas en video.
* El código se encuentra subido al GitHub.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validadas.

---

### 4.16 El sistema debe permitir buscar profesionales por palabra clave

#### Definición
Como cliente o visitante quiero escribir una palabra clave en una barra de búsqueda para encontrar profesionales más rápido.

#### DoD de Negocio
* El sistema debe mostrar una barra de búsqueda visible en la página principal.
* El sistema debe buscar coincidencias en oficios y especialidades.
* En caso de no haber resultados, el sistema debe sugerir categorías relacionadas.

#### DoD Técnico
* El endpoint de búsqueda y sus parámetros se encuentran documentados.
* Las consultas cuentan con índices o una optimización definida y tiempos de respuesta aceptables.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.17 El sistema debe permitir visualizar los perfiles de los profesionales por categoría

#### Definición
Como cliente quiero ver los perfiles completos de los profesionales de una categoría.

#### DoD de Negocio
* El sistema debe mostrar por cada resultado: datos personales, foto, oficios y puntuación.
* El sistema debe mostrar únicamente profesionales Verificados, con oficio activo y suscripción vigente.
* El sistema no debe mostrar datos restringidos en los resultados.

#### DoD Técnico
* El endpoint del listado se encuentra documentado y verificado para no exponer campos restringidos.
* Las pruebas del listado con y sin resultados se encuentran ejecutadas y documentadas en video.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada.

---

### 4.18 El sistema debe permitir consultar el perfil completo del profesional

#### Definición
Como cliente quiero consultar el perfil completo de un profesional para evaluar si es adecuado para el servicio que necesito.

#### DoD de Negocio
* El sistema debe mostrar datos personales, foto, oficios, experiencia, especialidades, certificaciones (declaradas o verificadas), cobertura y disponibilidad.
* El sistema debe mostrar la puntuación y las opiniones por oficio, de la más reciente a la más antigua, o "Sin valoraciones aún".
* El sistema no debe mostrar perfiles completos a los visitantes.
* El sistema debe habilitar los datos de contacto al cliente únicamente después de que el profesional acepte su solicitud.
* **Fase 2:**
  * El sistema debe mostrar la zona de cobertura en un mapa, sin la dirección exacta.
  * El sistema debe hacer visibles el RUT y la dirección exacta solo para el administrador.

#### DoD Técnico
* Las pruebas que verifican que las respuestas públicas no incluyen datos restringidos se encuentran ejecutadas y documentadas en video.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validadas.
* **Fase 2:** El servicio de mapas se encontrará configurado y documentado por video.

---

### 4.19 El sistema debe permitir al profesional seleccionar su zona de cobertura

#### Definición
Como profesional quiero seleccionar las comunas donde trabajo para recibir solo solicitudes que pueda atender.

#### DoD de Negocio
* El sistema debe permitir seleccionar una o varias comunas desde una lista.
* El sistema debe aplicar los cambios de cobertura de inmediato en las búsquedas.
* El sistema debe mostrar un resumen de la cobertura actual.
* El sistema no debe exigir la dirección exacta del profesional para ofrecer sus servicios.

#### DoD Técnico
* El catálogo de comunas y el modelo de cobertura se encuentran documentados.
* La integración con el servicio de mapas se encuentra documentada.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.20 El sistema debe permitir visualizar profesionales con filtro de zona de cobertura

#### Definición
Como cliente quiero filtrar los profesionales por zona para ver solo a quienes pueden atenderme.

#### DoD de Negocio
* El sistema debe solicitar permiso explícito para usar la ubicación del cliente y permitir elegir la comuna manualmente si lo rechaza.
* El sistema debe permitir buscar por comuna o por radio de 100, 500 o 1.000 metros.
* El sistema debe mostrar, por comuna, solo los profesionales que declaran cubrirla, y por radio, solo los ubicados dentro del radio elegido.
* El sistema debe representar la ubicación del profesional como una zona sombreada, sin mostrar dirección ni punto exacto.
* El sistema debe permitir ordenar los resultados por cercanía sin revelar ubicaciones exactas.
* El sistema no debe guardar coordenadas exactas.

#### DoD Técnico
* La técnica de cálculo de cercanía por zona se encuentra definida y documentada en el código.
* Las respuestas de búsqueda no incluyen coordenadas ni distancias exactas, y esto se encuentra verificado con pruebas en el código.
* Las pruebas con comuna se encuentran ejecutadas y documentadas en video.
* El código se encuentra subido al GitHub.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada.
* **Fase 2:** Las pruebas con comuna y con los tres radios se encuentran ejecutadas y documentadas.

---

### 4.21 El sistema debe permitir ampliar la zona de cobertura de la búsqueda

#### Definición
Como cliente quiero ampliar la zona de búsqueda cuando no hay resultados para encontrar más opciones.

#### DoD de Negocio
* El sistema debe ofrecer ampliar la búsqueda a comunas cercanas o a un radio mayor cuando no hay resultados.
* El sistema debe indicar en qué comuna cubre cada profesional mostrado.
* El sistema debe permitir volver a la búsqueda original.

#### DoD Técnico
* La definición de comunas cercanas se encuentra documentada en video.
* El código se encuentra subido al GitHub.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas en video.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada.
* Las pruebas de ampliación de búsqueda sin resultados se encuentran ejecutadas y documentadas en video.

---

### 4.22 El sistema debe permitir interactuar con un chatbot para identificar la necesidad

#### Definición
Como cliente que no sabe qué profesional necesita quiero describir mi problema a un asistente para que me recomiende la especialidad adecuada.

#### DoD de Negocio
* El sistema debe ofrecer un chat de texto libre, accesible desde la página principal, que responda en español.
* El sistema debe identificar al menos una especialidad relacionada, explicar por qué la sugiere y ordenarlas si hay varias.
* El sistema debe hacer preguntas breves si la descripción es insuficiente, con un máximo antes de dar una sugerencia o alternativa.
* El sistema debe ofrecer un botón al listado filtrado por la especialidad sugerida, conservando la comuna, y permitir volver al chat sin perder la conversación.
* En caso de que no logre identificar la especialidad, el sistema debe reconocerlo y ofrecer navegar por categorías o buscar por palabra clave.
* Ante situaciones de riesgo (fuga de gas, incendio, riesgo eléctrico), el sistema debe recomendar primero contactar a los servicios de emergencia.
* El sistema no debe solicitar RUT, claves ni datos de pago.
* El sistema debe permitir su uso sin registrarse, con límites de uso, y permitir indicar si la sugerencia fue útil.

#### DoD Técnico
* La integración con el modelo de IA se debe documentar y guardar en el repositorio.
* El diseño de las instrucciones (prompts) y la lista de situaciones de riesgo se deben documentar.
* Las pruebas con descripciones claras, ambiguas, fuera de alcance y de emergencia se deben ejecutar y documentar.
* La política de conservación de las conversaciones se documenta.
* El código se subirá al GitHub.
* Las pruebas funcionales de la historia se ejecutarán y documentarán.

---

### 4.23 El sistema debe permitir solicitar una visita

#### Definición
Como cliente registrado quiero solicitar una visita a un profesional para contratar sus servicios.

#### DoD de Negocio
* El sistema debe permitir al cliente seleccionar un profesional y el oficio correspondiente.
* El sistema debe exigir la descripción del problema y permitir indicar fecha u horario tentativo y la dirección de la visita.
* El sistema debe registrar la solicitud con estado Pendiente y hacerla llegar al profesional.
* El sistema no debe permitir solicitar visitas a profesionales no verificados, con oficio inactivo o con el perfil sin visualización.
* El sistema debe permitir al cliente ver sus solicitudes con su estado y el motivo si fue rechazada.

#### DoD Técnico
* El modelo de datos de solicitudes y el diagrama de estados se encuentran documentados.
* El endpoint de creación de solicitudes y sus validaciones en el servidor se encuentran documentados.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.24 El sistema debe permitir eliminar una visita solicitada

#### Definición
Como cliente quiero eliminar una solicitud que aún no fue respondida para evitar que el profesional la atienda si ya no la necesito.

#### DoD de Negocio
* El sistema debe permitir eliminar solo solicitudes en estado Pendiente.
* El sistema debe pedir confirmación antes de eliminar.
* El sistema debe dejar la solicitud en estado Cancelada, considerarla vencida y dejar de ofrecerla al profesional.
* El sistema debe notificar al profesional.

#### DoD Técnico
* Las pruebas de eliminación en estados no permitidos se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.25 El sistema debe permitir al profesional aceptar una solicitud

#### Definición
Como profesional quiero aceptar una solicitud de visita para atender al cliente.

#### DoD de Negocio
* El sistema debe mostrar al profesional una sección de solicitudes de visitas con el detalle de cada una.
* El sistema debe permitir aceptar una solicitud, que pasa a "Solicitudes aceptadas" y deja de estar pendiente.
* El sistema no debe mostrar los datos de contacto de ninguna de las partes antes de la aceptación.
* El sistema debe habilitar, al aceptar, los datos de contacto del profesional (teléfono y WhatsApp) para el cliente y los del cliente para el profesional, solo para esa solicitud.
* El sistema no debe permitir aceptar una solicitud ya respondida, cancelada o vencida.

#### DoD Técnico
* Las pruebas de transiciones de estado válidas e inválidas se encuentran ejecutadas y documentadas.
* Las pruebas que verifican que el contacto no se entrega antes de la aceptación se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.26 El sistema debe permitir al profesional rechazar una solicitud

#### Definición
Como profesional quiero rechazar una solicitud de visita que no puedo atender para que el cliente pueda buscar otra alternativa.

#### DoD de Negocio
* El sistema debe permitir rechazar una solicitud pendiente.
* El sistema debe exigir seleccionar un motivo.
* El sistema debe mostrar la solicitud rechazada en "Trabajos rechazados".
* El sistema debe notificar al cliente con el motivo del rechazo.

#### DoD Técnico
* El modelo de motivos de rechazo se encuentra documentado.
* Las pruebas de rechazo sobre solicitudes en estados no permitidos se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.27 El sistema debe vencer las solicitudes sin respuesta

#### Definición
Como cliente quiero que las solicitudes sin respuesta venzan tras un plazo para poder generar una nueva.

#### DoD de Negocio
* El sistema debe vencer una solicitud pendiente cuando el profesional la acepta, cuando pasa 1 mes desde su envío o cuando el cliente la elimina.
* El sistema debe pasar la solicitud a estado Vencida si pasa 1 mes sin que el profesional la tome.
* El sistema debe notificar al cliente dentro de la plataforma el tiempo máximo transcurrido sin que nadie tomara la solicitud, para que genere una nueva.
* El sistema debe permitir al cliente volver a solicitar a otro profesional.

#### DoD Técnico
* La tarea programada de vencimiento se encuentra implementada y documentada.
* Las pruebas de vencimiento por cada causa se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.28 El sistema debe permitir al profesional finalizar un servicio

#### Definición
Como profesional quiero marcar un servicio como finalizado para informar que el trabajo fue realizado.

#### DoD de Negocio
* El sistema debe mostrar el botón "Finalizar servicio" en los servicios aceptados.
* El sistema debe registrar la confirmación del profesional y enviar al cliente la solicitud de confirmación.
* El sistema no debe considerar el servicio finalizado hasta que ambas partes confirmen.

#### DoD Técnico
* El diagrama de estados del servicio se encuentra documentado.
* Las pruebas de la confirmación del profesional se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.29 El sistema debe permitir al cliente confirmar la finalización del servicio

#### Definición
Como cliente quiero confirmar que el servicio terminó para cerrar formalmente la solicitud.

#### DoD de Negocio
* El sistema debe permitir al cliente confirmar la finalización y registrar su confirmación.
* El sistema debe cambiar el estado a Finalizado cuando ambas partes confirmen y habilitar la valoración.
* El sistema debe enviar un recordatorio dentro de la plataforma si el cliente no confirma tras 7 días hábiles.
* El sistema debe dejar el servicio visible para revisión del administrador pasados otros 7 días hábiles sin confirmación.

#### DoD Técnico
* La tarea programada de recordatorios se encuentra implementada y documentada.
* El cálculo de días hábiles (fines de semana y feriados) se encuentra documentado y probado.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.30 El sistema debe permitir al cliente calificar al profesional

#### Definición
Como cliente quiero calificar al profesional al finalizar el servicio para reflejar mi experiencia y ayudar a otros usuarios.

#### DoD de Negocio
* El sistema debe habilitar la valoración solo cuando el servicio esté Finalizado.
* El sistema debe permitir calificar calidad, puntualidad y trato en una escala de 1 a 5, con comentario opcional.
* El sistema no debe permitir valorar más de una vez por servicio ni pasado 1 mes desde la aceptación de la solicitud.
* El sistema debe asociar la valoración al oficio del servicio y actualizar el promedio de ese oficio, de forma independiente de los demás.
* El sistema debe mostrar en el perfil el promedio, la cantidad de valoraciones y las opiniones por oficio.

#### DoD Técnico
* El modelo de datos de valoraciones y la regla de cálculo del promedio se encuentran documentados.
* Las pruebas de valoración sobre servicios no finalizados, duplicados y fuera de plazo se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.31 El sistema debe permitir al profesional calificar al cliente

#### Definición
Como profesional quiero calificar al cliente para dejar constancia de cómo fue la interacción.

#### DoD de Negocio
* El sistema debe habilitar la valoración solo cuando el servicio esté Finalizado.
* El sistema debe permitir calificar según los criterios definidos por el equipo, con comentario opcional.
* El sistema no debe permitir valorar más de una vez por servicio ni pasado 1 mes desde la aceptación de la solicitud.
* El sistema debe mostrar al profesional el promedio y la cantidad de valoraciones del cliente al recibir una solicitud, o "Sin historial".

#### DoD Técnico
* Los criterios de calificación del cliente se encuentran definidos y documentados.
* Las pruebas de valoración duplicada y fuera de plazo se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.32 El sistema debe permitir visualizar el Centro de Desarrollo Profesional

#### Definición
Como profesional quiero acceder a una sección de capacitación para mejorar la formalización y estabilidad de mi actividad.

#### DoD de Negocio
* El sistema debe permitir el acceso solo a profesionales con acceso a funciones de trabajador.
* El sistema debe organizar los contenidos por módulos: tributario, seguridad y gestión.
* El sistema debe listar videos, guías propias y enlaces a entidades oficiales, indicando claramente cuáles son externos.
* El sistema debe permitir marcar los contenidos como vistos y mostrar el avance por módulo.
* El sistema no debe permitir el acceso a visitantes ni a clientes.

#### DoD Técnico
* El modelo de datos de módulos, contenidos y avance se encuentra documentado.
* El alojamiento de los videos y guías se encuentra definido y los enlaces externos se encuentran verificados.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.33 El sistema debe permitir solicitar un ticket por problemas en la plataforma

#### Definición
Como usuario quiero solicitar un ticket cuando tengo un problema con la plataforma para que el administrador lo revise y me ayude a resolverlo.

#### DoD de Negocio
* El sistema debe permitir crear un ticket indicando el motivo y describiendo el problema, con fotografías opcionales.
* El sistema debe permitir crearlo hasta 3 meses después de la solicitud o del desperfecto de la plataforma que lo origina.
* El sistema debe entregar al administrador el ticket con los datos de contexto (usuario y solicitud o servicio relacionado).
* El sistema debe mostrar el estado del ticket (Abierto, En revisión o Resuelto) y la respuesta del administrador.
* El sistema debe notificar dentro de la plataforma cuando el ticket cambie de estado.

#### DoD Técnico
* El modelo de datos de tickets y el cálculo del plazo de 3 meses se encuentran documentados.
* La carga de fotografías valida tipo y tamaño en el servidor.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.34 El sistema debe permitir al administrador resolver los tickets de los usuarios

#### Definición
Como administrador quiero revisar y resolver los tickets de los usuarios para solucionar los problemas que tienen con la plataforma.

#### DoD de Negocio
* El sistema debe mostrar un listado de tickets filtrable por estado y antigüedad.
* El sistema debe permitir ver el detalle, los datos de contexto y las fotografías.
* El sistema debe permitir responder, cambiar el estado y cerrar el ticket indicando la resolución.
* El sistema debe registrar la resolución en la bitácora y notificar al usuario.
* El sistema no debe permitir esta función a usuarios sin rol de administrador.

#### DoD Técnico
* El endpoint de tickets se encuentra restringido por rol y probado con usuarios sin rol de administrador.
* El diagrama de estados del ticket se encuentra documentado.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.35 El sistema debe permitir al profesional contratar la suscripción mensual

#### Definición
Como profesional verificado quiero suscribirme mensualmente para acceder a las funciones de trabajador.

#### DoD de Negocio
* El sistema debe informar claramente el monto de la suscripción ($10.000 CLP mensuales) y lo que incluye.
* El sistema debe generar la orden de pago automáticamente en el momento en que la identidad del profesional queda verificada.
* El sistema debe otorgar 7 días de prueba gratuita desde la verificación, con acceso a las funciones de trabajador.
* El sistema debe permitir pagar mediante una pasarela de pago y confirmar el pago al profesional.
* El sistema debe dejar la suscripción vigente por un mes y las funciones de trabajador activas al confirmarse el pago.
* En caso de que el pago falle, el sistema no debe activar la suscripción e informará el motivo.

#### DoD Técnico
* La integración con la pasarela de pago en entorno de pruebas se encuentra documentada.
* El sistema no almacena datos de tarjetas y la confirmación de pago se valida en el servidor.
* La generación automática de la orden al verificar al profesional se encuentra implementada y probada.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.36 El sistema debe gestionar el vencimiento y la renovación de la suscripción

#### Definición
Como profesional quiero recibir avisos de vencimiento y poder renovar para no perder el acceso por descuido.

#### DoD de Negocio
* El sistema debe mostrar el estado de la suscripción (vigente, por vencer o vencida), la fecha de renovación, el monto y el historial de pagos.
* El sistema debe notificar dentro de la plataforma, 5 días antes del vencimiento (también al término de la prueba), que la suscripción está próxima a vencer y que el perfil quedará sin visualización.
* El sistema debe generar la orden de pago de cada renovación mensual 5 días antes del vencimiento, junto con el aviso.
* El sistema debe permitir reintentar un pago fallido.
* En caso de que la suscripción venza, el sistema debe dejar el perfil sin visualización y guardado, sin eliminar sus datos, hasta que se genere el pago.
* El sistema debe volver a mostrar el perfil al confirmarse el pago.

#### DoD Técnico
* La tarea programada de órdenes de renovación y avisos se encuentra implementada y documentada.
* Las pruebas de vencimiento, pago fallido y reactivación del perfil se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.37 El sistema debe permitir al profesional cancelar su suscripción

#### Definición
Como profesional quiero cancelar mi suscripción cuando lo estime pertinente para no ser cobrado en el próximo período.

#### DoD de Negocio
* El sistema debe permitir cancelar la suscripción en cualquier momento, cuando el profesional lo estime pertinente.
* El sistema debe pedir confirmación antes de cancelar.
* El sistema debe mantener el acceso hasta el fin del período pagado.
* El sistema debe permitir volver a suscribirse.

#### DoD Técnico
* El diagrama de estados de la suscripción se encuentra documentado.
* Las pruebas de cancelación y nueva suscripción se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.38 El sistema debe permitir recibir y consultar notificaciones dentro de la plataforma

#### Definición
Como usuario quiero recibir notificaciones dentro de la plataforma para no perder información importante sobre mis solicitudes, servicios y cuenta.

#### DoD de Negocio
* El sistema debe notificar al profesional la verificación aprobada o rechazada, la respuesta del administrador, las nuevas solicitudes, las solicitudes eliminadas y el vencimiento próximo de su suscripción.
* El sistema debe notificar al cliente cuando su solicitud sea aceptada, rechazada o vencida.
* El sistema debe notificar a ambas partes la confirmación de finalización pendiente, el cierre forzoso y los cambios en sus tickets.
* El sistema debe mostrar un acceso visible con el número de notificaciones sin leer, permitir marcarlas como leídas y llevar cada una al elemento relacionado.
* El sistema debe mostrar las notificaciones únicamente dentro de la plataforma.
* El sistema no debe enviar notificaciones por correo electrónico.

#### DoD Técnico
* La matriz de eventos y destinatarios de las notificaciones se encuentra documentada.
* El modelo de datos y el endpoint de notificaciones se encuentran documentados.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.39 El sistema debe permitir al administrador acceder a un panel de administración

#### Definición
Como administrador quiero ingresar a un panel exclusivo para gestionar los procesos que requieren intervención.

#### DoD de Negocio
* El sistema debe permitir el acceso al panel solo a usuarios con rol administrador.
* El sistema debe mostrar accesos a verificaciones, usuarios, solicitudes y servicios, tickets, suscripciones, moderación, contenidos e indicadores.
* El sistema debe rechazar y registrar los intentos de acceso no autorizado.

#### DoD Técnico
* Las rutas del panel se encuentran protegidas por rol y verificadas con pruebas.
* La vista es responsiva (escritorio y móvil).
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.40 El sistema debe permitir al administrador gestionar los perfiles de usuario

#### Definición
Como administrador quiero gestionar los perfiles de clientes y profesionales para controlar a quienes infrinjan las normas o no puedan validar su identidad.

#### DoD de Negocio
* El sistema debe permitir buscar clientes y profesionales y ver su estado.
* El sistema debe permitir consultar la información completa de un profesional (RUT, dirección exacta y documento de verificación), registrando cada consulta con administrador, fecha y motivo.
* El sistema debe permitir suspender, bloquear o reactivar una cuenta, exigiendo un motivo y notificando al usuario afectado.
* El sistema debe permitir dar de baja a un usuario completo, exigiendo un motivo, y eliminar la información asociada salvo la que el administrador recupere.
* El sistema no debe permitir a un profesional suspendido o bloqueado acceder a las funciones de trabajador, ni a un usuario dado de baja iniciar sesión o aparecer en búsquedas.

#### DoD Técnico
* Los estados de cuenta y sus efectos se encuentran documentados.
* El proceso de baja y los datos que se eliminan se encuentran definidos y documentados.
* Las pruebas de autorización por rol y de acceso con cuentas suspendidas, bloqueadas y dadas de baja se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.41 El sistema debe permitir al administrador recuperar datos de los perfiles

#### Definición
Como administrador quiero recuperar los datos asociados a un perfil dado de baja o eliminado para no perder información cuando un usuario se ingresa nuevamente o hubo un problema.

#### DoD de Negocio
* El sistema debe permitir consultar los datos asociados a un usuario dado de baja o a un perfil eliminado.
* El sistema debe permitir seleccionar qué datos recuperar y asignarlos a un nuevo usuario.
* El sistema debe permitir solo al administrador recuperar valoraciones y puntuaciones inactivas cuando existan problemas relacionados con trabajadores o usuarios.
* El sistema debe exigir un motivo y recalcular los promedios y el historial al recuperar valoraciones.
* El sistema no debe permitir a profesionales ni clientes recuperar datos por sí mismos.

#### DoD Técnico
* El tiempo y el alcance de la recuperación de datos se encuentran definidos y documentados.
* Las pruebas de reasignación sin pérdida ni duplicación de datos y de recálculo de promedios se encuentran ejecutadas y documentadas.
* El registro de las acciones en la bitácora se encuentra implementado.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.42 El sistema debe permitir al administrador moderar los contenidos y accesos de la plataforma

#### Definición
Como administrador quiero moderar lo que los usuarios publican o adjuntan para mantener la plataforma confiable y respetuosa.

#### DoD de Negocio
* El sistema debe mostrar las reseñas reportadas con su motivo y permitir mantenerlas o eliminarlas indicando un motivo, recalculando los promedios.
* El sistema debe permitir revisar las solicitudes de modificación o eliminación de una valoración.
* El sistema debe permitir aprobar o rechazar las certificaciones adjuntas, mostrando las aprobadas como verificadas en el perfil.
* El sistema debe permitir crear, editar, ocultar y reordenar los contenidos del Centro de Desarrollo Profesional y agregar enlaces externos oficiales.
* El sistema debe permitir suspender, bloquear o dar de baja perfiles que infrinjan las normas.
* El sistema debe exigir un motivo en cada decisión, registrarla en la bitácora y notificar a las partes involucradas.

#### DoD Técnico
* El modelo de datos de reportes, certificaciones y contenidos se encuentra documentado.
* Las pruebas de autorización por rol y de recálculo de promedios se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.43 El sistema debe permitir al administrador supervisar solicitudes y servicios y cerrarlos forzosamente

#### Definición
Como administrador quiero ver las solicitudes y los servicios en curso para detectar casos que requieran intervención y cerrarlos cuando no se puedan cerrar de forma normal.

#### DoD de Negocio
* El sistema debe mostrar un listado de solicitudes y servicios filtrable por estado y antigüedad, destacando los que tienen confirmación pendiente.
* El sistema debe permitir abrir un servicio y ejecutar el cierre forzoso, exigiendo un motivo.
* El sistema debe registrar que el cierre fue realizado por administración.
* El sistema debe eliminar la información del cliente asociada al servicio y no habilitar la valoración al cerrarlo forzosamente.
* El sistema debe permitir dar de baja al usuario completo en el caso del profesional.
* El sistema no debe permitir el cierre forzoso a usuarios sin rol de administrador.

#### DoD Técnico
* Los datos que se eliminan en un cierre forzoso se encuentran definidos y documentados.
* El endpoint de supervisión con filtros y paginación se encuentra documentado.
* Las pruebas de autorización por rol se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.44 El sistema debe permitir al administrador gestionar las suscripciones de los profesionales

#### Definición
Como administrador quiero ver el estado de suscripción de los profesionales y corregir casos excepcionales.

#### DoD de Negocio
* El sistema debe permitir consultar y filtrar por estado de suscripción.
* El sistema debe permitir activar o suspender manualmente una suscripción, exigiendo un motivo.
* El sistema debe registrar la acción en la bitácora.
* El sistema no debe permitir esta función a usuarios sin rol de administrador.

#### DoD Técnico
* Las pruebas de autorización por rol se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.45 El sistema debe permitir al administrador ver indicadores de uso de la plataforma

#### Definición
Como administrador quiero ver indicadores de uso para tomar decisiones sobre la plataforma.

#### DoD de Negocio
* El sistema debe mostrar solicitudes por oficio y comuna, tasa de aceptación y promedio de valoraciones.
* El sistema debe mostrar suscripciones vigentes y vencidas.
* El sistema debe mostrar el desempeño del chatbot: sugerencias por especialidad y porcentaje de respuestas útiles.
* El sistema debe permitir filtrar por período.
* El sistema no debe permitir el acceso a usuarios sin rol de administrador.

#### DoD Técnico
* Las consultas de los indicadores se encuentran documentadas y optimizadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.

---

### 4.46 El sistema debe registrar las acciones administrativas en una bitácora

#### Definición
Como administrador quiero que mis acciones queden registradas para poder auditarlas.

#### DoD de Negocio
* El sistema debe registrar quién, qué, cuándo y el motivo de cada acción administrativa.
* El sistema no debe permitir modificar ni eliminar la bitácora desde la aplicación.
* El sistema debe permitir consultar y filtrar la bitácora por fecha, administrador o tipo de acción.

#### DoD Técnico
* El modelo de datos de la bitácora se encuentra documentado.
* Las pruebas que verifican que los registros no pueden alterarse se encuentran ejecutadas y documentadas.
* El código se encuentra subido al GitHub y con su validación de pares.
* Las pruebas funcionales de la historia se encuentran ejecutadas y documentadas.
* La funcionalidad se encuentra desplegada en el ambiente de pruebas y validada por el Product Owner.