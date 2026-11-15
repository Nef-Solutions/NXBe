"""
Solicitudes de visita y disponibilidad del profesional contra el backend (etapa C).

  GET  /api/requests/                          las del usuario (el backend filtra por rol)
  POST /api/requests/                          crear (solo clientes)
  POST /api/requests/{id}/{accion}/            accept · reject · cancel · cancel_professional ·
                                               finish · confirm (409 si la transición no vale)
  GET|PATCH /api/professionals/me/availability/

Traduce cada solicitud a un diccionario con los estados que muestra el front.
"""

from datetime import date, datetime, timedelta

from core import api_client
from core.constants import DIAS_COMPLETOS, DIAS_SEMANA

# Estado del backend → etiqueta del front
ESTADOS = {
    "PENDING": "Pendiente",
    "ACCEPTED": "Aceptada",
    "PROFESSIONAL_FINISHED": "Esperando confirmación",
    "COMPLETED": "Finalizada",
    "REJECTED": "Rechazada",
    "CANCELLED": "Cancelada",
    "EXPIRED": "Vencida",
    "FORCED_CLOSED": "Cerrada por Overol",
}
DIAS_CORTOS = {full.lower(): short for short, full in DIAS_COMPLETOS.items()}


def _fecha(value, with_time=False):
    """Fecha ISO del backend en formato dd-mm-aaaa (y hora, si corresponde)."""
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if with_time:
        return parsed.astimezone().strftime("%d-%m-%Y %H:%M") if parsed.tzinfo else parsed.strftime("%d-%m-%Y %H:%M")
    return parsed.strftime("%d-%m-%Y")


def from_api(data):
    contact = None
    if data.get("phone") or data.get("address") or data.get("contact_commune"):
        contact = {
            "phone": data.get("phone") or "",
            "address": data.get("address") or "",
            "commune": data.get("contact_commune") or "",
        }
    return {
        "id": data["id"],
        "raw_status": data.get("status"),
        "status": ESTADOS.get(data.get("status"), data.get("status") or ""),
        "client_name": data.get("client_name") or "",
        "professional_name": data.get("professional_name") or "",
        "trade": data.get("category_name") or "",
        "specialty": data.get("specialty_name") or "",
        "description": data.get("problem_description") or "",
        "date": _fecha(data.get("visit_date")),
        "time": data.get("visit_time") or "",
        "commune": data.get("commune") or "",
        "visit_address": data.get("visit_address") or "",
        "rejection_reason": data.get("rejection_reason") or "",
        "cancelled_by": data.get("cancelled_by") or "",
        "cancel_reason": data.get("cancel_reason") or "",
        "client_confirmed": bool(data.get("client_confirmed_at")),
        "professional_confirmed": bool(data.get("professional_confirmed_at")),
        # Plazo tal como lo entrega el backend (hoy 30 días: PEDIDO 5.6)
        "expires_at": _fecha(data.get("expires_at"), with_time=True),
        "contact": contact,
    }


def list_requests():
    data = api_client.request("GET", "requests/")
    items = data.get("results", []) if isinstance(data, dict) else data or []
    return [from_api(item) for item in items]


def create_request(professional_id, specialty_id, description, visit_date, visit_time, commune, address):
    return from_api(api_client.request("POST", "requests/", {
        "professional": professional_id,
        "specialty": specialty_id,
        "problem_description": description.strip(),
        "visit_date": visit_date.isoformat(),
        "visit_time": visit_time,
        "commune": commune,
        "visit_address": address.strip(),
    }))


def action(request_id, name, reason=None):
    """POST /requests/{id}/{name}/. Lanza ApiError (409 si la transición ya no vale)."""
    payload = {"reason": reason} if reason is not None else {}
    return from_api(api_client.request("POST", f"requests/{int(request_id)}/{name}/", payload))


# ------------------------------------------------------------
# Disponibilidad del profesional
# ------------------------------------------------------------

def get_availability():
    """Disponibilidad con los días abreviados del front y las horas en HH:MM."""
    data = api_client.request("GET", "professionals/me/availability/") or {}
    return {
        "work_days": [DIAS_CORTOS[str(d).strip().lower()] for d in data.get("work_days") or []
                      if str(d).strip().lower() in DIAS_CORTOS],
        "work_start": (data.get("work_start") or "")[:5],
        "work_end": (data.get("work_end") or "")[:5],
        "is_available": bool(data.get("is_available", True)),
        "coverage_communes": list(data.get("coverage_communes") or []),
    }


def next_work_date(work_days, start=None):
    """Primer día desde `start` (hoy) en que trabaja el profesional (días abreviados)."""
    day = start or date.today()
    if not work_days:
        return day
    for _ in range(8):
        if DIAS_SEMANA[day.weekday()] in work_days:
            return day
        day += timedelta(days=1)
    return day


# ------------------------------------------------------------
# Valoraciones y reclamos (etapa D)
# ------------------------------------------------------------

ESTADOS_RECLAMO = {
    "OPEN": "Abierto",
    "PROFESSIONAL_RESPONDED": "Respondido por el profesional",
    "ESCALATED": "En mediación",
    "RESOLVED": "Resuelto",
}


def rate(visit_id, quality, punctuality, treatment, comment=""):
    """POST /ratings/: el cliente califica al profesional o el profesional al cliente
    (el backend decide a quién según quién escribe). Una vez por persona y servicio."""
    return api_client.request("POST", "ratings/", {
        "visit": int(visit_id),
        "quality": int(quality),
        "punctuality": int(punctuality),
        "treatment": int(treatment),
        "comment": comment.strip(),
    })


def already_rated(error):
    """True si el 400 del backend dice que esa persona ya calificó el servicio."""
    return any("ya fue calificado" in m for m in api_client.field_messages(error.data, "visit"))


def claim_from_api(data):
    return {
        "id": data["id"],
        "visit": data.get("visit"),
        "description": data.get("description") or "",
        "professional_response": data.get("professional_response") or "",
        "admin_resolution": data.get("admin_resolution") or "",
        "raw_status": data.get("status"),
        "status": ESTADOS_RECLAMO.get(data.get("status"), data.get("status") or ""),
        "created_at": _fecha(data.get("created_at"), with_time=True),
        "resolved_at": _fecha(data.get("resolved_at"), with_time=True),
    }


def list_claims():
    """GET /claims/: el cliente ve los suyos, el profesional los de sus servicios y el admin todos."""
    data = api_client.request("GET", "claims/") or []
    items = data.get("results", []) if isinstance(data, dict) else data
    return sorted((claim_from_api(c) for c in items), key=lambda c: c["id"], reverse=True)


def create_claim(visit_id, description):
    return claim_from_api(api_client.request("POST", "claims/", {"visit": int(visit_id), "description": description.strip()}))


def claim_action(claim_id, name, **payload):
    """POST /claims/{id}/{respond|escalate|resolve}/."""
    return claim_from_api(api_client.request("POST", f"claims/{int(claim_id)}/{name}/", payload))
