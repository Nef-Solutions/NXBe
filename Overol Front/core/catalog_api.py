"""
Catálogo y perfiles públicos (tarjetas, filtros, perfil y opiniones) desde /api/catalog/.

Traduce las respuestas del backend a la forma que usan las tarjetas y los perfiles
(ui/components.format_professional_card, ui/profile, views/shared).

Mientras el backend no los tenga (PEDIDO 5.3 a 5.5): no hay valoración por oficio,
ni oficio en cada opinión, ni cantidad de servicios finalizados.
"""

from urllib.parse import urlencode

import streamlit as st

from core import api_client
from core.constants import DIAS_COMPLETOS

# «Lunes» → «Lun» (el backend guarda los días con nombre completo)
DIAS_CORTOS = {full.lower(): short for short, full in DIAS_COMPLETOS.items()}
MAX_PAGINAS = 10


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
            # Para solicitar una visita: el backend exige una especialidad del profesional
            "specialty_list": [{"id": s["id"], "name": s.get("name", "")} for s in t.get("specialties") or []],
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
    return professional["trades"]


def rating(professional, trade=None):
    """(cantidad, promedio). La cantidad es None si no se conoce (el listado no la trae) y
    la valoración por oficio todavía no existe en el backend: devuelve (None, None)."""
    if trade:
        return None, None
    opinions = professional["opinions"]
    return (len(opinions) if opinions is not None else None), professional["rating_avg"]


def stats(professional):
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
    return [c["name"] for c in _categories()]


def specialty_options(trade):
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
    Profesionales disponibles con esos filtros. El oficio, la especialidad y la comuna se
    piden al backend; la palabra clave se aplica después en el front (search_professionals),
    porque la del backend distingue tildes y busca por nombre.
    """
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
    try:
        data = _get(f"catalog/professionals/{int(professional_id)}/")
    except api_client.ApiError as error:
        if error.status == 404:
            return None
        raise
    return from_api(data, anonymous)
