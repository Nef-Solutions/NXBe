"""
OVEROL - PROTOTIPO INTEGRAL CAPSTONE
Equipo NXBe

Archivo principal. Se puede ejecutar de dos formas:
    python app.py            (arranca Streamlit automáticamente)
    streamlit run app.py

Épicas / RF contempladas:
001 Registro + verificación profesional   006 Reputación + evaluación
002 Búsqueda + categorización             007 Centro de Desarrollo Profesional
003 Chatbot de diagnóstico                008 Administración + moderación
004 Perfil profesional + solicitud        009 Posventa + reclamos
005 Geolocalización + cobertura

PROTOTIPO FUNCIONAL LOCAL: usa SQLite para persistencia durante las
demostraciones. No reemplaza todavía un backend productivo.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# ============================================================
# 0. ARRANQUE AUTOMÁTICO DE STREAMLIT
# ============================================================

BOOTSTRAP_ENV = "OVEROL_STREAMLIT_STARTED"


def ensure_streamlit():
    if importlib.util.find_spec("streamlit") is None:
        print("Streamlit no está instalado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])


ensure_streamlit()

# Cuando se ejecuta con `python app.py`, levantamos Streamlit una sola vez.
# Se usa una variable de entorno en vez de un argumento de sys.argv porque
# Streamlit puede reconstruir sys.argv durante un rerun; eso podía provocar
# que el login abriera otra instancia/pestaña de la aplicación.
if os.environ.get(BOOTSTRAP_ENV) != "1":
    app_path = str(Path(__file__).resolve())
    child_env = os.environ.copy()
    child_env[BOOTSTRAP_ENV] = "1"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", app_path],
        env=child_env,
    )
    sys.exit()


# ============================================================
# 1. IMPORTACIONES
# ============================================================

import streamlit as st

# set_page_config debe ser el primer comando de Streamlit
st.set_page_config(
    page_title="Overol",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.constants import use_api
from core.database import expire_pending_requests, get_user, get_user_profile, init_db
from core.session import delete_session, render_cookie_script, restore_session
from ui.components import flash, load_css, navbar, security_note, show_flash
from views.admin import admin_dashboard
from views.auth import login_screen
from views.client import client_dashboard
from views.professional import professional_dashboard
from views.shared import close_professional, personal_questions_screen, sidebar
from views.visitor import visitor_dashboard


# ============================================================
# 2. ESTILOS Y BASE DE DATOS
# ============================================================

load_css()


@st.cache_resource
def bootstrap_database():
    """Crea tablas y datos demo una sola vez por proceso (no en cada rerun)."""
    init_db()
    return True


bootstrap_database()

# Las solicitudes pendientes sin respuesta por más de 72 horas pasan a «Vencida»
expire_pending_requests()

# Si el navegador trae una sesión persistente válida, se restaura sin pedir la contraseña
restore_session()


def back_to_visitor():
    """Callback del botón «Volver a explorar»: regresa siempre a la portada del visitante.
    Se ejecuta antes de redibujar la página, por eso no depende de st.rerun()."""
    st.session_state.pop("show_login", None)
    st.session_state["visitor_navigation"] = "🏠 Inicio"
    st.session_state["_visitor_prev_menu"] = "🏠 Inicio"
    close_professional()


# ============================================================
# 3. CABECERA
# ============================================================

_session_user = (
    get_user(st.session_state.user_id)
    if st.session_state.get("authenticated") and st.session_state.get("user_id")
    else None
)

navbar(_session_user)


# ============================================================
# 4. ESTADO DE AUTENTICACIÓN Y ENRUTAMIENTO POR ROL
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

show_flash()


if not st.session_state.authenticated and not st.session_state.get("show_login"):
    # Historia 001: la plataforma se puede explorar sin iniciar sesión
    visitor_dashboard()

elif not st.session_state.authenticated:
    st.button(
        "← Volver a explorar",
        key="back_to_visitor",
        on_click=back_to_visitor,
    )

    login_screen()

    st.markdown("---")

    if use_api():
        security_note(
            "Las cuentas se validan en el backend de Overol mediante tokens JWT. "
            "Las demás funciones del prototipo todavía usan la base local."
        )
    else:
        security_note(
            "El prototipo utiliza autenticación local y contraseñas almacenadas "
            "mediante PBKDF2 con salt aleatorio. Los controles de seguridad "
            "definitivos deben reforzarse al implementar el backend productivo."
        )

else:
    user = get_user(st.session_state.user_id)

    # Si la cuenta fue eliminada o suspendida mientras la sesión seguía abierta,
    # se cierra la sesión de inmediato.
    if not user or not user["active"]:
        delete_session(st.session_state.get("session_token"))
        st.session_state.clear()
        st.session_state["_clear_cookie"] = True
        flash("Tu sesión fue cerrada: la cuenta no está activa.", "warning")
        st.rerun()

    # Solo los clientes pueden ver perfiles individuales de profesionales y agendar:
    # a profesionales y administradores se les descarta cualquier enlace ?profesional=
    if user["role"] != "cliente" and "profesional" in st.query_params:
        del st.query_params["profesional"]

    profile = get_user_profile(user["id"])

    # Clientes y profesionales deben completar sus datos personales
    # antes de acceder al resto de la plataforma. El administrador no necesita
    # este paso para poder entrar al panel administrativo.
    if user["role"] in ("cliente", "profesional") and not profile:
        personal_questions_screen(user)
    else:
        sidebar(user)

        if user["role"] == "cliente":
            client_dashboard(user)

        elif user["role"] == "profesional":
            professional_dashboard(user)

        elif user["role"] == "admin":
            admin_dashboard(user)


# Escribe o borra la cookie de sesión persistente cuando corresponde
render_cookie_script()


# ============================================================
# 5. PIE
# ============================================================

st.divider()

st.markdown(
    """
    <div class="overol-footer">
        OVEROL · Proyecto de Título · Equipo NXBe<br>
        Prototipo funcional para demostración de requisitos
    </div>
    """,
    unsafe_allow_html=True,
)
