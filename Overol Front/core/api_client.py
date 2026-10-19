"""
Cliente HTTP para el backend Django de Overol (contrato: documentación de la API del backend).

Solo se usa cuando OVEROL_BACKEND=api. Los tokens JWT viven en st.session_state:
  - api_access:  token de acceso (15 minutos).
  - api_refresh: token de renovación (7 días).
Si una petición protegida responde 401, se renueva el acceso una vez y se reintenta.
"""

import requests
import streamlit as st

from core.constants import API_BASE_URL, API_TIMEOUT

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
    "privacy_policy_accepted": "Política de privacidad",
    "privacy_policy_version": "Política de privacidad",
    "professional_profile": "Perfil profesional",
}


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


def _error_message(status, data):
    """Convierte la respuesta de error de DRF en un texto en español."""
    if status >= 500:
        return "El servidor de Overol tuvo un problema. Intenta nuevamente más tarde."

    if isinstance(data, dict) and data:
        messages = []
        for field, value in data.items():
            texts = " ".join(_flatten(value))
            if field in ("detail", "non_field_errors"):
                messages.append(texts)
            else:
                messages.append(f"{FIELD_LABELS.get(field, field)}: {texts}")
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


def update_me(phone, address, commune):
    """El backend solo permite modificar teléfono, dirección y comuna."""
    return request(
        "PATCH",
        "auth/me/",
        {"phone": phone.strip(), "address": address.strip(), "commune": commune.strip()},
    )
