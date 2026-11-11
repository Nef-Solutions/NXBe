# Suites pendientes de reescribir contra la API

Estas suites prueban pantallas que todavía leen o escriben en SQLite y que hoy están **ocultas** de la barra (`PANTALLAS_PENDIENTES_API` en `core/constants.py`).
Se guardan como referencia de lo que cada pantalla debe cumplir. **No se corren**: usan el `comun.py` antiguo, que ya no existe.

| Suite | Etapa que la reescribe |
|---|---|
| `prueba_indicadores_reclamos.py` | D · valoraciones y reclamos (reclamos), G (indicadores) |
| `prueba_notificaciones.py`, `prueba_tickets.py` | E · notificaciones y tickets |
| `prueba_verificacion.py`, `prueba_cifrado.py`, `prueba_admin_panel.py` | F y G · profesional y admin |

Al conectar una pantalla, se reescribe su suite contra `backend_simulado.py` y se mueve a `tests/`.
La versión completa con SQLite queda en el tag `front-modo-local-final`.
