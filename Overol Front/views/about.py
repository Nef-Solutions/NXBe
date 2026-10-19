"""Pestaña «Quiénes somos»: propósito, problema que resolvemos y equipo."""

from html import escape

import streamlit as st

from core.constants import EQUIPO
from ui.components import hero, initials, section


def about_page():
    hero(
        "Quiénes somos",
        "Overol es una plataforma digital que facilita el encuentro entre personas "
        "que necesitan un servicio para el hogar y profesionales que lo ofrecen.",
    )

    section("🎯 El problema que resolvemos")

    left, right = st.columns(2)

    with left:
        st.markdown(
            """<div class="card"><h3>🏠 Para quienes necesitan un servicio</h3><div class="muted">Cuando algo falla en casa, no siempre es fácil encontrar a alguien calificado y de confianza. Eso lleva a contrataciones poco informadas, trabajos mal terminados o cobros excesivos.</div></div>""",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """<div class="card"><h3>🛠️ Para quienes ofrecen su oficio</h3><div class="muted">Muchos profesionales independientes solo cuentan con canales informales para conseguir clientes, lo que los lleva a trabajos mal remunerados o a depender de intermediarios.</div></div>""",
            unsafe_allow_html=True,
        )

    section("💡 Nuestra propuesta")

    cols = st.columns(3)
    pillars = [
        ("🔎", "Buscar y comparar", "Encuentra profesionales por oficio, especialidad y zona de cobertura, con su experiencia y valoraciones a la vista."),
        ("✅", "Confianza", "Los profesionales acreditan su identidad y cada oficio tiene su propia valoración, construida con opiniones reales."),
        ("🤝", "Contacto directo", "Cuando el profesional acepta tu solicitud, ambos pueden coordinar el servicio directamente."),
    ]
    for col, (icon, title, text) in zip(cols, pillars):
        with col:
            st.markdown(
                f"""<div class="card category-card"><div class="icon">{icon}</div><h3>{title}</h3><div class="muted">{text}</div></div>""",
                unsafe_allow_html=True,
            )

    section("👥 Nuestro equipo")

    cols = st.columns(len(EQUIPO))
    for col, (name, role, description) in zip(cols, EQUIPO):
        with col:
            st.markdown(
                "".join(
                    line.strip()
                    for line in f"""
                    <div class="card about-person">
                        <div class="avatar">{escape(initials(name))}</div>
                        <h3>{escape(name)}</h3>
                        <div class="about-role">{escape(role)}</div>
                        <div class="muted">{escape(description)}</div>
                    </div>
                    """.splitlines()
                ),
                unsafe_allow_html=True,
            )

    st.divider()
    st.caption(
        "Proyecto de Título · DUOC UC, Escuela de Informática y Telecomunicaciones · Equipo NXBe."
    )
