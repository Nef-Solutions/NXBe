# Despliegue del front de Overol

Cómo publicar el front (Streamlit) en un servidor. El backend Django se despliega aparte; lo que debe preparar el equipo de backend está en su propia documentación.

> Este documento no contiene claves. Nunca pongas valores secretos en el repositorio, en la imagen ni en este archivo: se entregan como variables de entorno del servidor.

---

## 1. Variables de entorno del front

Todas se leen en `core/config.py`.

| Variable | Para qué sirve | Ejemplo | Por defecto |
|---|---|---|---|
| `OVEROL_API_URL` | URL base de la API del backend, terminada en `/api/` | `https://api.overol.cl/api/` | `http://127.0.0.1:8000/api/` (solo sirve en el PC de desarrollo) |
| `OVEROL_API_TIMEOUT` | Segundos de espera por cada petición al backend | `10` | `10` |
| `OVEROL_MODO_DEMO` | `1` muestra en el login las cuentas de demostración y su clave. **En un servidor público debe quedar en `0`** | `0` | `0` |
| `OVEROL_COOKIE_SECURE` | `1` fuerza el atributo `Secure` en la cookie de sesión. Úsalo cuando la app esté tras https | `1` | `0` (igual se agrega `Secure` si la página carga por https) |
| `OVEROL_STREAMLIT_STARTED` | Evita que `app.py` lance una segunda instancia de Streamlit. La imagen ya la define | `1` | — |

Opciones de Streamlit (ya vienen en `.streamlit/config.toml` para producción; se pueden cambiar con variables `STREAMLIT_*`):

| Ajuste en `config.toml` | Valor de producción | Para desarrollo |
|---|---|---|
| `server.headless` | `true` (no abre navegador) | `STREAMLIT_SERVER_HEADLESS=false` |
| `server.enableXsrfProtection` / `server.enableCORS` | `true` | No cambiar |
| `browser.gatherUsageStats` | `false` (sin telemetría) | — |
| `client.toolbarMode` | `viewer` (sin opciones de desarrollador ni botón «Deploy») | `STREAMLIT_CLIENT_TOOLBAR_MODE=developer` |
| `client.showErrorDetails` | `none` (el detalle de los errores queda en la consola del servidor) | `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=full` |

---

## 2. Construir y correr el contenedor

Desde la carpeta `Overol Front`:

```bash
docker build -t overol-front .

docker run -d --name overol-front -p 8501:8501 \
  -e OVEROL_API_URL=https://api.overol.cl/api/ \
  -e OVEROL_COOKIE_SECURE=1 \
  -e OVEROL_MODO_DEMO=0 \
  --restart unless-stopped \
  overol-front
```

- La imagen usa Python 3.11, instala `requirements.txt` (versiones fijas, las mismas de las pruebas), corre con un usuario sin privilegios y expone el puerto **8501**.
- Tiene un *healthcheck* en `http://127.0.0.1:8501/_stcore/health`.
- No incluye pruebas, scripts, `.git`, bases locales, documentos subidos, `.env`, claves ni `__pycache__` (ver `.dockerignore`).
- **Streamlit Community Cloud** (la opción gratuita elegida) no usa esta imagen: instala `requirements.txt` y ejecuta `app.py` directamente. Las variables de la sección 1 se escriben como *secrets* en su panel (`core/config.py` las lee de las variables de entorno o, si no están, de `st.secrets`). Paso a paso en [`HOSTING.md`](../HOSTING.md).
- Para probar en local esta misma imagen junto al backend, sin el modo desarrollo, desde la raíz del repositorio: `docker compose -f docker-compose.yml up --build` (ver [`DOCKER.md`](../DOCKER.md)).

### Proxy https delante

El contenedor habla http. Delante debe ir un proxy inverso con https (Nginx, Caddy, Traefik o el balanceador del proveedor) que:

