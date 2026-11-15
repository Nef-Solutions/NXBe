# Backend de Overol

API REST de Overol, desarrollada con Django y Django REST Framework. Conecta a
personas que necesitan trabajos en el hogar con profesionales; incluye
autenticación, catálogo, solicitudes, centro profesional, asistente y pagos
Webpay Plus exclusivamente en sandbox.

## Requisitos

- CPython 3.14.8 es el entorno usado para la validación actual.
- Docker Desktop con Docker Compose.
- PostgreSQL/PostGIS se puede iniciar con Docker Compose.
- La clave `GEMINI_API_KEY` es necesaria para respuestas reales de Overil.
- Para enviar códigos de recuperación fuera de desarrollo, configura un
  backend de correo saliente.

Las dependencias Python están en
[`documentacion/requirements.txt`](documentacion/requirements.txt). Ese archivo
fija las versiones de paquetes, pero no instala Python ni los servicios Docker.

## Puesta en marcha local

Ejecuta estos comandos desde la carpeta `backend/` en PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r documentacion\requirements.txt
docker compose up -d
python manage.py migrate
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

La API queda en `http://127.0.0.1:8000/api/` y Django Admin en
`http://127.0.0.1:8000/admin/`. La raíz y el panel local de prueba están en
`http://127.0.0.1:8000/local-dashboard/`; este último requiere un usuario staff.

Después de migrar, la base recibe 66 categorías oficiales de oficios y 9
recursos externos de seguridad (videos, canales y playlist de YouTube). Las
migraciones no reemplazan registros preexistentes con el mismo nombre o URL.
Las categorías se consultan desde `GET /api/catalog/categories/`; los recursos
visibles del centro profesional desde `GET /api/professional-center/content/`.

## Capacidades y límites importantes

- La verificación profesional es manual: el profesional carga ambos lados de
  la cédula como JPEG/PNG (hasta 5 MiB) o PDF (hasta 10 MiB); un administrador
  los revisa y autoriza. Los documentos se guardan en almacenamiento privado.
  No se hace OCR.
- La recuperación de contraseña envía un código de seis dígitos por correo.
  En desarrollo, el backend de correo predeterminado imprime el mensaje en la
  consola.
- Overil usa Gemini para recomendar un oficio del catálogo según el problema
  descrito; no guarda historial ni entrega diagnósticos o pasos de reparación.
  Limita el uso a 10 consultas por usuario/día, 50 globales/día, 5 por hora
  y 30 tokens para clasificar.
- Webpay Plus está configurado para sandbox. El plan profesional inicial cuesta
  $10.000 CLP por un mes; su valor y duración se administran en Django Admin.
  La renovación es manual y no hay cobro recurrente.

Configura `GEMINI_API_KEY` en `.env` para probar respuestas del modelo. No
incluyas credenciales privadas en el frontend ni en el repositorio. Antes de
desplegar, reemplaza secretos, desactiva `DEBUG`, restringe CORS y configura
correo, HTTPS, persistencia y acceso al almacenamiento privado.

## Pruebas y verificaciones

Desde `backend/`:

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Las pruebas Django usan una base temporal y simulan las llamadas externas a
Gemini y Transbank. No equivalen a una llamada real al modelo ni a una compra
sandbox. La última ejecución registrada obtuvo 76 pruebas aprobadas.

Las solicitudes pendientes de visita se pueden expirar al ejecutar:

```powershell
python manage.py expire_visit_requests
```

No hay un scheduler periódico configurado.

## Documentación

- [Manual técnico integral](documentacion/manual-tecnico-integral-backend.md):
  arquitectura, modelos, configuración, endpoints y límites.
- [Esquema de base de datos](documentacion/esquema-base-datos.md): diagrama ER
  Mermaid derivado de los modelos actuales.
- [Guía frontend/API](documentacion/guia-integracion-frontend-api.md):
  payloads, respuestas, permisos y flujos de integración.
- [Reporte Postman y estado de pruebas](documentacion/Postman/reporte_de_pruebas_api_overol.md):
  conserva por separado los resultados históricos de Postman y la cobertura
  Django actual.
- [Dependencias Python](documentacion/requirements.txt).

Los archivos JSON de la carpeta `documentacion/Postman/` son artefactos de una
ejecución histórica y no representan por sí solos el contrato completo vigente.
