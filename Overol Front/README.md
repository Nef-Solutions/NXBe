# 🦺 Overol — Front-end (Streamlit)

**Proyecto de Título · DUOC UC · Equipo NXBe**

Overol es un marketplace que conecta a clientes con profesionales de oficios del hogar (gasfitería, electricidad, carpintería, pintura y otros). Este directorio contiene el **front-end**, hecho en Streamlit.

El front funciona de dos maneras:

| Modo | Comportamiento |
|---|---|
| `local` (por defecto) | Todo funciona con una base SQLite propia (`overol.db`), sin depender de ningún servidor. Ideal para demostraciones. |
| `api` | Inicio de sesión, registro y datos personales (teléfono, dirección y comuna) usan el backend Django del equipo. El resto de las funciones sigue en SQLite mientras se completa la integración. |

El modo se elige con la variable de entorno `OVEROL_BACKEND`.

---

## Cómo ejecutarlo

### Requisitos

- Python para el front (probado con Python 3.11).
- Las dependencias de `requirements.txt` (Streamlit y requests).

```bash
pip install -r requirements.txt
```

### Modo local

Todos los comandos se ejecutan desde la carpeta del front. Como su nombre tiene un espacio, va entre comillas:

```bash
cd "Overol Front"
python app.py
```

`app.py` levanta Streamlit por sí mismo y abre `http://localhost:8501`. La base de datos `overol.db` y la carpeta `documentos_verificacion/` se crean solas la primera vez, con datos de demostración.

> Si prefieres `streamlit run app.py`, define antes la variable `OVEROL_STREAMLIT_STARTED=1`; si no, `app.py` intenta lanzar una segunda instancia.

### Modo api (conectado al backend)

1. Levanta el backend Django (carpeta `backend/` en la raíz del repositorio) siguiendo su propia documentación. Necesita **Python 3.12 o superior** (Django 6.1), PostgreSQL y Redis (por ejemplo con `docker compose up -d`) y un archivo `backend/.env` creado a partir de `backend/.env.example`. Por defecto debe responder en `http://127.0.0.1:8000/api/`.
2. Arranca el front en modo api:

```powershell
# PowerShell
cd "Overol Front"
$env:OVEROL_BACKEND = "api"
$env:OVEROL_API_URL = "http://127.0.0.1:8000/api/"   # opcional: es el valor por defecto
python app.py
```

```bash
# Bash
cd "Overol Front"
OVEROL_BACKEND=api OVEROL_API_URL=http://127.0.0.1:8000/api/ python app.py
```

### Scripts de demostración (Windows)

```powershell
cd "Overol Front"
powershell -ExecutionPolicy Bypass -File scripts\demo_local.ps1   # modo local
powershell -ExecutionPolicy Bypass -File scripts\demo_api.ps1     # modo api
```

`demo_api.ps1` exige que exista `backend/.env` (si no, se detiene y explica cómo crearlo), comprueba Docker, levanta Postgres y Redis, crea el entorno del backend si no existe, aplica migraciones, abre el servidor del backend en una ventana aparte, espera a que la API responda y arranca el front. Si algo no está listo, se detiene con un mensaje.

Por defecto usan `python` del PATH para el front y `py -3.12` para crear el entorno del backend. Se pueden ajustar con variables de entorno:

| Variable | Por defecto |
|---|---|
| `OVEROL_FRONT_PYTHON` | `python` del PATH |
| `OVEROL_BACKEND_PYTHON` | `py -3.12` (solo para crear el entorno) |
| `OVEROL_BACKEND_DIR` | `backend` junto a `app.py`; si no existe, `..\backend` (la del repositorio) |
| `OVEROL_BACKEND_VENV` | `%LOCALAPPDATA%\Overol\backend_venv` |

### Notas del modo api

- Al iniciar sesión se crea en SQLite una copia local del usuario, enlazada por correo, para que las pantallas que aún no están conectadas sigan funcionando.
- Los usuarios de demostración locales solo sirven si también existen en el backend.
- La recuperación de contraseña está oculta en este modo.
- Nombre y apellido solo admiten letras, espacios y apóstrofes («Ana María», no «Ana-María»).
- Tras 3 claves incorrectas el backend bloquea la cuenta por un tiempo, incluso con la clave correcta.
- Con «Mantener mi sesión iniciada», el token de renovación del backend se guarda en el SQLite local para recuperar la sesión al recargar la página. Es una limitación aceptada del prototipo: en producción debe cifrarse o reemplazarse por una cookie segura.

---

## Usuarios de demostración (modo local)

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@overol.cl | admin123 |
| Cliente | cliente@overol.cl | cliente123 |
| Profesional | carlos@overol.cl | profesional123 |

En la pantalla de inicio de sesión hay botones que completan estos datos. Al entrar por primera vez, cliente y profesional deben completar su perfil personal.

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
│   ├── constants.py        Configuración, comunas, oficios, roles, estados y modo local/api
│   ├── security.py         Hash PBKDF2 y validación de RUT, correo, teléfono y contraseña
│   ├── database.py         SQLite: tablas, migraciones automáticas, datos demo y consultas
│   ├── session.py          Sesión persistente de 7 días (cookie con token con hash)
│   └── api_client.py       Cliente HTTP del backend (JWT, renovación del token, errores)
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
│   ├── client.py           Vistas del cliente y asistente
│   ├── professional.py     Vistas del profesional
│   └── admin.py            Vistas del administrador
└── scripts/
    ├── demo_local.ps1      Arranque en modo local
    └── demo_api.ps1        Arranque del backend y del front en modo api
```

> Prototipo académico: la base local, las credenciales de demostración y los datos de ejemplo son ficticios y no deben usarse en producción.
