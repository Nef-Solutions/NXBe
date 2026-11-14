# Pruebas del front (AppTest)

Pruebas automáticas de las pantallas de Streamlit con `streamlit.testing.v1.AppTest`.
Hacen clic en los botones por su `key` y revisan lo que queda en pantalla y lo que recibió el backend.

## Cómo correrlas

Desde la carpeta `Overol Front`, con el Python que tiene Streamlit:

```powershell
python tests/correr_pruebas.py                  # todas
python tests/correr_pruebas.py login busqueda   # solo algunas
python tests/correr_pruebas.py -v               # muestra cada verificación
```

Al final aparece `TODO OK` o la lista de verificaciones que fallaron.
Requisitos: `pip install -r requirements.txt`. **No hace falta tener el backend encendido.**

## Backend simulado

`backend_simulado.py` es una imitación en memoria del backend Django.
Reemplaza `requests.request`, así que ninguna petición sale a la red.

- **Formato:** responde con los mismos códigos y formatos que el backend real de `origin/main`, leídos de su código:
  - 401 por credenciales incorrectas.
  - 429 con `retry_after`.
  - 400 con los errores por campo.
  - 204 al cerrar sesión.
  - Tokens que rotan y quedan anulados.
  - Catálogo paginado.
  - Disponibilidad del profesional.
  - Solicitudes con la misma validación del backend: 400 por campo o `non_field_errors`, 403 sin permiso y 409 en una transición inválida.
  - Suscripción obligatoria para aparecer en el catálogo y recibir solicitudes, pagos con Webpay (`backend.webpay_return(token, ...)` simula la vuelta), cédula por multipart, mensajes de verificación, asistente (429 y 503) y recuperación con código.
- **Datos de demostración:** los mismos correos de `seed_demo` (contraseña `OverolDemo123!`), más un profesional pendiente de verificación y un cliente sin teléfono ni dirección.
- **Interruptores:**
  - `backend.caido = True` simula el backend apagado.
  - `backend.expire_access()` vence los tokens de acceso.
  - `backend.page_size_max` achica las páginas.
  - `backend.add_visit(...)` y `backend.age_visit(...)` preparan solicitudes.
  - `backend.before_action` cambia una solicitud justo antes de una acción, para simular una carrera (409).
- **Registro:** `backend.calls` guarda cada petición (método, ruta y cuerpo) para revisar qué envió el front.

Es una imitación: **no reemplaza las pruebas contra el backend real** (ver `PRUEBAS_MANUALES.md`).

## Qué protege el corredor

- **Copia del front:** cada suite trabaja sobre una copia temporal, que se borra al terminar.
- **Sin SQLite:** la copia no lleva `overol.db`, claves, `.env` ni documentos. Cada suite termina revisando que la app **no haya creado `overol.db`**, para detectar cualquier pantalla visible que todavía use SQLite.
- **Uso:** no corras un archivo `prueba_*.py` directo, porque se niega a correr sin una copia.

## Suites

| Archivo | Qué revisa |
|---|---|
| `prueba_login.py` | 401, bloqueo 429 del backend sin contador local, sesión persistente (identificador en la cookie, token en la memoria del servidor, restaurar al recargar, rotación, cerrar sesión, reinicio del servidor), acceso vencido, cuenta suspendida |
| `prueba_registro_perfil.py` | Registro de cliente y profesional (oficio inexistente, contraseña débil, correo repetido), completar perfil, Mi perfil por `PATCH /auth/me/`, cambio y recuperación de contraseña |
| `prueba_navegacion.py` | Barra de los 4 roles con las pantallas pendientes ocultas, estado de verificación, aviso del admin de Django, cerrar sesión |
| `prueba_busqueda.py` | Palabra clave sin distinguir mayúsculas ni tildes, varias palabras, filtros, «Limpiar búsqueda», visitante sin nombres |
| `prueba_catalogo.py` | Filtros enviados al backend, paginación, perfil público, formulario de solicitud, enlace directo, portada, backend caído |
| `prueba_solicitudes.py` | Formulario (especialidad, dirección de `/me`, errores 400 legibles), Mis solicitudes y Solicitudes con pestañas, aceptar, rechazar con motivo, cancelar de ambos lados, finalizar y confirmar en los dos órdenes, contacto, 409, vencida y «Cerrada por Overol» |
| `prueba_suscripcion_verificacion.py` | Suscripción y Webpay (formulario POST con `token_ws`, vuelta sin confiar en `?status=`, con y sin sesión), catálogo según la suscripción, cédula y mensajes de verificación |
| `prueba_asistente.py` | Asistente para cliente y profesional, historial en la sesión, aviso de datos personales, 429 y 503 |
| `prueba_valoraciones_reclamos.py` | Evaluar al profesional y al cliente (400 «ya calificado»), reclamos (crear, responder, mediación, resolución) y pago de visitas con Webpay |
| `prueba_cobertura.py` | Disponibilidad con días en nombre completo, horario, comunas y tarifa; validaciones; el cliente ve el horario nuevo |

`comun.py` reúne las utilidades: entrar con una cuenta del backend simulado, `check`, búsqueda de textos y peticiones.

## Suites pendientes

`pendientes_api/` guarda las suites de la época de SQLite para las pantallas que hoy están ocultas (`PANTALLAS_PENDIENTES_API`).
No se corren. Cada etapa reescribe las suyas contra el backend simulado y las devuelve a esta carpeta (ver su README).

## Límites conocidos

- **No es un navegador.** AppTest no muestra el diseño: los estilos, el CSS y la barra fija hay que mirarlos a mano.
- **Cookies:** AppTest no maneja cookies. Las pruebas reemplazan `read_session_cookie` y capturan el script que escribe la cookie.
- **Subida de archivos:** AppTest no sube archivos. `prueba_suscripcion_verificacion.py` reemplaza el selector de archivos por uno que entrega archivos preparados.
- **Webpay:** no se abre Webpay. Se revisa el formulario que se enviaría y se simula la vuelta con `backend.webpay_return`.
- **Botón de mantener presionado:** es un componente propio que AppTest no puede pulsar. `prueba_solicitudes.py` lo reemplaza por uno que confirma, para probar el resto de la cancelación del cliente.
