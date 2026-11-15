"""
Sesión del usuario contra el backend Django.

Usuario actual:
  Sale de GET /api/auth/me/ y se guarda en st.session_state["me"] (current_user()).
  Se vuelve a pedir cada SEGUNDOS_REVALIDAR para notar una cuenta suspendida.

Sesión persistente («Mantener mi sesión iniciada», 7 días):
  1. La cookie del navegador (overol_session) lleva SOLO un identificador aleatorio
     de 256 bits. No lleva tokens ni datos personales. SameSite=Lax, y Secure si la página
     carga por https o si OVEROL_COOKIE_SECURE=1 (app publicada tras https).
  2. El token de renovación del backend vive en la MEMORIA del servidor de Streamlit
     (st.cache_resource), indexado por el hash del identificador, con vencimiento a 7 días.
  3. Al recargar la página, la cookie permite recuperar el token y pedir un acceso nuevo.
  4. Cerrar sesión llama a POST /auth/logout/ (anula el token en el backend), borra la
     entrada de memoria y la cookie.
  Si el servidor de Streamlit se reinicia, la memoria se pierde y se pide ingresar de nuevo.

Requiere Streamlit 1.37 o superior (st.context.cookies).
"""

import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta

import streamlit as st

from core import api_client
from core.config import cookie_secure
from core.constants import API_ROLES, DIAS_SESION

COOKIE_NAME = "overol_session"
USER_KEY = "me"
SEGUNDOS_REVALIDAR = 60


# ------------------------------------------------------------
# Sesiones persistentes en memoria del servidor
# ------------------------------------------------------------

@st.cache_resource
def _store():
    return {"lock": threading.Lock(), "sessions": {}}


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(refresh_token, days=DIAS_SESION):
    """Guarda el token de renovación en memoria y devuelve el identificador para la cookie."""
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    store = _store()
    with store["lock"]:
        # Limpia de paso las sesiones vencidas
        for key in [k for k, v in store["sessions"].items() if v["expires"] < now]:
            del store["sessions"][key]
        store["sessions"][_hash(token)] = {"refresh": refresh_token, "expires": now + timedelta(days=days)}
    return token


def get_session_refresh(token):
    """Token de renovación de una sesión vigente ('' si no existe o venció)."""
    if not token:
        return ""
    store = _store()
    with store["lock"]:
        entry = store["sessions"].get(_hash(token))
        if entry and entry["expires"] < datetime.now():
            del store["sessions"][_hash(token)]
            entry = None
    return entry["refresh"] if entry else ""


def update_session_refresh(token, refresh_token):
    """El backend rota el token de renovación: se reemplaza el guardado (sin alargar el plazo)."""
    if not token:
        return
    store = _store()
    with store["lock"]:
        entry = store["sessions"].get(_hash(token))
        if entry:
            entry["refresh"] = refresh_token


def delete_session(token):
    if not token:
        return
    store = _store()
    with store["lock"]:
        store["sessions"].pop(_hash(token), None)


# ------------------------------------------------------------
# Usuario actual
# ------------------------------------------------------------

def user_from_me(me):
    """Respuesta de /auth/me/ con las claves que usan las pantallas."""
    role = API_ROLES.get(me.get("role"))
    if not role:
        raise ValueError(f"Rol desconocido del backend: {me.get('role')!r}")

    email = (me.get("email") or "").strip().lower()
    name = f"{(me.get('first_name') or '').strip()} {(me.get('last_name') or '').strip()}".strip()
    return {
        "id": me["id"],
        "email": email,
        "name": name or email,
        "first_name": me.get("first_name") or "",
        "last_name": me.get("last_name") or "",
        "rut": me.get("rut") or "",
        "role": role,
        "active": True,
        "phone": me.get("phone") or "",
        "address": me.get("address") or "",
        "commune": me.get("commune") or "",
        "contact_preference": me.get("contact_preference") or "",
        "bio": me.get("bio") or "",
        "headline": me.get("headline") or "",
        "visit_fee": me.get("visit_fee"),
        "verification_status": me.get("verification_status"),
        "professional_profile_id": me.get("professional_profile_id"),
    }


def load_user():
    """Pide /auth/me/ y deja el usuario en la sesión. Puede lanzar ApiError o ValueError."""
    user = user_from_me(api_client.get_me())
    st.session_state[USER_KEY] = user
    st.session_state["_me_loaded_at"] = time.time()
    return user


