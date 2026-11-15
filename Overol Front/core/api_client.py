"""
Cliente HTTP para el backend Django de Overol (contrato: documentación de la API del backend).

Los tokens JWT viven en st.session_state (nunca en el navegador):
  - api_access:  token de acceso (15 minutos).
  - api_refresh: token de renovación (7 días).
Si una petición protegida responde 401, se renueva el acceso una vez y se reintenta.
"""

import requests
import streamlit as st

from core.constants import API_BASE_URL, API_TIMEOUT, DIAS_COMPLETOS

ACCESS_KEY = "api_access"
REFRESH_KEY = "api_refresh"

# Nombres legibles de los campos que devuelve el backend en sus errores
FIELD_LABELS = {
    "email": "Correo",
    "username": "Usuario",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "phone": "Teléfono",
    "rut": "RUT",
    "address": "Dirección",
    "commune": "Comuna",
    "role": "Rol",
    "password": "Contraseña",
    "current_password": "Contraseña actual",
    "new_password": "Nueva contraseña",
    "bio": "Presentación",
    "headline": "Titular",
    "contact_preference": "Preferencia de contacto",
    "privacy_policy_accepted": "Política de privacidad",
    "privacy_policy_version": "Política de privacidad",
    "professional_profile": "Perfil profesional",
    "coverage_communes": "Comunas de cobertura",
    "categories": "Oficio",
    "work_days": "Días de trabajo",
    "work_start": "Hora de inicio",
    "work_end": "Hora de término",
    "is_available": "Disponibilidad",
    "professional": "Profesional",
    "specialty": "Especialidad",
    "problem_description": "Descripción",
    "visit_date": "Fecha",
    "visit_time": "Horario",
    "visit_address": "Dirección de la visita",
    "reason": "Motivo",
    "visit_fee": "Tarifa",
    "code": "Código",
    "id_card_front": "Cédula (frente)",
    "id_card_back": "Cédula (reverso)",
    "message": "Mensaje",
}

# Claves de la respuesta de error que no son mensajes para el usuario
HIDDEN_ERROR_KEYS = {"retry_after"}


class ApiError(Exception):
    """Error de la API con un mensaje listo para mostrar al usuario."""

    def __init__(self, message, status=None, data=None):
        super().__init__(message)
        self.status = status
        self.data = data


def _flatten(value):
    if isinstance(value, dict):
        return [m for v in value.values() for m in _flatten(v)]
    if isinstance(value, (list, tuple)):
        return [m for v in value for m in _flatten(v)]
    return [str(value)]


def error_text(status, data):
    """Texto legible para una respuesta de error (o parte de ella)."""
    return _error_message(status, data)


def field_messages(data, field):
    """Mensajes del backend para un campo del error (lista vacía si no hay)."""
    if isinstance(data, dict) and data.get(field):
        return _flatten(data[field])
    return []


def _error_message(status, data):
    """Convierte la respuesta de error de DRF en un texto en español."""
    if status >= 500:
        return "El servidor de Overol tuvo un problema. Intenta nuevamente más tarde."

    if isinstance(data, dict) and data:
        messages = []
        for field, value in data.items():
            if field in HIDDEN_ERROR_KEYS:
                continue
            texts = " ".join(_flatten(value))
            if field in ("detail", "non_field_errors"):
                messages.append(texts)
            else:
                messages.append(f"{FIELD_LABELS.get(field, field)}: {texts}")
        if messages:
            return " ".join(messages)

    if isinstance(data, list) and data:
        return " ".join(_flatten(data))

    return {
        401: "Tu sesión expiró. Vuelve a iniciar sesión.",
        403: "No tienes permiso para realizar esta acción.",
        404: "El recurso solicitado no existe.",
    }.get(status, f"Error inesperado del servidor (código {status}).")


