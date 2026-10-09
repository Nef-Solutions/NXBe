"""Componentes visuales reutilizables (hero, secciones, badges, tarjetas) y carga del CSS."""

from html import escape
from pathlib import Path

import streamlit as st

from core.constants import APP_DIR
from core.database import get_professional_rating

# Clase CSS del badge según el estado (ver style.css)
BADGE_CLASSES = {
    "Pendiente": "badge-warn",
    "En revisión": "badge-warn",
    "Abierto": "badge-warn",
    "En mediación": "badge-info",
    "Aceptada": "badge-info",
    "Aprobado": "badge-ok",
    "Completada": "badge-ok",
    "Resuelto": "badge-ok",
    "Activo": "badge-ok",
    "Rechazada": "badge-bad",
    "Rechazado": "badge-bad",
    "Cancelada": "badge-bad",
    "Suspendido": "badge-bad",
    "Cerrado": "badge-muted",
}


def _html(markup: str) -> str:
    """Compacta el HTML en una línea: evita que Markdown lo interprete como bloque de código."""
    return "".join(line.strip() for line in markup.splitlines())


def load_css(path=None):
    """Lee style.css (ubicado en la raíz del proyecto) y lo inyecta en la app."""
    css_path = Path(path) if path else APP_DIR / "style.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------
# Mensajes que sobreviven a st.rerun()
# ------------------------------------------------------------

def flash(message, kind="success"):
    """Encola un mensaje para mostrarlo tras el próximo st.rerun()."""
    st.session_state.setdefault("_flash", []).append((message, kind))


def show_flash():
    """Muestra (y vacía) los mensajes encolados. Se llama una vez por ejecución."""
    icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
    for message, kind in st.session_state.pop("_flash", []):
        st.toast(message, icon=icons.get(kind, "✅"))


# ------------------------------------------------------------
# Bloques visuales
# ------------------------------------------------------------

def hero(title, text):
    st.markdown(
        _html(
            f"""
            <div class="hero">
                <h1>{escape(title)}</h1>
                <p>{escape(text)}</p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(
        f'<div class="section-title">{escape(title)}</div>',
        unsafe_allow_html=True,
    )


def status_badge(status):
    css_class = BADGE_CLASSES.get(status, "badge-muted")
    st.markdown(
        f'<span class="badge {css_class}">{escape(str(status))}</span>',
        unsafe_allow_html=True,
    )


def security_note(text):
    st.markdown(
        _html(
            f"""
            <div class="security-box">
                <b>🔐 Seguridad / privacidad</b><br>
                {escape(text)}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def empty_state(icon, title, text=""):
    """Estado vacío amigable (en lugar de un simple st.info)."""
    st.markdown(
        _html(
            f"""
            <div class="empty-state">
                <div class="empty-icon">{icon}</div>
                <div class="empty-title">{escape(title)}</div>
                <div class="muted">{escape(text)}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def metric_card(value, label, icon=""):
    st.markdown(
        _html(
            f"""
            <div class="metric-card">
                <div class="metric-icon">{icon}</div>
                <div class="metric-number">{escape(str(value))}</div>
                <div class="metric-label">{escape(label)}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def stars(average):
    """Convierte un promedio (0-5) en estrellas: 4.4 -> ★★★★☆"""
    full = max(0, min(5, round(average)))
    return "★" * full + "☆" * (5 - full)


def initials(name):
    parts = [p for p in str(name).split() if p]
    letters = [next((c for c in p if c.isalpha()), "") for p in parts[:2]]
    return "".join(letters).upper() or "?"


def format_professional_card(professional):
    total, average = get_professional_rating(professional["id"])

    specialties = [
        x.strip() for x in professional["specialties"].split(",") if x.strip()
    ]
    coverage = [
        x.strip() for x in professional["coverage"].split(",") if x.strip()
    ]

    chips = "".join(
        f'<span class="chip">{escape(s)}</span>' for s in specialties
    )
    coverage_text = escape(", ".join(coverage)) if coverage else "Sin cobertura definida"

    if total:
        rating_html = (
            f'<span class="stars">{stars(average)}</span> '
            f'<b>{average}</b> <span class="muted">· {total} evaluaciones</span>'
        )
    else:
        rating_html = '<span class="muted">Aún sin evaluaciones</span>'

    fee = escape(professional["visit_fee"]) if professional["visit_fee"] else "Por definir"

    st.markdown(
        _html(
            f"""
            <div class="card pro-card">
                <div class="pro-head">
                    <div class="avatar">{escape(initials(professional["name"]))}</div>
                    <div>
                        <h3>{escape(professional["name"])}</h3>
                        <div class="verified">✓ Identidad verificada</div>
                    </div>
                </div>
                <div class="pro-trade">{escape(professional["trade"])}</div>
                <div class="chips">{chips}</div>
                <div class="pro-meta">📍 {coverage_text}</div>
                <div class="pro-rating">{rating_html}</div>
                <div class="pro-fee">💰 Visita: <b>{fee}</b></div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
