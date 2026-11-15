"""Configuración del front por variables de entorno: el único lugar que las lee.

| Variable               | Para qué sirve                                                     | Por defecto                    |
|------------------------|--------------------------------------------------------------------|--------------------------------|
| OVEROL_API_URL         | URL base de la API del backend (termina en /api/)                  | http://127.0.0.1:8000/api/     |
| OVEROL_API_TIMEOUT     | Segundos de espera por petición al backend                         | 10                             |
| OVEROL_MODO_DEMO       | "1" muestra en el login las cuentas de demostración y su clave     | "0" (producción: no se muestran)|
| OVEROL_COOKIE_SECURE   | "1" fuerza el atributo Secure en la cookie de sesión (tras https)  | "0" (Secure solo si la página carga por https) |

El valor por defecto de OVEROL_API_URL solo sirve en el PC de desarrollo: en un servidor público
hay que definirlo con la URL https del backend. Las opciones de Streamlit (headless, XSRF,
barra de herramientas) están en .streamlit/config.toml y se pueden cambiar con las variables
STREAMLIT_* de Streamlit (por ejemplo STREAMLIT_SERVER_HEADLESS=false). Ver DESPLIEGUE.md.
"""

import os

_API_URL_LOCAL = "http://127.0.0.1:8000/api/"


def _flag(name):
    """True solo si la variable vale exactamente "1" (cualquier otro valor o ausencia: False)."""
    return os.environ.get(name, "0").strip() == "1"


def _int(name, default, minimum=1):
    try:
        return max(minimum, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


API_BASE_URL = (os.environ.get("OVEROL_API_URL", "").strip() or _API_URL_LOCAL).rstrip("/") + "/"
API_TIMEOUT = _int("OVEROL_API_TIMEOUT", 10)

# Administrador de Django del mismo backend (se muestra al admin como referencia)
ADMIN_URL = (API_BASE_URL[: -len("api/")] if API_BASE_URL.endswith("/api/") else API_BASE_URL) + "admin/"


def modo_demo():
    """Cuentas de demostración visibles en el login. Se lee en cada ejecución (no al importar)."""
    return _flag("OVEROL_MODO_DEMO")


def cookie_secure():
    """Cookie de sesión siempre con Secure (la app corre tras https)."""
    return _flag("OVEROL_COOKIE_SECURE")
