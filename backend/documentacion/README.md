# Documentación del proyecto Overol

## Propósito

Overol conecta clientes con profesionales de oficios para solicitar visitas, coordinar servicios, evaluar el resultado y gestionar posventa.

## Estado actual

El backend está construido como un monolito modular con Django, Django REST Framework y PostgreSQL/PostGIS preparado para desarrollo local.

Actualmente existe código funcional para:

- Registro, inicio y cierre de sesión.
- Recuperación y cambio de contraseña.
- Estados de cuenta y bloqueo temporal después de tres intentos fallidos.
- Verificación de profesionales y mensajes de seguimiento.
- Catálogo de zonas, oficios, especialidades y profesionales.
- Perfiles públicos de profesionales verificados.
- Solicitudes de visita y transiciones del servicio.
- Calificaciones, promedio de reputación y reseñas.
- Reclamos de posventa y tickets de soporte.
- Notificaciones internas.
- Centro de Desarrollo Profesional y avance de contenidos.
- Administración y bitácora de acciones.
- Vencimiento de solicitudes pendientes después de 30 días.

## Fuera del alcance actual

Por decisión del proyecto todavía no se implementan:

- Suscripciones ni pasarela de pago.
- Chatbot de diagnóstico o integración con IA.
- Geolocalización real, mapas, coordenadas y radios de cobertura.
- Evidencias no relacionadas con código, como videos, revisión del Product Owner o despliegue.

## Puesta en marcha

1. Levantar PostgreSQL y Redis con Docker:

   ```powershell
   docker compose up -d
   ```

2. Instalar dependencias:

   ```powershell
   python -m pip install -r documentacion/requirements.txt
   ```

3. Aplicar migraciones y validar el proyecto:

   ```powershell
   python manage.py migrate
   python manage.py check
   python manage.py test
   ```

4. Iniciar el servidor:

   ```powershell
   python manage.py runserver
   ```

La API queda disponible en `http://127.0.0.1:8000/`.

## Documentos relacionados

- [Resumen del estado frente al Definition of Done](estado-dod.md)
- [Evaluación de la Definition of Done ajustada](evaluacion-dod-ajustada.md)
- [Arquitectura del backend](arquitectura.md)
- [Operación de Docker](docker.md)
- [Diagrama de base de datos](base-de-datos.md)
- [Contrato de API](api.md)
- [Acta de pruebas](pruebas.md)
- [Instalación en otro computador](instalacion.md)
- [Dependencias Python](requirements.txt)