- Redirija todo el tráfico http a https.
- **Permita WebSocket**: Streamlit usa `/_stcore/stream`. Sin WebSocket la página queda cargando.
- Envíe el tráfico de un mismo usuario siempre a la **misma instancia** (ver 4).

---

## 3. Qué URL del backend usar

- `OVEROL_API_URL` es la URL **https** pública del backend, terminada en `/api/` (por ejemplo `https://api.overol.cl/api/`).
- Las peticiones a la API las hace el **servidor** del front, no el navegador del usuario. Por eso basta con que el contenedor llegue al backend.
- Aun así, el backend debe ser público y estar en https: Webpay redirige el navegador del usuario a `TRANSBANK_RETURN_URL` del backend, y este lo devuelve a `PAYMENT_RESULT_URL`.
- En el `.env` del backend (los valores los define el equipo de backend):
  - `PAYMENT_RESULT_URL` debe ser la URL https del front (por ejemplo `https://overol.cl/`).
  - `TRANSBANK_RETURN_URL` debe ser `https://<dominio-del-backend>/api/payments/transbank/return/`.

**El front y el backend deben estar ambos bajo https.** Sin https, las contraseñas y los tokens viajan en claro y el navegador no guardará la cookie con `OVEROL_COOKIE_SECURE=1`.

---

## 4. Sesiones: viven en la memoria del servidor

- La cookie `overol_session` solo lleva un identificador aleatorio (`SameSite=Lax`, `Secure` tras https), sin datos personales.
- El token de renovación del backend se guarda en la **memoria del proceso de Streamlit**.
- **Un reinicio del contenedor cierra todas las sesiones**: los usuarios deben volver a iniciar sesión. Lo mismo pasa al publicar una versión nueva.
- Con más de una instancia, cada una tiene su propia memoria. Usa **una sola instancia** o sesiones pegajosas (*sticky sessions*) en el proxy.

---

## 5. Comprobar que quedó bien

- [ ] `https://<dominio-del-front>/_stcore/health` responde `ok`.
- [ ] La portada carga por https, sin avisos de certificado, y muestra profesionales (el front llega al backend).
- [ ] El login **no** muestra cuentas de demostración ni ninguna clave.
- [ ] Arriba a la derecha no aparece el botón «Deploy» ni las opciones de desarrollador.
- [ ] Al iniciar sesión con «Mantener mi sesión», en las herramientas del navegador la cookie `overol_session` tiene `Secure` y `SameSite=Lax`.
- [ ] Al recargar la página, la sesión se mantiene.
- [ ] Un error provocado (por ejemplo, el backend apagado) muestra un mensaje legible, sin el detalle técnico.
- [ ] Si se usa Webpay: un pago de suscripción de prueba vuelve al front y muestra el estado real.

---

## 6. Límites conocidos

- **Sesiones en memoria:** un reinicio cierra las sesiones; con varias instancias hacen falta sesiones pegajosas.
- **Webpay:** está en modo de pruebas (sandbox) hasta que el backend configure las credenciales de producción. Overol solo cobra la suscripción del profesional; no hay pago de visitas.
- **Asistente Overil:** depende de la clave de Gemini del backend. Sin ella, avisa que no está disponible. Tiene límite de consultas por hora y por día.
- **Panel del administrador:** no hay listados de verificaciones pendientes ni de usuarios en la API, así que se trabaja con el id. Moderación, contenidos y bitácora se hacen en el `/admin/` de Django.
- **Vencimiento de solicitudes:** lo fija el backend (hoy 30 días).
- **Cuentas de demostración:** si en el servidor existen las cuentas de `seed_demo`, su clave es pública (está en el repositorio). En un servidor público no se debe ejecutar `seed_demo`, o hay que cambiar esas claves.
- **No probado en un servidor real** ni con un proxy https: la imagen se construyó y las pruebas automáticas pasan, pero el despliegue completo queda por verificar con la lista del punto 5.
