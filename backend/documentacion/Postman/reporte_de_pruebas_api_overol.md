# Informe de Pruebas Automatizadas de API - Overol

Este documento consolida la definición técnica de la colección de pruebas de Postman (`Overol - Pruebas API`) junto con los resultados obtenidos en la ejecución automatizada (*Test Run*).

---

## 1. Resumen Ejecutivo de la Ejecución

| Métrica | Valor |
| :--- | :--- |
| **Fecha y hora de ejecución** | 19 de Octubre de 2026, 00:23:58 UTC |
| **Colección** | Overol - Pruebas API |
| **Estado final** | `finished` |
| **Total de peticiones ejecutadas** | 17 |
| **Total de pruebas / aserciones** | 54 |
| **Pruebas superadas (Pass)** | 54 (100%) |
| **Pruebas fallidas (Fail)** | 0 (0%) |
| **Tiempo total de ejecución** | 4.629 ms (~4,63 s) |

---

## 2. Resumen de Pruebas por Módulo

| Código | Nombre de la Prueba | Método | Endpoint / URL | Status Esperado | Status Obtenido | Tiempo (ms) | Resultado |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **AUTH-01** | Registrar cliente | `POST` | `/api/auth/register/` | 201 Created | 201 Created | 998 | PASS |
| **AUTH-02** | Obtener token JWT | `POST` | `/api/auth/token/` | 200 OK | 200 OK | 985 | PASS |
| **AUTH-03** | Consultar perfil propio | `GET` | `/api/auth/me/` | 200 OK | 200 OK | 45 | PASS |
| **AUTH-04** | Acceso sin token | `GET` | `/api/auth/me/` | 401 Unauthorized | 401 Unauthorized | 5 | PASS |
| **AUTH-05** | Renovar token | `POST` | `/api/auth/token/refresh/` | 200 OK | 200 OK | 40 | PASS |
| **AUTH-06** | Obtener token profesional | `POST` | `/api/auth/token/` | 200 OK | 200 OK | 1049 | PASS |
| **CAT-01** | Listar profesionales | `GET` | `/api/catalog/professionals/` | 200 OK | 200 OK | 63 | PASS |
| **CAT-02** | Buscar profesionales | `GET` | `/api/catalog/professionals/?keyword=gasfiter...` | 200 OK | 200 OK | 62 | PASS |
| **VIS-01** | Crear solicitud | `POST` | `/api/requests/` | 201 Created | 201 Created | 46 | PASS |
| **VIS-02** | Listar solicitudes | `GET` | `/api/requests/` | 200 OK | 200 OK | 44 | PASS |
| **NEG-01** | Registro sin aceptar privacidad | `POST` | `/api/auth/register/` | 400 Bad Request | 400 Bad Request | 53 | PASS |
| **NEG-02** | Registro con RUT inválido | `POST` | `/api/auth/register/` | 400 Bad Request | 400 Bad Request | 53 | PASS |
| **NEG-03** | Login con contraseña incorrecta | `POST` | `/api/auth/token/` | 401 Unauthorized | 401 Unauthorized | 1011 | PASS |
| **NEG-04** | Consultar perfil sin token | `GET` | `/api/auth/me/` | 401 Unauthorized | 401 Unauthorized | 5 | PASS |
| **NEG-05** | Crear solicitud sin campos obligatorios | `POST` | `/api/requests/` | 400 Bad Request | 400 Bad Request | 47 | PASS |
| **NEG-06** | Crear solicitud con profesional inexistente | `POST` | `/api/requests/` | 400/404 | 400 Bad Request | 47 | PASS |
| **NEG-07** | Rechazar solicitud sin motivo | `POST` | `/api/requests/{{visit_id}}/reject/` | 400 Bad Request | 400 Bad Request | 76 | PASS |

---

## 3. Detalle Técnico de Casos de Prueba

### Módulo: Autenticación (`/auth`)

#### AUTH-01 Registrar cliente
* **Método y URL:** `POST {{base_url}}/auth/register/`
* **Pre-request Script:** Generación dinámica de RUT chileno válido mediante algoritmo módulo 11 y correo electrónico con prefijo de tiempo unix (`cliente.postman.<timestamp>@ejemplo.cl`).
* **Payload enviado:**
  ```json
  {
    "email": "{{test_email}}",
    "first_name": "Ana",
    "last_name": "Pérez",
    "phone": "+56912345678",
    "rut": "{{test_rut}}",
    "address": "Av. Principal 123",
    "commune": "Santiago",
    "role": "CLIENT",
    "password": "ClaveSegura123!",
    "privacy_policy_accepted": true,
    "privacy_policy_version": "2026-10"
  }
  ```
