"""Portada de Overol: presentación, cifras, categorías, cómo funciona y profesionales destacados."""

import streamlit as st

from core.database import get_all_professionals, get_platform_stats, get_professional_rating
from ui.components import format_professional_card, hero, metric_card, section
from views.shared import (
    category_buttons,
    go_login_button,
    go_to,
    open_professional,
)

PASOS = [
    ("1", "Describe tu necesidad", "Elige un oficio o cuéntale tu problema al asistente."),
    ("2", "Compara profesionales", "Revisa experiencia, especialidades, cobertura y opiniones."),
    ("3", "Solicita una visita", "Envía tu solicitud al profesional que prefieras."),
    ("4", "Coordina y evalúa", "Cuando acepta, tienes su contacto. Al terminar, lo evalúas."),
]


def _open_from_home(nav_key, prev_key, target, professional_id):
    # Callback: cambia de sección y abre el perfil sin que el menú lo descarte.
    st.session_state[nav_key] = target
    st.session_state[prev_key] = target
    open_professional(professional_id)


def home_page(role, nav_key, prev_key, search_target, assistant_target, show_hero=True):
    """`role` es None para visitantes."""
    anonymous = role is None
    stats = get_platform_stats()

    # ---------------- Portada ----------------
    if show_hero:
        hero(
            "Encuentra al profesional ideal para tu hogar",
            "Plomeros, electricistas, carpinteros, pintores y maestros verificados "
            "por Overol. Compara perfiles, solicita una visita y evalúa el servicio.",
        )

    c1, c2, _ = st.columns([1, 1, 2])

    with c1:
        st.button(
            "🔎 Buscar profesionales",
            type="primary",
            use_container_width=True,
            key=f"home_search_{nav_key}",
            on_click=go_to,
            args=(nav_key, search_target),
        )

    with c2:
        if anonymous:
            go_login_button("go_login_hero", "Crear mi cuenta gratis")
        else:
            st.button(
                "🤖 Probar el asistente",
                use_container_width=True,
                key=f"home_assistant_{nav_key}",
                on_click=go_to,
                args=(nav_key, assistant_target),
            )

    # ---------------- Cifras reales ----------------
    cols = st.columns(4)
    for col, (icon, label, value) in zip(
        cols,
        [
            ("👷", "Profesionales verificados", stats["professionals"]),
            ("🧰", "Oficios disponibles", stats["trades"]),
            ("📍", "Comunas con cobertura", stats["communes"]),
            ("⭐", "Opiniones de clientes", stats["reviews"]),
        ],
    ):
        with col:
            metric_card(value, label, icon)

    # ---------------- Categorías ----------------
    section("🧰 ¿Qué necesitas arreglar?")
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
    featured = sorted(
        get_all_professionals(),
        key=lambda p: get_professional_rating(p["id"])[1],
        reverse=True,
    )[:3]

    if featured:
        section("⭐ Profesionales destacados")

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