def _send(method, path, payload=None, access=None, files=None):
    """`files` ({campo: (nombre, bytes, tipo)}) envía multipart en vez de JSON."""
    headers = {"Accept": "application/json"}
    if access:
        headers["Authorization"] = f"Bearer {access}"

    extra = {"files": files, "data": payload or {}} if files else {"json": payload}
    try:
        response = requests.request(
            method,
            API_BASE_URL + path.lstrip("/"),
            headers=headers,
            timeout=API_TIMEOUT,
            **extra,
        )
    except requests.RequestException:
        raise ApiError(
            "No se pudo conectar con el servidor de Overol. "
            "Revisa que el backend esté en ejecución."
        )

    try:
        data = response.json() if response.content else None
    except ValueError:
        data = None

    if response.status_code >= 400:
        raise ApiError(_error_message(response.status_code, data), response.status_code, data)

    return data


# ------------------------------------------------------------
# Tokens
# ------------------------------------------------------------

def set_tokens(access, refresh_token):
    st.session_state[ACCESS_KEY] = access
    st.session_state[REFRESH_KEY] = refresh_token


def clear_tokens():
    st.session_state.pop(ACCESS_KEY, None)
    st.session_state.pop(REFRESH_KEY, None)


def get_refresh_token():
    return st.session_state.get(REFRESH_KEY)


def refresh():
    """Pide un nuevo token de acceso. Devuelve True si lo consiguió."""
    refresh_token = st.session_state.get(REFRESH_KEY)
    if not refresh_token:
        return False

    try:
        data = _send("POST", "auth/token/refresh/", {"refresh": refresh_token})
    except ApiError as error:
        # 400/401: el token de renovación venció o es inválido
        if error.status in (400, 401):
            clear_tokens()
            return False
        raise

    st.session_state[ACCESS_KEY] = data["access"]

    # Si el backend rota el token de renovación, se guarda el nuevo
    if data.get("refresh"):
        st.session_state[REFRESH_KEY] = data["refresh"]
        from core.session import update_session_refresh

        update_session_refresh(st.session_state.get("session_token"), data["refresh"])

    return True


def request(method, path, payload=None, auth=True, files=None):
    """Petición a la API. Con auth=True envía el JWT y lo renueva si expiró."""
    if not auth:
        return _send(method, path, payload, files=files)

    if not st.session_state.get(ACCESS_KEY) and not refresh():
        raise ApiError("Tu sesión expiró. Vuelve a iniciar sesión.", 401)

    try:
        return _send(method, path, payload, st.session_state.get(ACCESS_KEY), files)
    except ApiError as error:
        if error.status != 401 or not refresh():
            raise
        return _send(method, path, payload, st.session_state.get(ACCESS_KEY), files)


# ------------------------------------------------------------
# Autenticación y perfil
# ------------------------------------------------------------

def login(email, password):
    """Obtiene los tokens y devuelve el perfil del usuario (GET /auth/me/)."""
    data = _send("POST", "auth/token/", {"email": email, "password": password})
    set_tokens(data["access"], data["refresh"])
    return get_me()


def register(payload):
    return request("POST", "auth/register/", payload, auth=False)


def get_me():
    return request("GET", "auth/me/")


def update_me(**fields):
    """PATCH /auth/me/: phone, address, commune y, para profesionales, bio, headline,
    contact_preference y visit_fee (el backend ignora estos últimos en un cliente)."""
    return request(
        "PATCH",
        "auth/me/",
        {k: v.strip() if isinstance(v, str) else v for k, v in fields.items()},
    )


def logout():
    """Anula en el backend el token de renovación de esta sesión (POST /auth/logout/)."""
    if not st.session_state.get(REFRESH_KEY):
        return

    # El cuerpo se arma DESPUÉS de renovar: renovar rota el token de renovación
    if not st.session_state.get(ACCESS_KEY) and not refresh():
        return
    try:
        _send("POST", "auth/logout/", {"refresh": st.session_state[REFRESH_KEY]}, st.session_state[ACCESS_KEY])
    except ApiError as error:
        if error.status != 401 or not refresh():
            raise
        _send("POST", "auth/logout/", {"refresh": st.session_state[REFRESH_KEY]}, st.session_state[ACCESS_KEY])


