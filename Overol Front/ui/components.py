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


def _set_section(nav_key, option):
    # Callback: cambia de sección antes de redibujar la página.
    st.session_state[nav_key] = option


def nav_bar(nav_key, options, extra=None, badges=None):
    """
    Barra de secciones fija bajo la cabecera (estilo en style.css, «st-key-nav_bar_»).
    Un botón por opción; el de la sección actual va en ámbar (type="primary").
    La sección elegida se guarda en st.session_state[nav_key], igual que antes con st.radio,
    por lo que los callbacks que cambian de sección (go_to, deeplinks) siguen funcionando.
    `extra` es una función opcional que dibuja un botón más al final (p. ej. «Ingresar»).
    `badges` ({opción: número}) agrega un contador a la etiqueta, p. ej. «🔔 Notificaciones (2)»;
    el valor guardado sigue siendo la opción sin contador.
    Devuelve la opción seleccionada.
    """
    if st.session_state.get(nav_key) not in options:
        st.session_state[nav_key] = options[0]

    current = st.session_state[nav_key]

    with st.container(key=f"nav_bar_{nav_key}"):
        cols = st.columns(len(options) + (1 if extra else 0))

        for i, (col, option) in enumerate(zip(cols, options)):
            with col:
                count = (badges or {}).get(option)
                # Con contador, espacios no separables: «🔔 Notificaciones (2)» queda en una línea
                label = f"{option} ({count})".replace(" ", "\u00a0") if count else option
                st.button(
                    label,
                    key=f"{nav_key}_btn_{i}",
                    type="primary" if option == current else "secondary",
                    on_click=_set_section,
                    args=(nav_key, option),
                    use_container_width=True,
                )

        if extra:
            with cols[-1]:
                extra()

    return current


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

def notifications_page(user):
    """Lista de notificaciones del usuario (cliente o profesional) con «marcar como leída»."""
    from core.database import get_notifications, mark_all_notifications_read, mark_notification_read

    section("🔔 Notificaciones")

    items = get_notifications(user["id"])

    if not items:
        empty_state(
            "🔔",
            "No tienes notificaciones",
            "Aquí verás los cambios de tus solicitudes y las respuestas de soporte.",
        )
        return

    unread = sum(1 for item in items if not item["is_read"])

    if unread:
        # Los callbacks marcan antes de redibujar, así el contador de la barra se actualiza al tiro.
        st.button(
            f"Marcar todas como leídas ({unread})",
            key="notif_read_all",
            on_click=mark_all_notifications_read,
            args=(user["id"],),
        )

    for item in items:
        state = "notif-read" if item["is_read"] else "notif-unread"
        new = "" if item["is_read"] else '<span class="badge badge-warn">Nueva</span> '

        with st.container(border=True, key=f"notif_{item['id']}"):
            st.markdown(
                _html(
                    f"""
                    <div class="notif {state}">
                        <div class="notif-title">{new}{escape(item["title"])}</div>
                        <div>{escape(item["message"])}</div>
                        <div class="when">{escape(item["created_at"])}</div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

            if not item["is_read"]:
                st.button(
                    "Marcar como leída",
                    key=f"notif_read_{item['id']}",
                    on_click=mark_notification_read,
                    args=(item["id"], user["id"]),
                )


def support_box(user, request_id, role_label):
    """
    Conversación con soporte (administrador) sobre una solicitud.
    `role_label` distingue las claves de widgets entre cliente y profesional.
    """
    from core.constants import MAX_ASUNTO, MAX_TEXTO
    from core.database import add_support_message, audit, get_support_thread, get_support_ticket

    thread = get_support_thread(request_id, user["id"])
    ticket = get_support_ticket(request_id, user["id"])

    if ticket:
        count = f"{len(thread)} mensaje" + ("" if len(thread) == 1 else "s")
        title = f"💬 Ticket de soporte #{ticket['id']} · {ticket['status']} ({count})"
    else:
        title = "💬 Contactar a soporte"

    with st.expander(title):
        if not ticket:
            st.caption(
                "Abre un ticket si tienes un problema con esta solicitud. "
                "El equipo de Overol te responderá en este mismo lugar."
            )
        else:
            st.markdown(f"**Asunto:** {escape(ticket['subject'])}", unsafe_allow_html=True)
            status_badge(ticket["status"])

            if ticket["status"] == "Resuelto":
                st.caption("Este ticket está resuelto. Si escribes otro mensaje, se vuelve a abrir.")

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
            subject = None
            if not ticket:
                subject = st.text_input(
                    "Asunto",
                    max_chars=MAX_ASUNTO,
                    placeholder="Ej.: El profesional no llegó a la visita",
                    key=f"support_subject_{role_label}_{request_id}",
                )
            body = st.text_area(
                "Tu mensaje para soporte",
                max_chars=MAX_TEXTO,
                placeholder="Cuéntanos qué ocurrió con esta solicitud.",
                key=f"support_text_{role_label}_{request_id}",
            )
            sent = st.form_submit_button(
                "Abrir ticket" if not ticket else "Enviar a soporte",
                use_container_width=True,
                key=f"support_send_{role_label}_{request_id}",
            )

        if sent:
            ok, error = add_support_message(request_id, user["id"], body, subject=subject)

            if not ok:
                st.error(error)
            else:
                audit(user["id"], "SUPPORT_MESSAGE", "requests", request_id,
                      "Ticket de soporte abierto" if not ticket else "Mensaje enviado a soporte")
                flash("Ticket abierto. Soporte te responderá aquí." if not ticket
                      else "Mensaje enviado a soporte.")
                st.rerun()
