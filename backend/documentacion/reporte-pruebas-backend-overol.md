# Reporte de pruebas del backend Overol

## Alcance

Se probaron las reglas y endpoints backend implementados en autenticación, catálogo, visitas, calificaciones, tickets y Centro de Desarrollo Profesional. No se contabilizaron interfaces gráficas ni pruebas visuales.

## Comandos ejecutados

Desde `backend/`:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test apps.authentication apps.catalog apps.visits
```

Resultado:

- `check`: correcto, sin problemas del sistema.
- `makemigrations --check`: correcto, no hay migraciones pendientes.
- Pruebas Django: **33 pruebas ejecutadas, 33 correctas, 0 errores**.
- La suite creó y destruyó una base de datos de pruebas independiente.

## Casos probados

### Autenticación y seguridad: 13 pruebas

- Sanitización de nombres y rechazo de payloads de SQL injection.
- Escape seguro de comillas mediante el ORM.
- Validación de RUT con módulo 11.
- Obtención, renovación y uso de tokens JWT.
- Rechazo de tokens para cuentas desactivadas.
- Registro con aceptación de privacidad y contraseña robusta.
- Bloqueo después de tres intentos fallidos y entrega de `retry_after`.
- Ocultamiento de RUT y dirección para clientes.
- Acceso privado de administradores a documentos de verificación.
- Reglas de cambio de estado de cuenta y motivo obligatorio.
- Logout y blacklist del refresh token.
- Decisión administrativa de verificación, notificación y auditoría.

### Catálogo y geolocalización: 9 pruebas

- Listado únicamente de profesionales aprobados.
- Filtro por zona de atención.
- Búsqueda por palabras clave.
- Resistencia del filtro de búsqueda ante payloads de SQL injection.
- Filtros combinados por especialidad y comuna.
- Validación de radios permitidos para búsqueda geográfica.
- Mensaje explícito cuando PostGIS no está disponible.
- Actualización de disponibilidad y creación de oficios por profesionales.
- Restricción de gestión de disponibilidad para clientes.

### Visitas, calificaciones y posventa: 11 pruebas

- Flujo de visita que requiere confirmación del profesional y del cliente.
- Bloqueo de finalización de una visita pendiente.
- Motivo obligatorio al rechazar una solicitud.
- Rechazo de días y horarios fuera de la disponibilidad declarada.
- Creación de solicitudes con expiración a 30 días.
- Expiración de solicitudes antiguas y notificación única por ejecución.
- Una sola calificación dentro de la ventana permitida.
- Rechazo de calificaciones después de 30 días de completado el servicio.
- Ocultamiento de contactos antes de la aceptación y para terceros.
- Creación de tickets con límite de descripción y resolución administrativa.
- Protección por rol y registro de progreso en el Centro de Desarrollo Profesional.

## Cómo se probaron

Las pruebas usan `django.test.TestCase` y `rest_framework.test.APIClient`/`APIRequestFactory`. Cada caso crea sus propios usuarios, perfiles, oficios, especialidades y visitas en la base temporal; después verifica estados HTTP, errores de validación, transiciones de estado, datos persistidos, notificaciones y permisos.

Para la expiración se creó una solicitud y se ajustó su `created_at` mediante `QuerySet.update()` para simular una solicitud de más de 30 días sin alterar el comportamiento de `auto_now_add`. Para las coordenadas se verificaron rangos, precisión y validación de la dependencia PostGIS.

## Resultado y cobertura pendiente

El backend cubierto por estos módulos funciona correctamente en la suite ejecutada. Estas pruebas no certifican:

- Envío real mediante un servidor SMTP.
- Ejecución automática programada del comando de expiración.
- Carga de documentos válidos con archivos reales y Pillow.
- Búsqueda geoespacial con profesionales realmente dentro y fuera de un radio en una instancia PostGIS de integración.
- Todos los endpoints de reclamos, notificaciones y administración que no tienen casos específicos en esta suite.
- Integración con servicios externos o despliegue productivo.

## Validación contra la base Docker

Además de la suite con base temporal, el catálogo base se valida contra la
instancia PostgreSQL/PostGIS de Docker ejecutando:

```powershell
docker compose up -d db
python manage.py migrate
python manage.py shell -c "from apps.catalog.models import TradeCategory, Specialty; print(list(TradeCategory.objects.values_list('name', flat=True))); print(Specialty.objects.count())"
```

La migración `0004_seed_default_catalog` es idempotente y deja disponibles
Electricidad, Gasfitería y Cerrajería, junto con sus especialidades, después de
`migrate`.

Resultado en esta ejecución:

- El contenedor `overol_db` existente estaba activo y fue reutilizado.
- `python manage.py migrate`: correcto; no quedaron migraciones pendientes.
- Catálogo base: Electricidad, Gasfitería y Cerrajería presentes.
- Especialidades base: Instalaciones eléctricas, Reparación de fugas y
  Apertura y cambio de cerraduras presentes.
- Suite contra Docker: **33 pruebas correctas** usando PostgreSQL/PostGIS.
- `python manage.py check`: correcto.
- `python manage.py makemigrations --check`: correcto, sin cambios detectados.

Las pruebas que crean categorías usan nombres propios de prueba para no
colisionar con el catálogo base persistente de Docker.