def change_password(current_password, new_password):
    return request(
        "POST",
        "auth/password/change/",
        {"current_password": current_password, "new_password": new_password},
    )


def reset_password(email):
    """Paso 1: el backend envía un código de 6 dígitos (202 exista o no la cuenta)."""
    data = request("POST", "auth/password/reset/", {"email": email.strip().lower()}, auth=False)
    return (data or {}).get("detail", "")


def confirm_password_reset(email, code, new_password):
    """Paso 2: código de 6 dígitos y contraseña nueva. Anula las sesiones abiertas."""
    data = request(
        "POST",
        "auth/password/reset/confirm/",
        {"email": email.strip().lower(), "code": code.strip(), "new_password": new_password},
        auth=False,
    )
    return (data or {}).get("detail", "")


# ------------------------------------------------------------
# Verificación, suscripción, pagos y asistente
# ------------------------------------------------------------

def get_verification_documents():
    return request("GET", "auth/verification/documents/") or {}


def upload_verification_documents(files):
    """files: {"id_card_front"|"id_card_back": (nombre, bytes, tipo)} (multipart)."""
    return request("POST", "auth/verification/documents/", files=files) or {}


def get_verification_messages():
    return request("GET", "auth/verification/messages/") or []


def send_verification_message(message):
    return request("POST", "auth/verification/messages/", {"message": message.strip()})


def get_subscription():
    return request("GET", "payments/professional-subscription/") or {}


def start_subscription_payment():
    """Inicia el pago del plan activo: devuelve url y token de Webpay (sandbox)."""
    return request("POST", "payments/professional-subscription/transbank/", {}) or {}


def assistant_chat(message):
    return (request("POST", "assistant/chat/", {"message": message.strip()}) or {}).get("reply", "")


def get_categories():
    """Oficios del catálogo del backend: [{id, name, keywords, home_zones}]."""
    return request("GET", "catalog/categories/", auth=False) or []


def get_specialties(category_id):
    """Especialidades de un oficio del backend: [{id, name, category_id}]."""
    return request("GET", f"catalog/specialties/?category_id={int(category_id)}", auth=False) or []


def update_availability(work_days, work_start, work_end, is_available, coverage):
    """Disponibilidad del profesional. Los días van con nombre completo («Lun» → «Lunes»)."""
    return request(
        "PATCH",
        "professionals/me/availability/",
        {
            "work_days": [DIAS_COMPLETOS.get(day, day) for day in work_days],
            "work_start": work_start,
            "work_end": work_end,
            "is_available": bool(is_available),
            "coverage_communes": list(coverage),
        },
    )


# ------------------------------------------------------------
# Notificaciones y tickets de soporte (etapa E)
# ------------------------------------------------------------

ESTADOS_TICKET = {"OPEN": "Abierto", "IN_REVIEW": "En revisión", "RESOLVED": "Resuelto"}


def list_notifications():
    """GET /notifications/: las del usuario, de la más nueva a la más antigua."""
    data = request("GET", "notifications/") or []
    items = data.get("results", []) if isinstance(data, dict) else data
    return sorted(items, key=lambda n: n.get("created_at") or "", reverse=True)


def unread_notifications():
    """Cantidad de no leídas (None si el backend no responde)."""
    try:
        return sum(1 for n in list_notifications() if not n.get("is_read"))
    except ApiError:
        return None


def read_notification(notification_id):
    return request("POST", f"notifications/{int(notification_id)}/read/", {})


def list_tickets(status=None):
    """GET /tickets/: los propios (el admin ve todos). `status`: OPEN, IN_REVIEW o RESOLVED."""
    data = request("GET", "tickets/" + (f"?status={status}" if status else "")) or []
    items = data.get("results", []) if isinstance(data, dict) else data
    return sorted(items, key=lambda t: t.get("id", 0), reverse=True)


