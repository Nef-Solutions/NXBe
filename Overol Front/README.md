# 🦺 Overol — Front-end (Streamlit)

**Proyecto de Título · DUOC UC · Equipo NXBe**

Overol es un marketplace que conecta a clientes con profesionales de oficios del hogar. Este directorio contiene el **front-end**, hecho en Streamlit. Todos los datos vienen del **backend Django del equipo** (carpeta `backend/` del repositorio), a través de su API REST con JWT. El front no guarda datos propios.

> La versión anterior, que funcionaba sola con SQLite, quedó en el tag `front-modo-local-final`.

---

## Cómo ejecutarlo

### Requisitos

- **Front:** Python 3.11 o superior, con las dependencias de `requirements.txt` (Streamlit y requests).
- **Backend:** Python 3.12 o superior (Django 6.1), Docker Desktop para Postgres/PostGIS y un archivo `backend/.env` creado desde `backend/.env.example`.

```bash
pip install -r requirements.txt
```

### Con el script (Windows)

```powershell
cd "Overol Front"
powershell -ExecutionPolicy Bypass -File scripts\demo_api.ps1             # backend + front
powershell -ExecutionPolicy Bypass -File scripts\demo_api.ps1 -DemoListo  # además prepara a los profesionales de demo
```

El script:
1. Comprueba Docker y levanta Postgres/PostGIS con `docker compose up -d`.
2. Crea el entorno del backend si no existe (fuera de la carpeta `backend/`) e instala sus dependencias si faltan.
3. Aplica las migraciones y carga los datos de demostración (`seed_demo`).
4. Abre el servidor del backend en una ventana aparte, espera a que la API responda y arranca el front en `http://localhost:8501`.

Si algo no está listo, se detiene con un mensaje.

Con `-DemoListo`, deja a `profesional1` a `profesional3@demo.overol.cl` con horario (09:00–18:00) y un mes de suscripción. Sin eso, el catálogo queda vacío, porque `seed_demo` todavía no lo hace.

| Variable opcional | Por defecto |
|---|---|
| `OVEROL_FRONT_PYTHON` | `python` del PATH |
| `OVEROL_BACKEND_PYTHON` | `py -3.12` (solo para crear el entorno del backend) |
| `OVEROL_BACKEND_DIR` | `backend` junto a `app.py`; si no existe, `..\backend` (la del repositorio) |
| `OVEROL_BACKEND_VENV` | `%LOCALAPPDATA%\Overol\backend_venv` |

### A mano

```powershell
# Backend (carpeta backend del repositorio)
docker compose up -d
python -m pip install -r documentacion\requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000

# Front (otra ventana, carpeta "Overol Front")
python app.py
```

`app.py` levanta Streamlit por sí mismo. Si prefieres `streamlit run app.py`, define antes `OVEROL_STREAMLIT_STARTED=1`. El front busca la API en `http://127.0.0.1:8000/api/`; se cambia con `OVEROL_API_URL`.

### Variables del backend que importan al front (`backend/.env`)

- **`PAYMENT_RESULT_URL=http://localhost:8501/`:** es la dirección a la que vuelve Webpay después de un pago. El valor por defecto apunta a otro front.
- **Clave de Gemini:** solo hace falta para las respuestas reales del asistente Overil. Sin ella, el asistente avisa que no está disponible y todo lo demás funciona.

---

## Usuarios de demostración

Los crea `python manage.py seed_demo`. La contraseña de todos es `OverolDemo123!`. En la pantalla de ingreso hay botones que completan estos datos.

| Rol | Correo |
|---|---|
| Administrador | admin@demo.overol.cl |
| Cliente | cliente1@demo.overol.cl, cliente2@demo.overol.cl |
| Profesional | profesional1@demo.overol.cl, profesional2@demo.overol.cl, profesional3@demo.overol.cl |

---

## Qué puede hacer cada rol

| Rol | Pantallas |
|---|---|
| Visitante | Portada con cifras y destacados, catálogo con tarjetas anónimas, perfil público sin datos personales, registro e ingreso |
| Cliente | Buscar profesionales (oficio, especialidad, comuna y palabra clave), solicitar visita, Mis solicitudes (cancelar, confirmar, pagar la visita con Webpay, evaluar, reclamar, soporte), Mis reclamos, Notificaciones, Asistente, Mi perfil |
| Profesional | Solicitudes (aceptar, rechazar con motivo, cancelar, finalizar, calificar al cliente, soporte), Notificaciones, Mi perfil (datos, vista pública con reputación, oficios), Cobertura (días, horario, comunas, tarifa), Suscripción con Webpay, Verificación (cédula y mensajes), Reclamos, Desarrollo profesional, Asistente |
| Administrador | Indicadores de reclamos y tickets, Verificación (ver la cédula, aprobar o rechazar), estado de cuentas, Reclamos (resolver) y Bandeja de soporte |

