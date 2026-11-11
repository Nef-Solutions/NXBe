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
    _simular_backend()
    return str(front)


# ------------------------------------------------------------
# Backend simulado: ninguna prueba sale a la red
# ------------------------------------------------------------

peticiones = []      # (método, ruta) de cada petición HTTP que hizo la app
TAM_PAGINA = [50]    # una prueba puede achicarlo para ejercitar la paginación
BACKEND_CAIDO = [False]  # True: el catálogo también falla como backend apagado


class _Respuesta:
    def __init__(self, status, data):
        import json

        self.status_code = status
        self._data = data
        self.content = json.dumps(data, default=str).encode()

    def json(self):
        return self._data


def _simular_backend():
    """En modo api, /api/catalog/ responde con los profesionales de la copia SQLite, en el
    formato del backend (ids iguales a los locales). Cualquier otra ruta falla como si el
    backend estuviera apagado. En modo local solo registra si algo intentó salir a la red."""
    import requests

    def fake(method, url, json=None, headers=None, timeout=None):
        from urllib.parse import parse_qs, urlsplit

        from core.constants import API_BASE_URL, use_api

        parts = urlsplit(url.replace(API_BASE_URL, "/"))
        peticiones.append((method, parts.path + (f"?{parts.query}" if parts.query else "")))
        if use_api() and method == "GET" and parts.path.startswith("/catalog/") and not BACKEND_CAIDO[0]:
            query = {k: v[0] for k, v in parse_qs(parts.query).items()}
            return _catalogo(parts.path, query)
        raise requests.ConnectionError("backend simulado: ruta no disponible")

    requests.request = fake


def _catalogo(path, query):
    from core import database as db
    from core.constants import DIAS_COMPLETOS, ESPECIALIDADES_POR_OFICIO, OFICIOS

    categories = [{"id": i, "name": n, "keywords": "", "home_zones": []} for i, n in enumerate(OFICIOS, 1)]
    specialties, sid = [], 0
    for c in categories:
        for name in ESPECIALIDADES_POR_OFICIO.get(c["name"], []):
            sid += 1
            specialties.append({"id": sid, "name": name, "category_id": c["id"]})

    def serializar(row, detail=False):
        trades = []
        for t in db.get_trades(row["id"]):
            cat = next((c for c in categories if c["name"] == t["trade"]), {"id": 0})
            names = [s.strip() for s in (t["specialties"] or "").split(",") if s.strip()]
            trades.append({
                "id": t["id"], "category_id": cat["id"], "category": t["trade"],
                "years_experience": t["years_experience"], "description": "",
                "specialties": [{"id": s["id"], "name": s["name"]} for s in specialties if s["name"] in names],
            })
        first, _, last = row["name"].partition(" ")
        data = {
            "id": row["id"], "name": row["name"], "first_name": first, "last_name": last,
            "visit_fee": f"{int(re.sub(r'[^0-9]', '', row['visit_fee'] or '') or 0)}.00",
            "rating_avg": db.get_professional_rating(row["id"])[1],
            "verification_status": "APPROVED", "trades": trades, "profile_photo": None,
            "commune": None, "rut": None, "address": None, "bio": row["about"] or "",
            "coverage": [c.strip() for c in row["coverage"].split(",") if c.strip()],
            "work_days": [DIAS_COMPLETOS[d] for d in (row["work_days"] or "").split(",") if d in DIAS_COMPLETOS],
            "work_start": f"{row['work_start']}:00" if row["work_start"] else None,
            "work_end": f"{row['work_end']}:00" if row["work_end"] else None,
        }
        if detail:
            data["opinions"] = [
                {"quality": r["quality"], "punctuality": r["punctuality"], "treatment": r["treatment"],
                 "comment": r["comment"], "created_at": "2026-11-01T10:00:00", "author_name": "Cliente D."}
                for r in db.get_public_reviews(row["id"], limit=100)
            ]
        return data

    if path == "/catalog/categories/":
        return _Respuesta(200, categories)
    if path == "/catalog/specialties/":
        cid = query.get("category_id")
        return _Respuesta(200, [s for s in specialties if not cid or str(s["category_id"]) == cid])

    match = re.fullmatch(r"/catalog/professionals/(\d+)/", path)
    if match:
        row = db.get_professional_by_id(int(match.group(1)))
        if not row or not row["verified"] or not row["active"]:
            return _Respuesta(404, {"detail": "No encontrado."})
        return _Respuesta(200, serializar(row, detail=True))

    if path == "/catalog/professionals/":
        rows = db.get_all_professionals()
        cat = next((c["name"] for c in categories if str(c["id"]) == query.get("category_id")), None)
        spec = next((s["name"] for s in specialties if str(s["id"]) == query.get("specialty_id")), None)
        result = []
        for row in rows:
            trades = db.get_trades(row["id"])
            if "category_id" in query and cat not in [t["trade"] for t in trades]:
                continue
            specs = [s.strip() for t in trades if not cat or t["trade"] == cat
                     for s in (t["specialties"] or "").split(",")]
            if "specialty_id" in query and spec not in specs:
                continue
            if "commune" in query and query["commune"] not in row["coverage"].split(","):
                continue
            result.append(serializar(row))
        size = min(int(query.get("page_size", 20)), TAM_PAGINA[0])
        page = int(query.get("page", 1))
        chunk = result[(page - 1) * size: page * size]
        more = page * size < len(result)
        return _Respuesta(200, {"count": len(result), "next": f"?page={page + 1}" if more else None,
                                "previous": None, "results": chunk})

    return _Respuesta(404, {"detail": "No encontrado."})


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        _fails.append(msg)


def terminar():
    print("\nRESULTADO:", "TODO OK" if not _fails else f"{len(_fails)} fallo(s)")
    sys.exit(1 if _fails else 0)


def new_app(front, user_id=None):
    """Abre la app con la sesión de `user_id` ya iniciada (None = visitante)."""
    import streamlit
    from streamlit.testing.v1 import AppTest

    streamlit.cache_data.clear()  # el catálogo de la API se guarda en caché 30 s
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
