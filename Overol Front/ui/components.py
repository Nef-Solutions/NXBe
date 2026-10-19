"""Componentes visuales reutilizables (hero, secciones, badges, tarjetas) y carga del CSS."""

import re
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core.constants import APP_DIR
from core.database import get_professional_rating, get_trades

# Clase CSS del badge según el estado (ver style.css)
BADGE_CLASSES = {
    "Pendiente": "badge-warn",
    "En revisión": "badge-warn",
    "Abierto": "badge-warn",
    "En mediación": "badge-info",
    "Aceptada": "badge-info",
    "Aprobado": "badge-ok",
    "Finalizada": "badge-ok",
    "Resuelto": "badge-ok",
    "Activo": "badge-ok",
    "Rechazada": "badge-bad",
    "Rechazado": "badge-bad",
    "Cancelada": "badge-bad",
    "Suspendido": "badge-bad",
    "Vencida": "badge-muted",
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


def format_professional_card(professional, anonymous=False):
    """
    Tarjeta resumen del profesional (lista de resultados), con mini portada.
    anonymous=True (visitantes): no muestra nombre ni apellido (Historia 003).
    """
    total, average = get_professional_rating(professional["id"])
    trades = get_trades(professional["id"])

    headline = " · ".join(t["trade"] for t in trades[:3])
    if len(trades) > 3:
        headline += f" · +{len(trades) - 3}"

    specialties = [
        x.strip()
        for t in trades
        for x in (t["specialties"] or "").split(",")
        if x.strip()
    ]
    specialty_chips = "".join(
        f'<span class="chip">{escape(s)}</span>' for s in specialties[:4]
    )

    coverage = [
        x.strip() for x in professional["coverage"].split(",") if x.strip()
    ]
    coverage_text = escape(", ".join(coverage)) if coverage else "Sin cobertura definida"

    if total:
        rating_html = (
            f'<span class="stars">{stars(average)}</span> '
            f'<b>{average}</b> <span class="muted">· {total} opiniones</span>'
        )
    else:
        rating_html = '<span class="muted">Aún sin opiniones</span>'

    fee = escape(professional["visit_fee"]) if professional["visit_fee"] else "Por definir"
    schedule = escape(professional["schedule"]) if professional["schedule"] else ""

    about = (professional["about"] or "").strip()
    if len(about) > 110:
        about = about[:107].rstrip() + "…"
    about_html = f'<div class="pro-about">{escape(about)}</div>' if about else ""

    if anonymous:
        title = f'Profesional #{professional["id"]}'
        avatar = "🦺"
    else:
        title = professional["name"]
        avatar = initials(professional["name"])

    st.markdown(
        _html(
            f"""
            <div class="card pro-card">
                <div class="mini-cover"></div>
                <div class="pro-card-body">
                    <div class="mini-avatar">{escape(avatar)}</div>
                    <h3>{escape(title)}</h3>
                    <div class="pro-headline">{escape(headline)}</div>
                    <div class="verified">✓ Identidad verificada</div>
                    {about_html}
                    <div class="chips">{specialty_chips}</div>
                    <div class="pro-meta">📍 {coverage_text}</div>
                    {f'<div class="pro-meta">🕘 {schedule}</div>' if schedule else ''}
                    <div class="pro-rating">{rating_html}</div>
                    <div class="pro-fee">💰 Visita: <b>{fee}</b></div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def contact_box(contact, title):
    """Datos de contacto habilitados tras aceptar la solicitud (Historias 011 y 022)."""
    if not contact:
        return

    phone = contact["phone"] or ""
    digits = re.sub(r"\D", "", phone)

    links = ""
    if digits:
        links += (
            f' · <a href="https://wa.me/{digits}" target="_blank">WhatsApp</a>'
            f' · <a href="tel:+{digits}">Llamar</a>'
        )
    links += f' · <a href="mailto:{escape(contact["email"])}">Escribir correo</a>'

    st.markdown(
        _html(
            f"""
            <div class="contact-box">
                <b>📇 {escape(title)}</b><br>
                👤 {escape(contact["name"])}<br>
                📱 {escape(phone) or "Teléfono no informado"}<br>
                ✉️ {escape(contact["email"])}<br>
                💬 Prefiere contacto por: {escape(contact["contact_preference"] or "no indicado")}<br>
                <span class="muted">Coordinen directamente el servicio{links}</span>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


ROLE_CHIPS = {
    None: ("👤 Visitante", "visitante"),
    "cliente": ("🏠 Cliente", "cliente"),
    "profesional": ("🛠️ Profesional", "profesional"),
    "admin": ("🛡️ Administrador", "admin"),
}


def navbar(user=None):
    """Barra superior: marca, lema y distintivo del tipo de usuario conectado."""
    label, css = ROLE_CHIPS.get(user["role"] if user else None, ROLE_CHIPS[None])
    name = f" · {escape(user['name'])}" if user else ""

    st.markdown(
        _html(
            f"""
            <div class="navbar">
                <span class="logo">🦺 OVEROL</span>
                <span class="tagline">Marketplace de profesionales para el hogar</span>
                <span class="nav-spacer"></span>
                <span class="role-chip role-{css}">{label}{name}</span>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Botón «mantén presionado para confirmar» (componente propio)
# ------------------------------------------------------------

_HOLD_BUTTON = components.declare_component(
    "hold_to_confirm",
    path=str(APP_DIR / "ui" / "hold_button"),
)


def hold_to_confirm(key, label="Mantén presionado para confirmar", seconds=1.8):
    """
    Botón que solo confirma si el usuario lo mantiene apretado; mientras tanto se llena
    como una barra de carga. Devuelve True UNA sola vez, cuando se completó la pausa.
    """
    value = _HOLD_BUTTON(label=label, seconds=seconds, key=key, default=None)
    done_key = f"_hold_done_{key}"

    if value and st.session_state.get(done_key) != value:
        st.session_state[done_key] = value
        return True

    return False


# ------------------------------------------------------------
# Mensajes a soporte
# ------------------------------------------------------------

def support_box(user, request_id, role_label):
    """
    Conversación con soporte (administrador) sobre una solicitud.
    `role_label` distingue las claves de widgets entre cliente y profesional.
    """
    from core.constants import MAX_TEXTO
    from core.database import add_support_message, audit, get_support_thread

    thread = get_support_thread(request_id, user["id"])
    suffix = f" ({len(thread)} mensajes)" if thread else ""

    with st.expander(f"💬 Contactar a soporte{suffix}"):
        if not thread:
            st.caption(
                "Escribe aquí si tienes un problema con esta solicitud. "
                "El equipo de Overol te responderá en este mismo lugar."
            )

        for message in thread:
            who = "Soporte Overol" if message["from_admin"] else "Tú"
            css = "support-admin" if message["from_admin"] else "support-user"
            st.markdown(
                _html(
                    f"""
                    <div class="support-msg {css}">
                        <div class="who">{who} · {escape(message["created_at"])}</div>
                        <div>{escape(message["body"])}</div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

        with st.form(f"support_form_{role_label}_{request_id}", clear_on_submit=True):
            body = st.text_area(
                "Tu mensaje para soporte",
                max_chars=MAX_TEXTO,
                placeholder="Cuéntanos qué ocurrió con esta solicitud.",
                key=f"support_text_{role_label}_{request_id}",
            )
            sent = st.form_submit_button(
                "Enviar a soporte",
                use_container_width=True,
                key=f"support_send_{role_label}_{request_id}",
            )

        if sent:
            ok, error = add_support_message(request_id, user["id"], body)

            if not ok:
                st.error(error)
            else:
                audit(user["id"], "SUPPORT_MESSAGE", "requests", request_id,
                      "Mensaje enviado a soporte")
                flash("Mensaje enviado a soporte.")
                st.rerun()