* **Aserciones validadas:**
  * Status 201 - Registro exitoso
  * Respuesta tiene campo `id`
  * Respuesta tiene campo `email`
  * Content-Type es `application/json`
* **Resultado de ejecución:** 201 Created (998 ms) - **PASS**

#### AUTH-02 Obtener token JWT
* **Método y URL:** `POST {{base_url}}/auth/token/`
* **Payload enviado:**
  ```json
  {
    "email": "{{test_email}}",
    "password": "ClaveSegura123!"
  }
  ```
* **Aserciones validadas:**
  * Status 200 - Token obtenido
  * Respuesta tiene `access_token` (almacenado en el entorno)
  * Respuesta tiene `refresh_token` (almacenado en el entorno)
  * `access_token` es tipo string y no está vacío
* **Resultado de ejecución:** 200 OK (985 ms) - **PASS**

#### AUTH-03 Consultar perfil
* **Método y URL:** `GET {{base_url}}/auth/me/`
* **Autenticación:** Bearer Token (`{{access_token}}`)
* **Aserciones validadas:**
  * Status 200 - Perfil obtenido
  * Respuesta contiene la propiedad `email`
  * Content-Type incluye `application/json`
* **Resultado de ejecución:** 200 OK (45 ms) - **PASS**

#### AUTH-04 Acceso sin token
* **Método y URL:** `GET {{base_url}}/auth/me/`
* **Autenticación:** Ninguna (`noauth`)
* **Aserciones validadas:**
  * Status 401 - No autorizado sin token
  * Respuesta contiene el objeto/mensaje de error `detail`
* **Resultado de ejecución:** 401 Unauthorized (5 ms) - **PASS**

#### AUTH-05 Renovar token
* **Método y URL:** `POST {{base_url}}/auth/token/refresh/`
* **Payload enviado:**
  ```json
  {
    "refresh": "{{refresh_token}}"
  }
  ```
* **Aserciones validadas:**
  * Status 200 - Token renovado
  * Respuesta entrega un nuevo `access_token` (actualizado en entorno)
  * El nuevo token no está vacío
* **Resultado de ejecución:** 200 OK (40 ms) - **PASS**

#### AUTH-06 Obtener token profesional
* **Método y URL:** `POST {{base_url}}/auth/token/`
* **Payload enviado:**
  ```json
  {
    "email": "profesional.postman@ejemplo.cl",
    "password": "ProfesionalSegura123!"
  }
  ```
* **Aserciones validadas:**
  * Status 200 - Token profesional obtenido (`professional_access_token` persistido en entorno)
* **Resultado de ejecución:** 200 OK (1049 ms) - **PASS**

---

### Módulo: Catálogo (`/catalog`)

#### CAT-01 Listar profesionales
* **Método y URL:** `GET {{base_url}}/catalog/professionals/`
* **Aserciones validadas:**
  * Status 200 - Listado de profesionales
  * La respuesta es un array o contiene lista paginada en `results`
  * Content-Type es `application/json`
  * Tiempo de respuesta inferior a 3.000 ms
  * *Efecto secundario:* Guarda `professional_id` y `specialty_id` para pruebas dependientes.
* **Resultado de ejecución:** 200 OK (63 ms) - **PASS**

#### CAT-02 Buscar profesionales
* **Método y URL:** `GET {{base_url}}/catalog/professionals/?keyword=gasfiter&page=1&page_size=20`
* **Aserciones validadas:**
  * Status 200 - Búsqueda exitosa
  * Respuesta contiene colección de datos
  * Content-Type incluye `application/json`
  * Tiempo de respuesta inferior a 3.000 ms
* **Resultado de ejecución:** 200 OK (62 ms) - **PASS**

---

### Módulo: Solicitudes de Visita (`/requests`)

#### VIS-01 Crear solicitud
* **Método y URL:** `POST {{base_url}}/requests/`
* **Autenticación:** Bearer Token (`{{access_token}}`)
* **Payload enviado:**
  ```json
  {
    "professional": {{professional_id}},
    "specialty": {{specialty_id}},
    "problem_description": "El enchufe de la cocina no funciona.",
    "tentative_schedule": "Sábado por la mañana",
    "visit_address": "Calle Ejemplo 123"
  }
  ```
