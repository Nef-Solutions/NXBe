"""Portada de Overol: presentación, cifras, categorías, cómo funciona y profesionales destacados."""

import streamlit as st

from core import api_client, catalog_api
from ui.components import format_professional_card, hero, metric_card, section
from views.shared import (
    category_buttons,
    go_login_button,
    open_professional,
)

PASOS = [
    ("1", "Describe tu necesidad", "Elige un oficio o busca por palabra clave."),
    ("2", "Compara profesionales", "Revisa experiencia, especialidades, cobertura y opiniones."),
    ("3", "Solicita una visita", "Envía tu solicitud al profesional que prefieras."),
    ("4", "Coordina y evalúa", "Cuando acepta, tienes su contacto. Al terminar, lo evalúas."),
]


def _open_from_home(nav_key, prev_key, target, professional_id):
    # Callback: cambia de sección y abre el perfil sin que el menú lo descarte.
    st.session_state[nav_key] = target
    st.session_state[prev_key] = target
    open_professional(professional_id)


def home_page(role, nav_key, prev_key, search_target, show_hero=True):
    """`role` es None para visitantes."""
    anonymous = role is None

    try:
        professionals = catalog_api.list_professionals(anonymous=anonymous)
    except api_client.ApiError:
        professionals = []  # sin backend, la portada se muestra sin cifras ni destacados

    # ---------------- Portada ----------------
    if show_hero:
        hero(
            "Encuentra al profesional ideal para tu hogar",
            "Plomeros, electricistas, carpinteros, pintores y maestros verificados "
            "por Overol. Compara perfiles, solicita una visita y evalúa el servicio.",
        )

    # ---------------- Cifras reales (del catálogo del backend) ----------------
    # «Opiniones de clientes» vuelve cuando el backend entregue la cantidad (PEDIDO 5.3)
    if professionals:
        trades = {t["trade"] for p in professionals for t in catalog_api.trades(p)}
        communes = {c for p in professionals for c in p["coverage"].split(",") if c}
        cols = st.columns(3)
        for col, (icon, label, value) in zip(
            cols,
            [
                ("👷", "Profesionales verificados", len(professionals)),
                ("🧰", "Oficios disponibles", len(trades)),
                ("📍", "Comunas con cobertura", len(communes)),
            ],
        ):
            with col:
                metric_card(value, label, icon)

    # ---------------- Categorías ----------------
    section("🧰 ¿Qué necesitas arreglar?")
    st.caption("Elige un oficio para ver a los profesionales disponibles.")
    category_buttons(nav_key, search_target)

    # ---------------- Cómo funciona ----------------
    section("¿Cómo funciona Overol?")

    cols = st.columns(4)
    for col, (number, title, description) in zip(cols, PASOS):
        with col:
            st.markdown(
                f"""<div class="card"><div class="step-number">{number}</div><h3>{title}</h3><div class="muted">{description}</div></div>""",
                unsafe_allow_html=True,
            )

    # ---------------- Destacados ----------------
    featured = sorted(professionals, key=lambda p: catalog_api.rating(p)[1], reverse=True)[:3]

    if featured:
        section("⭐ Profesionales destacados")

        with st.container(key=f"pro_grid_home_{nav_key}"):
            cols = st.columns(3)
        for col, professional in zip(cols, featured):
            with col:
                format_professional_card(professional, anonymous=anonymous)
                st.button(
                    "Ver perfil",
                    key=f"home_feat_{nav_key}_{professional['id']}",
                    use_container_width=True,
                    on_click=_open_from_home,
                    args=(nav_key, prev_key, search_target, professional["id"]),
                )

    if anonymous:
        st.divider()
        st.markdown("#### ¿Listo para solicitar una visita?")
        st.caption("Crea tu cuenta gratis para contactar profesionales y hacer seguimiento de tus servicios.")
        go_login_button("go_login_home", "Crear mi cuenta gratis")
