"""
Sesiones persistentes: permiten mantener la sesión abierta aunque se recargue la página.

Funcionamiento:
  1. Al ingresar con «Mantener mi sesión iniciada» se crea un token aleatorio.
     En la base de datos solo se guarda su HASH (SHA-256), nunca el token.
  2. El token viaja en una cookie del navegador (overol_session).
  3. Al abrir o recargar la página, si la cookie trae un token válido y no vencido,
     la sesión se restaura sin pedir la contraseña.
  4. Al cerrar sesión se elimina el token de la base y se borra la cookie.

Requiere Streamlit 1.37 o superior (st.context.cookies). En versiones anteriores la
función queda desactivada sin afectar al resto de la aplicación.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

import streamlit as st

from core.constants import DIAS_SESION, use_api
from core.database import get_connection, get_user

COOKIE_NAME = "overol_session"


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id, days=DIAS_SESION, api_refresh=""):
    """Crea una sesión persistente y devuelve el token (se entrega solo al navegador).
    En modo api guarda también el token de renovación del backend (en texto plano:
    limitación aceptada del prototipo, ver README)."""
    token = secrets.token_urlsafe(32)
    now = datetime.now()

    conn = get_connection()
    # Limpia sesiones vencidas de paso
    conn.execute(
        "DELETE FROM user_sessions WHERE expires_at < ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"),),
    )
    conn.execute(
        """
        INSERT INTO user_sessions (token_hash, user_id, created_at, expires_at, api_refresh)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            _hash(token),
            user_id,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            (now + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"),
            api_refresh or "",
        ),
    )
    conn.commit()
    conn.close()
    return token


def get_session_refresh(token):
    """Token de renovación del backend guardado con la sesión persistente ('' si no hay)."""
    if not token:
        return ""

    conn = get_connection()
    row = conn.execute(
        "SELECT api_refresh FROM user_sessions WHERE token_hash = ?",
        (_hash(token),),
    ).fetchone()
    conn.close()
    return (row["api_refresh"] or "") if row else ""


def update_session_refresh(token, api_refresh):
    """Guarda un token de renovación rotado por el backend."""
    if not token:
        return

    conn = get_connection()
    conn.execute(
        "UPDATE user_sessions SET api_refresh = ? WHERE token_hash = ?",
        (api_refresh, _hash(token)),
    )
    conn.commit()
    conn.close()


def validate_session(token):
    """Devuelve el usuario dueño del token si la sesión es válida; si no, None."""
    if not token:
        return None

    conn = get_connection()
    row = conn.execute(
        "SELECT user_id, expires_at FROM user_sessions WHERE token_hash = ?",
        (_hash(token),),
    ).fetchone()

    if not row:
        conn.close()
        return None

    if row["expires_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        conn.execute("DELETE FROM user_sessions WHERE token_hash = ?", (_hash(token),))
        conn.commit()
        conn.close()
        return None

    conn.close()

    user = get_user(row["user_id"])

    # Una cuenta suspendida o eliminada no puede restaurar su sesión
    if not user or not user["active"]:
        return None

    return user


def delete_session(token):
    if not token:
        return

    conn = get_connection()
    conn.execute("DELETE FROM user_sessions WHERE token_hash = ?", (_hash(token),))
    conn.commit()
    conn.close()


def read_session_cookie():
    """Lee la cookie de sesión que envió el navegador (None si no existe o no es compatible)."""
    try:
        value = st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None

    # Solo se aceptan textos con la forma de un token; cualquier otra cosa se ignora
    if isinstance(value, str) and 20 <= len(value) <= 200:
        return value

    return None


def restore_session():
    """Si el navegador trae una sesión válida, deja al usuario autenticado."""
    if st.session_state.get("authenticated") or st.session_state.get("_session_checked"):
        return

    st.session_state["_session_checked"] = True

    token = read_session_cookie()

    try:
        user = validate_session(token)
    except Exception:
        user = None

    # Modo api: la sesión solo se restaura si el backend acepta el token de renovación
    if user and use_api():
        from core import api_client

        api_client.set_tokens(None, get_session_refresh(token))
        try:
            restored = api_client.refresh()
        except api_client.ApiError:
            restored = False

        if not restored:
            api_client.clear_tokens()
            return

    if user:
        st.session_state.user_id = user["id"]
        st.session_state.authenticated = True
        st.session_state["session_token"] = token


def render_cookie_script():
    """
    Escribe o borra la cookie en el navegador. Se llama una vez por ejecución, al final
    de la página, y solo hace algo cuando hay una orden pendiente.
    """
    set_token = st.session_state.pop("_set_cookie", None)
    clear = st.session_state.pop("_clear_cookie", False)

    if not set_token and not clear:
        return

    if set_token:
        script = (
            "const s = window.parent.location.protocol === 'https:' ? '; Secure' : '';"
            f"window.parent.document.cookie = '{COOKIE_NAME}={set_token}; "
            f"max-age={DIAS_SESION * 86400}; path=/; SameSite=Lax' + s;"
        )
    else:
        script = (
            f"window.parent.document.cookie = '{COOKIE_NAME}=; max-age=0; path=/; SameSite=Lax';"
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
