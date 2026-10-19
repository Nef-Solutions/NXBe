"""Vistas del rol Visitante (Historias 001 a 004): navegación sin iniciar sesión."""

import streamlit as st

from views.about import about_page
from views.client import client_chatbot, client_search
from views.home import home_page
from views.shared import apply_deeplink, close_professional, go_login_button

NAV_KEY = "visitor_navigation"
PREV_KEY = "_visitor_prev_menu"
INICIO = "🏠 Inicio"
PROFESIONALES = "🔎 Profesionales"
ASISTENTE = "🤖 Asistente"
QUIENES = "ℹ️ Quiénes somos"


def visitor_dashboard():
    # ?profesional=ID abre directamente el perfil de ese profesional
    apply_deeplink(NAV_KEY, PROFESIONALES, PREV_KEY)

    # ---------------- Barra de navegación ----------------
    nav_col, login_col = st.columns([5, 1.4])

    with nav_col:
        menu = st.radio(
            "Navegación",
            [INICIO, PROFESIONALES, ASISTENTE, QUIENES],
            horizontal=True,
            key=NAV_KEY,
            label_visibility="collapsed",
        )

    with login_col:
        go_login_button("go_login_top", "🔑 Ingresar o registrarme")

    # Al cambiar de sección se descarta el perfil abierto
    if st.session_state.get(PREV_KEY) != menu:
        close_professional()
        st.session_state[PREV_KEY] = menu

    if menu == INICIO:
        home_page(None, NAV_KEY, PREV_KEY, PROFESIONALES, ASISTENTE)

    elif menu == PROFESIONALES:
        client_search(None)

    elif menu == ASISTENTE:
        client_chatbot(None)

    elif menu == QUIENES:
        about_page()
