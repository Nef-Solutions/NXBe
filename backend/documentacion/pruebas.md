# Acta de pruebas del backend Overol

**Fecha de ejecución:** 17/10/2026  
**Proyecto:** Overol Backend  
**Entorno:** Windows, Python 3.14, Django, Django REST Framework y PostgreSQL

## 1. Objetivo

Registrar las comprobaciones ejecutadas sobre el backend y dejar evidencia de qué se probó, cómo se probó y cuál fue el resultado.

## 2. Condiciones del entorno

Antes de probar fue necesario instalar las dependencias declaradas en `documentacion/requirements.txt` y disponer de PostgreSQL funcionando. Las migraciones se aplicaron con:

```powershell
python manage.py migrate
```

La primera ejecución del comando de vencimiento falló porque la tabla `visits_visitrequest` todavía no existía. Después de aplicar las migraciones, el comando funcionó correctamente.

## 3. Resumen de resultados

| Área | Pruebas | Resultado |
| :--- | :---: | :--- |
| Comprobación Django | `1` | Aprobada |
| Migraciones | `1` ejecución | Aprobada |
| Autenticación y JWT | `6` | Aprobadas |
| Catálogo y búsqueda | `4` | Aprobadas |
| Visitas y estados | `3` | Aprobadas |
| Comando de vencimiento | `1` ejecución | Aprobada |
| **Total de pruebas unitarias** | **13** | **13 aprobadas** |

## 4. Pruebas de configuración

### 4.1 Comprobación del proyecto Django

**Comando:**

```powershell
python manage.py check
```

**Qué se probó:**

- Configuración de Django.
- Registro de aplicaciones.
- Carga de URLs.
- Modelos y relaciones reconocidas por Django.
- Configuración administrativa.

**Resultado:** aprobado.

```text
System check identified no issues (0 silenced).
```

### 4.2 Aplicación de migraciones

**Comando:**

```powershell
python manage.py migrate
```

**Qué se probó:**

- Creación de campos de usuario y seguridad.
- Creación de mensajes de verificación.
- Creación de oficios profesionales.
- Creación de solicitudes, calificaciones, reclamos, tickets, notificaciones, contenidos y bitácora.

**Resultado:** aprobado. Se aplicaron correctamente las migraciones pendientes:

- `authentication.0004_user_profile_and_privacy`
- `authentication.0005_account_security_and_case_messages`
- `catalog.0002_professional_trade`
- `visits.0001_initial`

## 5. Pruebas de autenticación y seguridad

**Comando:**

```powershell
python manage.py test apps.authentication.tests
```

**Resultado:** `6/6` aprobadas.

### Casos cubiertos

| Caso | Qué verifica | Resultado |
| :--- | :--- | :--- |
| Sanitización de nombres | Normaliza apóstrofes tipográficos, espacios y puntuación sobrante. | Aprobado |
| Rechazo de SQL injection | Rechaza secuencias como `;`, `--` y comentarios SQL. | Aprobado |
| ORM con apóstrofes | Permite nombres como `Bernardo O'Higgins` sin romper consultas. | Aprobado |
| Validación de RUT | Valida el algoritmo Módulo 11 y entrega formato canónico. | Aprobado |
| JWT | Obtiene access/refresh, renueva el access y usa Bearer en una ruta protegida. | Aprobado |
| JWT y cuentas inactivas | Rechaza tokens para cuentas dadas de baja. | Aprobado |

## 6. Pruebas de catálogo

**Comando:**

```powershell
python manage.py test apps.catalog.tests
```

**Resultado:** `4/4` aprobadas.

### Casos cubiertos

| Caso | Qué verifica | Resultado |
| :--- | :--- | :--- |
| Solo profesionales aprobados | Excluye perfiles pendientes de las búsquedas. | Aprobado |
| Filtro por zona | Encuentra profesionales relacionados con una zona del hogar. | Aprobado |
| Búsqueda por keyword | Encuentra coincidencias en keywords del oficio. | Aprobado |
| Keyword maliciosa | Una entrada SQL no altera ni amplía la consulta. | Aprobado |

## 7. Pruebas del ciclo de visitas

**Comando:**

```powershell
python manage.py test apps.visits.tests
```

**Resultado:** `3/3` aprobadas.

### Casos cubiertos

| Caso | Qué verifica | Resultado |
| :--- | :--- | :--- |
| Confirmación doble | El servicio pasa a `COMPLETED` después de la confirmación profesional y del cliente. | Aprobado |
| Finalización inválida | Una solicitud `PENDING` no puede finalizarse directamente. | Aprobado |
| Rechazo sin motivo | No permite rechazar una solicitud sin explicar la razón. | Aprobado |

## 8. Prueba del vencimiento de solicitudes

**Comando:**

```powershell
python manage.py expire_visit_requests
```

**Qué se probó:**

- Carga del comando personalizado de Django.
- Consulta de solicitudes pendientes antiguas.
- Cambio de estado a `EXPIRED`.
- Creación de notificación para el cliente.

**Resultado observado:** aprobado.

```text
0 solicitud(es) vencida(s).
```

El resultado `0` es correcto porque no había solicitudes pendientes con más de 30 días en la base de datos usada durante la ejecución.

## 9. Validación sintáctica

**Comando:**

```powershell
python -m compileall -q apps core manage.py
```

**Qué se probó:**

- Compilación sintáctica de los módulos Python.
- Ausencia de errores básicos de sintaxis en modelos, vistas, serializers, migraciones, comandos y URLs.

**Resultado:** aprobado.

## 10. Alcance no probado o pendiente

Las siguientes áreas no fueron probadas porque están fuera del alcance solicitado o requieren componentes que no están implementados:

- Suscripciones y pasarela de pago.
- Chatbot e integración con IA.
- Geolocalización real, mapas y radios de cobertura.
- Frontend responsivo.
- Envío real de correos de recuperación.
- Integración con servicios externos.
- Pruebas de carga y rendimiento.
- Despliegue en ambiente de pruebas o producción.
- Evidencias audiovisuales y aprobación del Product Owner.

## 11. Conclusión

Las comprobaciones ejecutadas sobre el backend fueron aprobadas: Django no reportó problemas de configuración, las migraciones se aplicaron correctamente, las 13 pruebas unitarias pasaron y el comando de vencimiento funcionó después de preparar el esquema de base de datos.

Este documento acredita las pruebas técnicas realizadas al código disponible en la fecha indicada. No acredita las áreas expresamente excluidas ni requisitos no relacionados con ejecución de código.