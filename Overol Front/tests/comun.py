"""Utilidades comunes de las pruebas AppTest.

Cada prueba recibe como argumento la carpeta de una COPIA temporal del front (la crea
correr_pruebas.py), así nunca toca el overol.db real ni la clave real de los documentos.
"""

import os
import re
import sys
from pathlib import Path

FRONT_REAL = Path(__file__).resolve().parents[1]
_fails = []


def preparar():
    """Valida que se corre sobre una copia y deja listo el entorno. Devuelve la carpeta de la copia."""
    if len(sys.argv) < 2:
        sys.exit("Corre las pruebas con: python tests/correr_pruebas.py")

    front = Path(sys.argv[1]).resolve()

    if front == FRONT_REAL:
        sys.exit("Estas pruebas modifican la base: córrelas con correr_pruebas.py, que usa una copia.")

    if not os.environ.get("OVEROL_CLAVE_DOCUMENTOS_ARCHIVO") or os.environ.get("OVEROL_CLAVE_DOCUMENTOS"):
        sys.exit("Falta la clave de prueba: córrelas con correr_pruebas.py.")

    os.environ["OVEROL_STREAMLIT_STARTED"] = "1"
    os.chdir(front)
    sys.path.insert(0, str(front))
    return str(front)


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        _fails.append(msg)


def terminar():
    print("\nRESULTADO:", "TODO OK" if not _fails else f"{len(_fails)} fallo(s)")
    sys.exit(1 if _fails else 0)


def new_app(front, user_id=None):
    """Abre la app con la sesión de `user_id` ya iniciada (None = visitante)."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    if user_id:
        at.session_state["authenticated"] = True
        at.session_state["user_id"] = user_id
    return at.run()


def usuarios(front):
    """Arranca la app una vez (crea la base si falta) y devuelve los ids de los usuarios demo."""
    new_app(front)
    from core import database as db

    conn = db.get_connection()
    ids = {
        row["email"]: row["id"]
        for row in conn.execute("SELECT id, email FROM users").fetchall()
    }
    conn.close()
    return {
        "admin": ids["admin@overol.cl"],
        "cliente": ids["cliente@overol.cl"],
        "carlos": ids["carlos@overol.cl"],
        "daniel": ids["daniel@overol.cl"],
        "marcelo": ids["marcelo@overol.cl"],
    }


def plain(label):
    # Quita el contador de no leídas («🔔 Notificaciones (3)») y los espacios duros
    return re.sub(r"\s\(\d+\)$", "", label.replace(" ", " "))


def md(at):
    return " ".join(m.value for m in at.markdown)


def texts(at):
    """Todo el texto visible de avisos y leyendas (para buscar mensajes)."""
    parts = [m.value for m in at.markdown]
    for kind in ("caption", "info", "warning", "success", "error"):
        parts += [str(e.value) for e in at.get(kind)]
    return " ".join(parts)


def keys(at, prefix):
    return [b.key for b in at.button if b.key and b.key.startswith(prefix)]


def reset_pending(db, client_id, professional_id):
    """Cancela las pendientes previas entre ambos (la regla impide duplicar una pendiente)."""
    conn = db.get_connection()
    conn.execute(
        "UPDATE requests SET status = 'Cancelada', cancelled_by = 'cliente' "
        "WHERE client_id = ? AND professional_id = ? AND status = 'Pendiente'",
        (client_id, professional_id),
    )
    conn.commit()
    conn.close()


def next_valid_slot(db, professional_id):
    """Primera fecha y franja que respetan los días y horas del profesional."""
    from core.constants import FRANJAS_HORARIAS

    pro = db.get_professional_by_id(professional_id)
    date = db.next_work_date(pro["work_days"])
    slot = next(
        s for s in FRANJAS_HORARIAS
        if not pro["work_start"]
        or (pro["work_start"] <= s.split(" - ")[0] and s.split(" - ")[1] <= pro["work_end"])
    )
    return date, slot