def create_ticket(visit_id, subject, description):
    return request("POST", "tickets/", {
        "visit": int(visit_id), "subject": subject.strip(), "description": description.strip(),
    })


def resolve_ticket(ticket_id, response):
    return request("POST", f"tickets/{int(ticket_id)}/resolve/", {"response": response.strip()})


# ------------------------------------------------------------
# Oficios del profesional y centro de desarrollo (etapa F)
# ------------------------------------------------------------

MODULOS_CONTENIDO = {"TAX": "Tributario", "SAFETY": "Seguridad", "MANAGEMENT": "Gestión"}


def list_my_trades():
    """GET /professionals/me/trades/: id, category_id, years_experience, description,
    certification, certification_verified, is_active (las especialidades no vienen)."""
    return request("GET", "professionals/me/trades/") or []


def add_trade(category_id, years, description, specialties):
    return request("POST", "professionals/me/trades/", {
        "category_id": int(category_id), "years_experience": int(years or 0),
        "description": description.strip(), "specialties": list(specialties),
    })


def update_trade(trade_id, **fields):
    """PATCH: years_experience, description y specialties (el backend solo agrega especialidades)."""
    return request("PATCH", f"professionals/me/trades/{int(trade_id)}/", fields)


def deactivate_trade(trade_id):
    """DELETE: desactiva el oficio (no lo borra)."""
    return request("DELETE", f"professionals/me/trades/{int(trade_id)}/")


def list_content():
    """GET /professional-center/content/ (solo profesionales): title, description, module, url, order."""
    data = request("GET", "professional-center/content/") or []
    return data.get("results", []) if isinstance(data, dict) else data


def complete_content(content_id):
    return request("POST", "professional-center/progress/", {"content": int(content_id)})


# ------------------------------------------------------------
# Administración (etapa G)
# ------------------------------------------------------------

ESTADOS_CUENTA = {"ACTIVE": "Activa", "SUSPENDED": "Suspendida", "BLOCKED": "Bloqueada", "DEACTIVATED": "Desactivada"}


def decide_verification(professional_profile_id, decision, reason=""):
    """POST /auth/verification/{id}/{approve|reject}/. Aprobar exige ambos lados de la cédula."""
    return request("POST", f"auth/verification/{int(professional_profile_id)}/{decision}/", {"reason": reason.strip()})


def set_account_status(user_id, status, reason):
    """POST /auth/admin/accounts/{id}/status/ con ACTIVE, SUSPENDED, BLOCKED o DEACTIVATED y motivo."""
    return request("POST", f"auth/admin/accounts/{int(user_id)}/status/", {"status": status, "reason": reason.strip()})


def download_verification_document(professional_profile_id, side):
    """Descarga privada de la cédula (admin con is_staff). Devuelve (bytes, tipo, nombre)."""
    path = f"admin/verifications/{int(professional_profile_id)}/document/?side={side}"
    for attempt in (1, 2):
        if not st.session_state.get(ACCESS_KEY) and not refresh():
            raise ApiError("Tu sesión expiró. Vuelve a iniciar sesión.", 401)
        try:
            response = requests.request(
                "GET", API_BASE_URL + path,
                headers={"Authorization": f"Bearer {st.session_state.get(ACCESS_KEY)}"},
                timeout=API_TIMEOUT,
            )
        except requests.RequestException:
            raise ApiError("No se pudo conectar con el servidor de Overol. Revisa que el backend esté en ejecución.")
        if response.status_code == 401 and attempt == 1 and refresh():
            continue
        if response.status_code >= 400:
            try:
                data = response.json()
            except ValueError:
                data = None
            raise ApiError(_error_message(response.status_code, data), response.status_code, data)
        disposition = response.headers.get("Content-Disposition", "")
        name = disposition.split("filename=")[-1].strip('"') if "filename=" in disposition else f"cedula_{side}"
        return response.content, response.headers.get("Content-Type", "application/octet-stream"), name
