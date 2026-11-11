"""
Fase 3: catálogo y perfiles públicos (tarjetas, filtros, perfil y opiniones).

En modo api los datos salen de /api/catalog/ y se traducen a la forma que ya usan
las tarjetas y los perfiles (las mismas claves que una fila de `professionals`).
En modo local cada función delega en core.database, así que nada cambia.

Diferencias con la base local mientras el backend no las tenga (PEDIDO 5.3 a 5.5):
no hay valoración por oficio, ni oficio en cada opinión, ni servicios finalizados.
"""

from urllib.parse import urlencode

import streamlit as st

from core import api_client
from core import database as db
from core.constants import DIAS_COMPLETOS, ESPECIALIDADES_POR_OFICIO, OFICIOS, use_api

# «Lunes» → «Lun» (el backend guarda los días con nombre completo)
DIAS_CORTOS = {full.lower(): short for short, full in DIAS_COMPLETOS.items()}
MAX_PAGINAS = 10


def is_api(professional):
    return isinstance(professional, dict) and professional.get("source") == "api"


@st.cache_data(ttl=30, show_spinner=False)
def _get(path):
    # Endpoints públicos del catálogo; los errores no quedan en caché
    return api_client.request("GET", path, auth=False)


# ------------------------------------------------------------
# Traducción de la respuesta de la API
# ------------------------------------------------------------

def _fee(value):
    try:
        amount = int(float(value or 0))
    except (TypeError, ValueError):
        return ""
    return f"${amount:,}".replace(",", ".") if amount else ""


def from_api(data, anonymous=False):
    """Profesional de la API con las claves de la base local. `anonymous` quita el nombre."""
    days = [DIAS_CORTOS[str(d).strip().lower()] for d in data.get("work_days") or []
            if str(d).strip().lower() in DIAS_CORTOS]
    start = (data.get("work_start") or "")[:5]
    end = (data.get("work_end") or "")[:5]
    name = "" if anonymous else (
        data.get("name") or f"{data.get('first_name', '')} {data.get('last_name', '')}"
    ).strip()

    trades = [
        {
            "trade": t.get("category") or "",
            "specialties": ",".join(s.get("name", "") for s in t.get("specialties") or []),
            "years_experience": t.get("years_experience"),
            "certifications": "",
        }
        for t in data.get("trades") or []
    ]

    opinions = data.get("opinions")
    if opinions is not None:
        opinions = [
            {
                "quality": o.get("quality") or 0,
                "punctuality": o.get("punctuality") or 0,
                "treatment": o.get("treatment") or 0,
                "comment": o.get("comment") or "",
                "trade": "",
            }
            for o in opinions
        ]

    return {
        "source": "api",
        "id": data["id"],
        "name": name,
        "about": data.get("bio") or "",
        "coverage": ",".join(data.get("coverage") or []),
        "work_days": ",".join(days),
        "work_start": start,
        "work_end": end,
        "schedule": f"{', '.join(days)} · {start}–{end}" if days and start else ", ".join(days),
        "visit_fee": _fee(data.get("visit_fee")),
        # El catálogo del backend solo entrega profesionales aprobados
        "verified": 1,
        "availability": 1,
        "trades": trades,
        "rating_avg": round(float(data.get("rating_avg") or 0), 2),
        "opinions": opinions,
    }


# ------------------------------------------------------------
# Datos que usan las tarjetas y los perfiles
# ------------------------------------------------------------

def trades(professional):
    if is_api(professional):
        return professional["trades"]
    return db.get_trades(professional["id"])


def rating(professional, trade=None):
    """(cantidad, promedio). En modo api la cantidad es None si no se conoce
    y la valoración por oficio todavía no existe: devuelve (None, None)."""
    if not is_api(professional):
        return db.get_professional_rating(professional["id"], trade)
    if trade:
        return None, None
    opinions = professional["opinions"]
    return (len(opinions) if opinions is not None else None), professional["rating_avg"]


def stats(professional):
    if not is_api(professional):
        return db.get_professional_stats(professional["id"])
    years = [t["years_experience"] for t in professional["trades"] if t["years_experience"] is not None]
    total, average = rating(professional)
    return {
        "finished": "—",
        "reviews": total or 0,
        "average": average,
        "years": max(years) if years else None,
        "member_since": "",
    }


def reviews(professional, limit=5):
    """Opiniones con comentario, sin datos del cliente."""
    if not is_api(professional):
        return db.get_public_reviews(professional["id"], limit)
    return [o for o in professional["opinions"] or [] if o["comment"]][:limit]


# ------------------------------------------------------------
# Filtros y búsqueda
# ------------------------------------------------------------

def _categories():
    return _get("catalog/categories/") or []


def _specialties(category_id=None):
    query = f"?{urlencode({'category_id': category_id})}" if category_id else ""
    return _get(f"catalog/specialties/{query}") or []


def trade_options():
    if not use_api():
        return OFICIOS
    return [c["name"] for c in _categories()]


def specialty_options(trade):
    if not use_api():
        if trade == "Todas":
            return [s for specs in ESPECIALIDADES_POR_OFICIO.values() for s in specs]
        return ESPECIALIDADES_POR_OFICIO.get(trade, [])

    category_id = _category_id(trade) if trade != "Todas" else None
    if trade != "Todas" and category_id is None:
        return []
    return list(dict.fromkeys(s["name"] for s in _specialties(category_id)))


def _category_id(trade):
    return next((c["id"] for c in _categories() if c["name"] == trade), None)


def _specialty_id(specialty, category_id=None):
    return next((s["id"] for s in _specialties(category_id) if s["name"] == specialty), None)


def list_professionals(trade="Todas", specialty="Todas", commune="Todas", anonymous=False):
    """
    Profesionales disponibles con esos filtros. En modo api el oficio, la especialidad y
    la comuna se piden al backend; la palabra clave se aplica después en el front
    (search_professionals), porque la del backend distingue tildes y busca por nombre.
    """
    if not use_api():
        return db.get_all_professionals(specialty=specialty, commune=commune, trade=trade)

    params = {"page_size": 50}

    if trade != "Todas":
        params["category_id"] = _category_id(trade)
        if params["category_id"] is None:
            return []

    if specialty != "Todas":
        params["specialty_id"] = _specialty_id(specialty, params.get("category_id"))
        if params["specialty_id"] is None:
            return []

    if commune != "Todas":
        params["commune"] = commune

    found = {}
    for page in range(1, MAX_PAGINAS + 1):
        data = _get("catalog/professionals/?" + urlencode({**params, "page": page}))
        results = data.get("results", []) if isinstance(data, dict) else data or []
        for item in results:
            found.setdefault(item["id"], item)  # el backend puede repetir filas al filtrar
        if not isinstance(data, dict) or not data.get("next"):
            break

    return [from_api(item, anonymous) for item in found.values()]


def get_professional(professional_id, anonymous=False):
    """Perfil completo (con opiniones). None si no existe o no está aprobado."""
    if not use_api():
        return db.get_professional_by_id(professional_id)

    try:
        data = _get(f"catalog/professionals/{int(professional_id)}/")
    except api_client.ApiError as error:
        if error.status == 404:
            return None
        raise
    return from_api(data, anonymous)
