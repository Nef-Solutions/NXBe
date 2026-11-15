"""Utilidades comunes de las pruebas AppTest.

Cada prueba recibe como argumento la carpeta de una COPIA temporal del front (la crea
correr_pruebas.py) y habla con la imitación del backend (backend_simulado.py): ninguna
petición sale a la red y no se usa ningún archivo del front real.
"""

import os
import re
import sys
from pathlib import Path

FRONT_REAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRONT_REAL / "tests"))

import backend_simulado  # noqa: E402

backend = backend_simulado.backend
_fails = []


def preparar():
    """Valida que se corre sobre una copia, conecta el backend simulado y devuelve la carpeta."""
    if len(sys.argv) < 2:
        sys.exit("Corre las pruebas con: python tests/correr_pruebas.py")

    front = Path(sys.argv[1]).resolve()

    if front == FRONT_REAL:
        sys.exit("Corre las pruebas con correr_pruebas.py: trabajan sobre una copia del front.")

    os.environ["OVEROL_STREAMLIT_STARTED"] = "1"
    os.chdir(front)
    sys.path.insert(0, str(front))
    backend_simulado.instalar()
    return str(front)


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        _fails.append(msg)


def terminar():
    # Ninguna pantalla visible puede tocar SQLite: la copia no tiene overol.db
    check(not (Path.cwd() / "overol.db").exists(), "la app no creó overol.db (no usa SQLite)")
    print("\nRESULTADO:", "TODO OK" if not _fails else f"{len(_fails)} fallo(s)")
    sys.exit(1 if _fails else 0)


def new_app(front, email=None, run=True, **state):
    """Abre la app. Con `email`, entra con esa cuenta del backend simulado (tokens reales
    de la imitación; el usuario lo carga la app con GET /auth/me/)."""
    import streamlit
    from streamlit.testing.v1 import AppTest

    streamlit.cache_data.clear()  # el catálogo se guarda en caché 30 s
    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    if email:
        access, refresh = backend.issue_tokens(backend.by_email(email)["id"])
        at.session_state["authenticated"] = True
        at.session_state["api_access"] = access
        at.session_state["api_refresh"] = refresh
    for key, value in state.items():
        at.session_state[key] = value
    return at.run() if run else at


def plain(label):
    # Quita el contador de no leídas («🔔 Notificaciones (3)») y los espacios duros
    return re.sub(r"\s\(\d+\)$", "", label.replace(" ", " "))


def md(at):
    return " ".join(m.value for m in at.markdown)


def texts(at):
    """Todo el texto visible de avisos y leyendas (para buscar mensajes)."""
    parts = [m.value for m in at.markdown]
    for kind in ("caption", "info", "warning", "success", "error"):
        parts += [str(e.value) for e in at.get(kind)]
    return " ".join(parts)


def errors(at):
    return " ".join(str(e.value) for e in at.error)


def toasts(at):
    return " ".join(t.value for t in at.toast)


def keys(at, prefix):
    return [b.key for b in at.button if b.key and b.key.startswith(prefix)]


def nav_labels(at, nav):
    return [plain(b.label) for b in at.button if (b.key or "").startswith(f"{nav}_btn_")]


def card_ids(at):
    """Ids (del backend) de las tarjetas de profesionales en pantalla."""
    return {int(b.key.rsplit("_", 1)[1]) for b in at.button if (b.key or "").startswith("client_view_prof_")}


def calls(method=None, prefix=""):
    """Peticiones que recibió el backend simulado: [(método, ruta, cuerpo)]."""
    return [c for c in backend.calls if (not method or c[0] == method) and c[1].startswith(prefix)]
