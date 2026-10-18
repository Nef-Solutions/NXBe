# Resumen del estado frente al DoD

Este documento es un resumen ejecutivo. La evaluación completa está en [evaluacion-dod-ajustada.md](evaluacion-dod-ajustada.md).

## Cómo leer los estados

- **Parcial:** existe código funcional, pero falta completar una o más reglas, pruebas, controles o pantallas.
- **Pendiente:** todavía no existe una implementación funcional.
- **Fuera de alcance:** el equipo decidió no construirlo en esta etapa.
- **Fase 2:** no se exige ahora; el código existente relacionado se conserva.

## Resumen

| Estado | Cantidad | Significado |
| :--- | ---: | :--- |
| Parcial | 35 | Hay una base funcional, pero aún no cumple todo el DoD. |
| Pendiente | 3 | Aún no hay una solución funcional. |
| Fuera de alcance | 8 | Se decidió postergarlo. |
| Completo | 0 | Ninguna historia cumple todos los criterios técnicos y de negocio. |

## Funcionalidad disponible

- Cuentas, sesiones, privacidad, RUT y estados de usuario.
- Verificación profesional y mensajes al administrador.
- Catálogo y búsqueda de profesionales verificados.
- Oficios, experiencia y certificaciones declaradas.
- Solicitudes, aceptación, rechazo, cancelación y finalización de visitas.
- Calificaciones, reseñas, posventa y tickets.
- Notificaciones internas.
- Centro de Desarrollo Profesional.
- Django Admin y bitácora administrativa.

## Historias pendientes dentro del alcance

- **4.41 Recuperación de datos:** recuperar y reasignar información de perfiles eliminados.
- **4.43 Cierre forzoso:** cerrar un servicio excepcionalmente desde administración.
- **4.45 Indicadores:** mostrar métricas de uso en un panel administrativo.

## Fuera de alcance

- Suscripciones y pasarela de pago.
- Chatbot e inteligencia artificial.
- Geolocalización real, mapas, coordenadas, radios y cobertura real.
- Requisitos que no son código, como videos, aprobación del Product Owner y despliegue.

## Validaciones registradas

- `python manage.py check` aprobado.
- Migraciones aplicadas correctamente.
- 13 pruebas unitarias aprobadas.
- Comando `python manage.py expire_visit_requests` ejecutado correctamente.
- Compilación sintáctica aprobada.

El detalle de las pruebas está en [pruebas.md](pruebas.md).
