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


def _send(method, path, payload=None, access=None):
    headers = {"Accept": "application/json"}
    if access:
        headers["Authorization"] = f"Bearer {access}"

    try:
        response = requests.request(
            method,
            API_BASE_URL + path.lstrip("/"),
            json=payload,
            headers=headers,
            timeout=API_TIMEOUT,
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


def request(method, path, payload=None, auth=True):
    """Petición a la API. Con auth=True envía el JWT y lo renueva si expiró."""
    if not auth:
        return _send(method, path, payload)

    if not st.session_state.get(ACCESS_KEY) and not refresh():
        raise ApiError("Tu sesión expiró. Vuelve a iniciar sesión.", 401)

    try:
        return _send(method, path, payload, st.session_state.get(ACCESS_KEY))
    except ApiError as error:
        if error.status != 401 or not refresh():
            raise
        return _send(method, path, payload, st.session_state.get(ACCESS_KEY))


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
    """El backend responde 202 exista o no la cuenta (no revela qué correos están registrados)."""
    data = request("POST", "auth/password/reset/", {"email": email.strip().lower()}, auth=False)
    return (data or {}).get("detail", "")


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