* **Aserciones validadas:**
  * Status 201 - Solicitud creada
  * Respuesta contiene identificador `id` (guardado en `{{visit_id}}`)
  * Respuesta contiene campo `status`
  * Content-Type es `application/json`
* **Resultado de ejecución:** 201 Created (46 ms) - **PASS**

#### VIS-02 Listar solicitudes
* **Método y URL:** `GET {{base_url}}/requests/`
* **Autenticación:** Bearer Token (`{{access_token}}`)
* **Aserciones validadas:**
  * Status 200 - Listado de solicitudes
  * Respuesta devuelve un listado o colección `results`
  * Content-Type es `application/json`
  * Tiempo de respuesta menor a 3.000 ms
* **Resultado de ejecución:** 200 OK (44 ms) - **PASS**

---

### Módulo: Casos Negativos y Validaciones (`NEG`)

#### NEG-01 Registro sin aceptar privacidad
* **Método y URL:** `POST {{base_url}}/auth/register/`
* **Cuerpo de prueba:** `"privacy_policy_accepted": false`
* **Aserciones validadas:**
  * Status 400 - Error por falta de aceptación de privacidad
  * Respuesta contiene al menos un mensaje de validación
  * Formato JSON
* **Resultado de ejecución:** 400 Bad Request (53 ms) - **PASS**

#### NEG-02 Registro con RUT inválido
* **Método y URL:** `POST {{base_url}}/auth/register/`
* **Cuerpo de prueba:** `"rut": "00.000.000-0"`
* **Aserciones validadas:**
  * Status 400 - Error por formato/dígito verificador de RUT
  * Respuesta contiene detalle de error
  * Formato JSON
* **Resultado de ejecución:** 400 Bad Request (53 ms) - **PASS**

#### NEG-03 Login con contraseña incorrecta
* **Método y URL:** `POST {{base_url}}/auth/token/`
* **Cuerpo de prueba:** `"password": "ContraseñaIncorrecta!"`
* **Aserciones validadas:**
  * Status 401 - Credenciales incorrectas
  * Respuesta contiene la propiedad `detail`
  * No expone ninguna propiedad de token (`access`)
* **Resultado de ejecución:** 401 Unauthorized (1011 ms) - **PASS**

#### NEG-04 Consultar perfil sin token
* **Método y URL:** `GET {{base_url}}/auth/me/`
* **Autenticación:** Sin cabecera `Authorization`
* **Aserciones validadas:**
  * Status 401 - No autorizado
  * Respuesta contiene campo de error `detail`
  * No expone datos personales (`email`)
* **Resultado de ejecución:** 401 Unauthorized (5 ms) - **PASS**

#### NEG-05 Crear solicitud sin campos obligatorios
* **Método y URL:** `POST {{base_url}}/requests/`
* **Autenticación:** Bearer Token (`{{access_token}}`)
* **Cuerpo de prueba:** `{}` (objeto vacío)
* **Aserciones validadas:**
  * Status 400 - Error por campos requeridos faltantes
  * Respuesta lista los errores de validación
  * No genera ningún identificador de recurso (`id`)
* **Resultado de ejecución:** 400 Bad Request (47 ms) - **PASS**

#### NEG-06 Crear solicitud con profesional inexistente
* **Método y URL:** `POST {{base_url}}/requests/`
* **Autenticación:** Bearer Token (`{{access_token}}`)
* **Cuerpo de prueba:** `"professional": 99999`
* **Aserciones validadas:**
  * Status 400 o 404 (Entidad no encontrada / Clave foránea inexistente)
  * Respuesta describe el error
  * No se crea el registro
* **Resultado de ejecución:** 400 Bad Request (47 ms) - **PASS**

#### NEG-07 Rechazar solicitud sin motivo
* **Método y URL:** `POST {{base_url}}/requests/{{visit_id}}/reject/`
* **Autenticación:** Bearer Token (`{{professional_access_token}}`)
* **Cuerpo de prueba:** `{}` (sin campo de motivo)
* **Aserciones validadas:**
  * Status 400 - Error por omisión de motivo de rechazo
  * Respuesta describe el requerimiento faltante
  * Content-Type incluye `application/json`
* **Resultado de ejecución:** 400 Bad Request (76 ms) - **PASS**