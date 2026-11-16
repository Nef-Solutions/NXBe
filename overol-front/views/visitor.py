"""Vistas del rol Visitante (Historias 001 a 004): navegación sin iniciar sesión."""

import streamlit as st

from ui.components import nav_bar
from views.about import about_page
from views.client import client_search
from views.home import home_page
from views.payments import RETURN_KEY
from views.shared import apply_deeplink, close_professional, go_login_button

NAV_KEY = "visitor_navigation"
PREV_KEY = "_visitor_prev_menu"
INICIO = "🏠 Inicio"
PROFESIONALES = "🔎 Profesionales"
QUIENES = "ℹ️ Quiénes somos"
OPCIONES = [INICIO, PROFESIONALES, QUIENES]


def _leave_login(option):
    # Callback: desde la pantalla de ingreso, vuelve a explorar en la sección elegida
    st.session_state.pop("show_login", None)
    st.session_state.pop(RETURN_KEY, None)  # descarta una vuelta de Webpay sin sesión
    st.session_state[NAV_KEY] = option
    st.session_state[PREV_KEY] = option
    close_professional()


def visitor_login_sidebar():
    """Menú lateral en la pantalla de ingreso: las mismas secciones del visitante (salen de ella)."""
    with st.sidebar:
        st.markdown("## 🦺 Overol")
        st.caption("Explora profesionales sin iniciar sesión.")
        with st.container(key="side_sections"):
            for i, option in enumerate(OPCIONES):
                st.button(option, key=f"side_{NAV_KEY}_btn_{i}", on_click=_leave_login, args=(option,),
                          use_container_width=True)
        st.divider()
        st.button("🔑 Ingresar o registrarme", key="side_login_current", type="primary",
                  use_container_width=True, disabled=True, help="Estás en la pantalla de ingreso")


def visitor_dashboard():
    # ?profesional=ID abre directamente el perfil de ese profesional
    apply_deeplink(NAV_KEY, PROFESIONALES, PREV_KEY)

    # ---------------- Navegación (menú lateral) ----------------
    menu = nav_bar(
        NAV_KEY,
        OPCIONES,
        extra=lambda: go_login_button("go_login_top", "🔑 Ingresar o registrarme"),
    )

    # Al cambiar de sección se descarta el perfil abierto
    if st.session_state.get(PREV_KEY) != menu:
        close_professional()
        st.session_state[PREV_KEY] = menu

    if menu == INICIO:
        home_page(None, NAV_KEY, PREV_KEY, PROFESIONALES)

    elif menu == PROFESIONALES:
        client_search(None)

    elif menu == QUIENES:
        about_page()
