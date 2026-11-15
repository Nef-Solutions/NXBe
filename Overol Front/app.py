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

Todos los datos vienen del backend Django del equipo (API REST con JWT).
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
def running_inside_streamlit():
    """True si este archivo ya lo está ejecutando un servidor Streamlit (streamlit run,
    Streamlit Community Cloud), aunque no se haya definido OVEROL_STREAMLIT_STARTED."""
    try:
        from streamlit import runtime

        return runtime.exists()
    except Exception:
        return False


if os.environ.get(BOOTSTRAP_ENV) != "1" and not running_inside_streamlit():
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
    initial_sidebar_state="auto",
)

from core.session import (
    current_user,
    end_session,
    is_profile_complete,
    render_cookie_script,
    restore_session,
)
from ui.components import flash, load_css, navbar, security_note, show_flash
from views.admin import admin_dashboard
from views import payments
from views.auth import login_screen
from views.client import client_dashboard
from views.professional import professional_dashboard
from views.shared import close_professional, personal_questions_screen, sidebar
from views.visitor import visitor_dashboard


# ============================================================
# 2. ESTILOS Y SESIÓN
# ============================================================

load_css()

# Todos los datos vienen del backend Django; el front ya no crea ni usa overol.db.
# Vuelta de Webpay (?status=...): se guarda antes de que la URL se limpie.
payments.capture_payment_return()

# Si el navegador trae una sesión persistente vigente, se restaura sin pedir la contraseña.
restore_session()


def back_to_visitor():
    """Callback del botón «Volver a explorar»: regresa siempre a la portada del visitante.
    Se ejecuta antes de redibujar la página, por eso no depende de st.rerun()."""
    st.session_state.pop("show_login", None)
    st.session_state.pop(payments.RETURN_KEY, None)  # descarta una vuelta de Webpay sin sesión
    st.session_state["visitor_navigation"] = "🏠 Inicio"
    st.session_state["_visitor_prev_menu"] = "🏠 Inicio"
    close_professional()


# ============================================================
# 3. CABECERA
# ============================================================

_session_user = current_user()

# Sesión vencida o cuenta suspendida mientras la sesión seguía abierta: se cierra
if st.session_state.get("authenticated") and not _session_user:
    end_session()
    flash("Tu sesión terminó. Vuelve a iniciar sesión.", "warning")
    st.rerun()

# Tras volver de Webpay: el resultado se muestra en la pantalla del pago. Sin sesión
# (no marcó «Mantener mi sesión»), primero se le pide ingresar.
if payments.pending_return():
    if _session_user:
        payments.route_payment_return(_session_user)
    else:
        st.session_state["show_login"] = True

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

    if payments.pending_return():
        st.info("Volviste de Webpay. Inicia sesión para ver el resultado de tu pago.")

    login_screen()

    st.markdown("---")

    security_note(
        "Las cuentas se validan en el backend de Overol mediante tokens JWT. "
        "Los tokens nunca se guardan en el navegador."
    )

else:
    user = _session_user

    # Solo los clientes pueden ver perfiles individuales de profesionales y agendar:
    # a profesionales y administradores se les descarta cualquier enlace ?profesional=
    if user["role"] != "cliente" and "profesional" in st.query_params:
        del st.query_params["profesional"]

    # Clientes y profesionales deben tener teléfono, dirección y comuna
    # antes de acceder al resto de la plataforma. El administrador no necesita este paso.
    if not is_profile_complete(user):
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
