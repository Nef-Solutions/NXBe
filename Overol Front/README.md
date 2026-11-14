# 🦺 Overol — Front-end (Streamlit)

**Proyecto de Título · DUOC UC · Equipo NXBe**

Overol es un marketplace que conecta a clientes con profesionales de oficios del hogar (gasfitería, electricidad, carpintería, pintura y otros). Este directorio contiene el **front-end**, hecho en Streamlit.

El front trabaja **siempre contra el backend Django del equipo** (carpeta `backend/`). Ya no usa SQLite: el modo local se eliminó en noviembre de 2026. La última versión con SQLite quedó en el tag `front-modo-local-final`.

La conexión a la API avanza por etapas. Las pantallas que todavía no están conectadas se ocultan de la barra (lista `PANTALLAS_PENDIENTES_API` en `core/constants.py`):

| Etapa | Estado |
|---|---|
| B · Cuentas, sesión, perfil, catálogo y perfiles públicos | ✅ conectada |
| C · Solicitudes y cobertura del profesional (días, horario y tarifa) | ✅ conectada |
| C2 · Suscripción con Webpay (sandbox), cédula, recuperación con código, oficios del backend y asistente Overil | ✅ conectada |
| D · Valoraciones y reclamos · E · Notificaciones y tickets · F · Resto del panel del profesional · G · Panel del admin | ⏳ pendientes (ocultas) |

---

## Cómo ejecutarlo

### Requisitos

- Python para el front (probado con Python 3.11).
- Las dependencias de `requirements.txt` (Streamlit y requests).

```bash
pip install -r requirements.txt
```

### Backend

Levanta el backend Django (carpeta `backend/` en la raíz del repositorio) siguiendo su propia documentación. Necesita **Python 3.12 o superior** (Django 6.1), PostgreSQL y Redis (por ejemplo con `docker compose up -d`) y un archivo `backend/.env` creado a partir de `backend/.env.example`. Después:

```powershell
python -m pip install -r documentacionequirements.txt   # incluye google-genai y transbank-sdk
python manage.py migrate
python manage.py seed_demo      # usuarios y catálogo de demostración
python manage.py runserver
```

Ya no se usa Redis: `docker compose up -d` levanta solo Postgres/PostGIS. En `backend/.env` define `PAYMENT_RESULT_URL=http://localhost:8501/` para que Webpay vuelva al front, y la clave de Gemini si quieres respuestas reales del asistente.

Por defecto el front lo busca en `http://127.0.0.1:8000/api/`; se puede cambiar con `OVEROL_API_URL`.

### Front

Todos los comandos se ejecutan desde la carpeta del front. Como su nombre tiene un espacio, va entre comillas:

```bash
cd "Overol Front"
python app.py
```

`app.py` levanta Streamlit por sí mismo y abre `http://localhost:8501`.

> Si prefieres `streamlit run app.py`, define antes la variable `OVEROL_STREAMLIT_STARTED=1`; si no, `app.py` intenta lanzar una segunda instancia.

### Scripts de demostración (Windows)

```powershell
cd "Overol Front"
powershell -ExecutionPolicy Bypass -File scripts\demo_api.ps1
```

`demo_local.ps1` es de la versión con SQLite: ya no sirve y se elimina en la etapa H. `demo_api.ps1` todavía no ejecuta `seed_demo`: córrelo a mano la primera vez.

`demo_api.ps1` exige que exista `backend/.env` (si no, se detiene y explica cómo crearlo), comprueba Docker, levanta Postgres y Redis, crea el entorno del backend si no existe, aplica migraciones, abre el servidor del backend en una ventana aparte, espera a que la API responda y arranca el front. Si algo no está listo, se detiene con un mensaje.

Por defecto usan `python` del PATH para el front y `py -3.12` para crear el entorno del backend. Se pueden ajustar con variables de entorno:

| Variable | Por defecto |
|---|---|
| `OVEROL_FRONT_PYTHON` | `python` del PATH |
| `OVEROL_BACKEND_PYTHON` | `py -3.12` (solo para crear el entorno) |
| `OVEROL_BACKEND_DIR` | `backend` junto a `app.py`; si no existe, `..\backend` (la del repositorio) |
| `OVEROL_BACKEND_VENV` | `%LOCALAPPDATA%\Overol\backend_venv` |

### Notas