### Reglas que conviene saber

- **Sesión persistente** («Mantener mi sesión iniciada», 7 días): la cookie lleva solo un identificador aleatorio. El token de renovación del backend vive en la memoria del servidor de Streamlit. Si el servidor se reinicia, hay que volver a ingresar.
- **Bloqueo:** tras 3 claves incorrectas, el backend bloquea la cuenta 5 minutos. El front muestra cuántos faltan.
- **Recuperar la contraseña:** en dos pasos. El backend envía un código de 6 dígitos (en desarrollo se imprime en la consola de `runserver`) y con él se elige la contraseña nueva.
- **Profesionales en el catálogo:** solo aparecen y reciben solicitudes si están **verificados** y con **suscripción vigente** ($10.000 al mes, pagada con Webpay en modo de pruebas).
  - Para solicitar una visita, además deben tener horario y al menos una especialidad en el oficio elegido.
  - Hoy solo Gasfitería, Electricidad y Cerrajería tienen especialidades en el backend.
- **Webpay:** al volver de Webpay, el front consulta el estado real del pago; no confía en el parámetro de la URL. Si no marcaste «Mantener mi sesión», te pide ingresar antes de mostrar el resultado.
- **Asistente Overil:** para clientes y profesionales con sesión. La conversación vive solo en la sesión. El texto se procesa con un servicio de Google, así que no hay que escribir datos personales. Límite: 5 consultas por hora y 10 al día.
- **Vencimiento de solicitudes:** el front muestra el plazo que entrega el backend (`expires_at`). Hoy son 30 días, no 72 horas.
- **Panel del admin:** el backend no entrega la lista de verificaciones pendientes ni de usuarios, así que el panel pide el id (se ve en `/admin/` de Django). Moderación de reseñas, contenidos del centro profesional y bitácora no tienen endpoint: están ocultas (`PANTALLAS_PENDIENTES_API`) y se hacen en `/admin/`.
- **Nombres:** nombre y apellido solo admiten letras, espacios y apóstrofes («Ana María», no «Ana-María»).

Lo que falta en el backend está detallado en `PEDIDO_BACKEND_PARA_NEFI.md`, un documento del equipo que no está en el repositorio.

---

## Estructura

```
Overol Front/
├── app.py                  Arranque, sesión, vuelta de Webpay y enrutamiento por rol
├── style.css               Estilos
├── requirements.txt        Dependencias del front
├── .streamlit/config.toml  Tema claro, color principal ámbar
├── core/
│   ├── constants.py        Configuración, comunas, oficios destacados, roles y pantallas sin endpoint
│   ├── api_client.py       Cliente HTTP del backend (JWT con renovación, errores legibles, archivos)
│   ├── session.py          Usuario actual (/auth/me/) y sesión persistente de 7 días
│   ├── catalog_api.py      Catálogo, perfiles públicos y búsqueda por palabra clave
│   ├── requests_api.py     Solicitudes, disponibilidad, valoraciones y reclamos
│   └── security.py         Validaciones de RUT, correo, teléfono y contraseña
├── ui/
│   ├── components.py       Componentes visuales, notificaciones, soporte y mensajes flash
│   ├── profile.py          Perfiles con estructura tipo LinkedIn
│   └── hold_button/        Botón de confirmación por presión sostenida
├── views/
│   ├── home.py · about.py · visitor.py
│   ├── auth.py             Ingreso, registro y recuperación de contraseña
│   ├── shared.py           Perfil personal, perfil del profesional y solicitud de visita
│   ├── client.py           Vistas del cliente
│   ├── professional.py     Vistas del profesional
│   ├── admin.py            Vistas del administrador
│   ├── payments.py         Webpay: formulario de pago y vuelta
│   └── assistant.py        Asistente Overil
├── tests/                  Pruebas AppTest con un backend simulado y pruebas manuales
└── scripts/demo_api.ps1    Arranque de la demo
```

## Pruebas

- **Automáticas:** `python tests/correr_pruebas.py`. Usan una imitación en memoria del backend (`tests/backend_simulado.py`), así que no hace falta tenerlo encendido. Detalle en `tests/README.md`.
- **Manuales contra el backend real:** `tests/PRUEBAS_MANUALES.md`.

> Prototipo académico: las credenciales de demostración y los datos de ejemplo son ficticios y no deben usarse en producción. Webpay funciona en modo de pruebas (sandbox).