def current_user():
    """Usuario autenticado (o None). Se revalida con el backend cada SEGUNDOS_REVALIDAR."""
    if not st.session_state.get("authenticated"):
        return None

    user = st.session_state.get(USER_KEY)
    if user and time.time() - st.session_state.get("_me_loaded_at", 0) < SEGUNDOS_REVALIDAR:
        return user

    try:
        return load_user()
    except api_client.ApiError as error:
        # 401: el token ya no sirve (sesión vencida, cuenta suspendida o desactivada)
        if error.status == 401:
            return None
        # Backend caído: se sigue con los datos conocidos y se reintenta en la próxima ejecución
        return user
    except ValueError:
        return None


def is_profile_complete(user):
    """Cliente y profesional deben tener teléfono, dirección y comuna antes de entrar."""
    return user["role"] == "admin" or all(user[k] for k in ("phone", "address", "commune"))


def start_session(remember):
    """Tras un login exitoso (tokens ya guardados): carga el usuario y, si corresponde,
    crea la sesión persistente. Puede lanzar ApiError o ValueError."""
    load_user()
    st.session_state["authenticated"] = True
    st.session_state.pop("show_login", None)

    if remember:
        token = create_session(api_client.get_refresh_token())
        st.session_state["session_token"] = token
        st.session_state["_set_cookie"] = token
    else:
        st.session_state["_clear_cookie"] = True


def end_session():
    """Cierra la sesión en el backend, en la memoria del servidor y en el navegador."""
    try:
        api_client.logout()
    except api_client.ApiError:
        pass  # aunque el backend no responda, la sesión local se cierra igual

    delete_session(st.session_state.get("session_token"))
    st.session_state.clear()
    st.session_state["_clear_cookie"] = True


# ------------------------------------------------------------
# Cookie
# ------------------------------------------------------------

def read_session_cookie():
    """Lee la cookie de sesión que envió el navegador (None si no existe o no es compatible)."""
    try:
        value = st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None

    # Solo se aceptan textos con la forma de un identificador; cualquier otra cosa se ignora
    if isinstance(value, str) and 20 <= len(value) <= 200:
        return value

    return None


def restore_session():
    """Si el navegador trae el identificador de una sesión vigente, la restaura."""
    if st.session_state.get("authenticated") or st.session_state.get("_session_checked"):
        return

    st.session_state["_session_checked"] = True

    token = read_session_cookie()
    refresh_token = get_session_refresh(token)

    if not refresh_token:
        if token:
            st.session_state["_clear_cookie"] = True  # identificador desconocido o vencido
        return

    api_client.set_tokens(None, refresh_token)
    st.session_state["session_token"] = token

    try:
        restored = api_client.refresh() and load_user()
    except (api_client.ApiError, ValueError):
        restored = False

    if not restored:
        api_client.clear_tokens()
        delete_session(token)
        st.session_state.pop("session_token", None)
        st.session_state["_clear_cookie"] = True
        return

    st.session_state["authenticated"] = True


def render_cookie_script():
    """
    Escribe o borra la cookie en el navegador. Se llama una vez por ejecución, al final
    de la página, y solo hace algo cuando hay una orden pendiente.
    """
    set_token = st.session_state.pop("_set_cookie", None)
    clear = st.session_state.pop("_clear_cookie", False)

    if not set_token and not clear:
        return

    # Secure: siempre con OVEROL_COOKIE_SECURE=1; si no, solo cuando la página carga por https
    secure = (
        "const s = '; Secure';" if cookie_secure()
        else "const s = window.parent.location.protocol === 'https:' ? '; Secure' : '';"
    )
    if set_token:
        script = (
            secure
            + f"window.parent.document.cookie = '{COOKIE_NAME}={set_token}; "
            f"max-age={DIAS_SESION * 86400}; path=/; SameSite=Lax' + s;"
        )
    else:
        script = (
            secure
            + f"window.parent.document.cookie = '{COOKIE_NAME}=; max-age=0; path=/; SameSite=Lax' + s;"
        )

    html = f"<script>try {{ {script} }} catch (e) {{}}</script>"

    try:
        if hasattr(st, "iframe"):
            # Streamlit reciente: st.iframe reemplaza a components.v1.html
            st.iframe(html, height=1)
        else:
            import streamlit.components.v1 as components

            components.html(html, height=0)
    except Exception:
        pass