- **Sesión persistente** («Mantener mi sesión iniciada», 7 días): la cookie del navegador lleva solo un identificador aleatorio. El token de renovación del backend vive en la memoria del servidor de Streamlit. Si el servidor se reinicia, hay que volver a ingresar.
- **Bloqueo:** tras 3 claves incorrectas, el backend bloquea la cuenta por 5 minutos, incluso con la clave correcta. El front muestra cuántos minutos faltan.
- **Recuperar contraseña:** en dos pasos. El backend envía un código de 6 dígitos por correo (en desarrollo se imprime en la consola de `runserver`) y con él se elige la contraseña nueva.
- **Registro de profesional:** los 66 oficios salen del catálogo del backend. Si el oficio aún no tiene especialidades, se puede registrar igual, pero no recibirá solicitudes hasta tener al menos una.
- **Suscripción:** un profesional solo aparece en el catálogo y recibe solicitudes con una suscripción vigente ($10.000 al mes, pagada con Webpay en modo de pruebas). `seed_demo` no la trae: para la demo, fija «Suscripción vigente hasta» en `/admin/` o págala desde «💳 Suscripción».
- **Webpay:** al volver de Webpay, el front consulta el estado real del pago al backend; no confía en el parámetro de la URL. Si no marcaste «Mantener mi sesión», te pide ingresar antes de mostrar el resultado.
- **Asistente Overil:** para clientes y profesionales con sesión. No guarda la conversación (solo vive en la sesión) y el texto se procesa con un servicio de Google: no escribas datos personales. Límite: 5 consultas por hora y 10 al día.
- **Nombres:** nombre y apellido solo admiten letras, espacios y apóstrofes («Ana María», no «Ana-María»).
- **Solicitudes:** para solicitar, el profesional debe tener horario (se configura en «📍 Cobertura») y al menos una especialidad en el oficio elegido. Hoy `seed_demo` no carga horario.
- **Vencimiento:** el front muestra el plazo que entrega el backend (`expires_at`). Hoy son 30 días, no 72 horas (pedido a Nefi).
- **Administración:** mientras se conecta el panel (etapa G), el admin aprueba verificaciones y gestiona cuentas en `/admin/` de Django.
- **Pruebas:** automáticas en `tests/` (contra un backend simulado) y manuales en `tests/PRUEBAS_MANUALES.md`.

---

## Usuarios de demostración

Los crea `python manage.py seed_demo` en el backend. La contraseña de todos es `OverolDemo123!`.

| Rol | Correo |
|---|---|
| Administrador | admin@demo.overol.cl |
| Cliente | cliente1@demo.overol.cl, cliente2@demo.overol.cl |
| Profesional | profesional1@demo.overol.cl, profesional2@demo.overol.cl, profesional3@demo.overol.cl |

En la pantalla de inicio de sesión hay botones que completan estos datos.

---

## Estructura

Dentro del repositorio del equipo, el front está en `Overol Front/` y el backend Django en `backend/`, una al lado de la otra:

```
NXBe/
├── backend/                Backend Django (API REST)
└── Overol Front/           Este front
```

```
Overol Front/
├── app.py                  Arranque, cabecera y enrutamiento por rol
├── style.css               Estilos de la aplicación
├── requirements.txt        Dependencias del front
├── .streamlit/
│   └── config.toml         Tema claro, color principal ámbar
├── core/
│   ├── constants.py        Configuración, comunas, oficios, roles, estados y pantallas pendientes de la API
│   ├── security.py         Hash PBKDF2 y validación de RUT, correo, teléfono y contraseña
│   ├── database.py         SQLite de la versión anterior: solo lo usan las pantallas aún ocultas (se elimina en la etapa H)
│   ├── session.py          Usuario actual (/auth/me/) y sesión persistente de 7 días (token en memoria del servidor)
│   ├── api_client.py       Cliente HTTP del backend (JWT, renovación del token, errores)
│   └── catalog_api.py      Catálogo y perfiles públicos desde la API
├── ui/
│   ├── components.py       Componentes visuales, carga del CSS y mensajes flash
│   ├── profile.py          Perfiles con estructura tipo LinkedIn
│   └── hold_button/        Botón de confirmación por presión sostenida
├── views/
│   ├── home.py             Portada
│   ├── about.py            «Quiénes somos»
│   ├── visitor.py          Navegación sin iniciar sesión
│   ├── auth.py             Inicio de sesión, registro y recuperación de contraseña
│   ├── shared.py           Perfil personal, perfil del profesional y barra lateral
│   ├── client.py           Vistas del cliente
│   ├── professional.py     Vistas del profesional
│   └── admin.py            Vistas del administrador
├── tests/                 Pruebas AppTest (backend simulado) y pruebas manuales
└── scripts/
    ├── demo_local.ps1      Obsoleto (versión con SQLite)
    └── demo_api.ps1        Arranque del backend y del front en modo api
```

> Prototipo académico: las credenciales de demostración y los datos de ejemplo son ficticios y no deben usarse en producción.
