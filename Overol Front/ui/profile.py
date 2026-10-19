"""
Perfiles con estructura tipo LinkedIn.

  ┌───────────────────────────────────────────┐
  │  PORTADA                                  │
  │  (avatar)  Nombre                         │
  │            Titular · oficios              │
  │            📍 ubicación · ★ valoración    │
  │  [insignias]                              │
  │  [ estadísticas ]                         │
  └───────────────────────────────────────────┘
  Acerca de · Experiencia · Especialidades · Certificaciones ·
  Disponibilidad · Cobertura y tarifa · Opiniones de clientes
"""

from html import escape

import streamlit as st

from core.constants import DIAS_SEMANA, OFICIOS_INFO
from core.database import (
    get_client_stats,
    get_professional_rating,
    get_professional_stats,
    get_public_reviews,
    get_trades,
)
from ui.components import _html, initials, stars

TRADE_ICONS = {trade: icon for icon, trade, _ in OFICIOS_INFO}


def _chips(items, css=""):
    return "".join(f'<span class="chip {css}">{escape(i)}</span>' for i in items)


def _split(text):
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def _section(title, icon, body_html):
    st.markdown(
        _html(
            f"""
            <div class="psection">
                <h3><span class="psection-icon">{icon}</span>{escape(title)}</h3>
                {body_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Cabecera del profesional
# ------------------------------------------------------------

def profile_header(professional, anonymous=False):
    stats = get_professional_stats(professional["id"])
    trades = get_trades(professional["id"])
    coverage = _split(professional["coverage"])

    name = f'Profesional #{professional["id"]}' if anonymous else professional["name"]
    avatar = "🦺" if anonymous else initials(professional["name"])

    headline = " · ".join(t["trade"] for t in trades[:3])
    if len(trades) > 3:
        headline += f" · +{len(trades) - 3}"

    if coverage:
        place = coverage[0] + (f" y {len(coverage) - 1} comunas más" if len(coverage) > 1 else "")
        location = f"📍 {escape(place)}"
    else:
        location = "📍 Cobertura por definir"

    if stats["reviews"]:
        rating = (
            f'<span class="stars">{stars(stats["average"])}</span> '
            f'<b>{stats["average"]}</b> '
            f'<span class="muted">· {stats["reviews"]} opiniones</span>'
        )
    else:
        rating = '<span class="muted">Aún sin opiniones</span>'

    badges = []
    if professional["verified"]:
        badges.append('<span class="pbadge pbadge-ok">✓ Identidad verificada</span>')
    else:
        badges.append('<span class="pbadge pbadge-warn">⏳ Verificación pendiente</span>')
    badges.append(
        '<span class="pbadge pbadge-ok">🟢 Disponible</span>'
        if professional["availability"]
        else '<span class="pbadge pbadge-bad">🔴 No disponible</span>'
    )
    if stats["member_since"]:
        badges.append(f'<span class="pbadge">Miembro desde {escape(stats["member_since"])}</span>')

    years = f'{stats["years"]}' if stats["years"] is not None else "—"

    st.markdown(
        _html(
            f"""
            <div class="profile-card">
                <div class="profile-cover"></div>
                <div class="profile-body">
                    <div class="profile-avatar">{escape(avatar)}</div>
                    <h1>{escape(name)}</h1>
                    <div class="profile-headline">{escape(headline) or "Profesional"}</div>
                    <div class="profile-meta">{location}</div>
                    <div class="profile-rating">{rating}</div>
                    <div class="profile-badges">{"".join(badges)}</div>
                    <div class="profile-stats">
                        <div class="pstat"><div class="pstat-n">{stats["finished"]}</div><div class="pstat-l">Servicios finalizados</div></div>
                        <div class="pstat"><div class="pstat-n">{stats["reviews"]}</div><div class="pstat-l">Opiniones</div></div>
                        <div class="pstat"><div class="pstat-n">{escape(years)}</div><div class="pstat-l">Años de experiencia</div></div>
                    </div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Secciones del profesional
# ------------------------------------------------------------

def profile_sections(professional, owner=False):
    """Secciones del perfil. `owner=True` muestra textos guía en lo que aún está vacío."""
    trades = get_trades(professional["id"])

    # ---------- Acerca de ----------
    about = (professional["about"] or "").strip()
    if about:
        _section("Acerca de", "📝", f'<p class="pabout">{escape(about)}</p>')
    elif owner:
        _section(
            "Acerca de", "📝",
            '<p class="muted">Aún no escribes tu presentación. Cuéntales a los clientes '
            "quién eres y cómo trabajas.</p>",
        )

    # ---------- Experiencia (una entrada por oficio) ----------
    entries = ""
    for trade in trades:
        total, average = get_professional_rating(professional["id"], trade["trade"])
        years = (
            f'{trade["years_experience"]} años de experiencia'
            if trade["years_experience"] is not None
            else "Experiencia no informada"
        )
        rating = (
            f'<span class="stars">{stars(average)}</span> <b>{average}</b> '
            f'<span class="muted">· {total} evaluaciones</span>'
            if total
            else '<span class="muted">Aún sin evaluaciones</span>'
        )
        specs = _chips(_split(trade["specialties"]))
        entries += (
            '<div class="exp-item">'
            f'<div class="exp-icon">{TRADE_ICONS.get(trade["trade"], "🛠️")}</div>'
            '<div class="exp-body">'
            f'<div class="exp-title">{escape(trade["trade"])}</div>'
            f'<div class="exp-sub">{escape(years)}</div>'
            f'<div class="exp-rating">{rating}</div>'
            f'<div class="chips">{specs}</div>'
            "</div></div>"
        )
    if entries:
        _section("Experiencia", "🧰", entries)

    # ---------- Especialidades (aptitudes) ----------
    skills = []
    for trade in trades:
        skills += _split(trade["specialties"])
    if skills:
        _section("Especialidades", "⚙️", f'<div class="chips">{_chips(dict.fromkeys(skills))}</div>')
    elif owner:
        _section(
            "Especialidades", "⚙️",
            '<p class="muted">Agrega tus especialidades en «Editar mi perfil → Oficios y experiencia».</p>',
        )

    # ---------- Certificaciones ----------
    certs = ""
    for trade in trades:
        if trade["certifications"]:
            certs += (
                '<div class="cert-item">'
                '<div class="cert-icon">🎓</div>'
                f'<div><div class="exp-title">{escape(trade["certifications"])}</div>'
                f'<div class="exp-sub">{escape(trade["trade"])}</div></div>'
                "</div>"
            )
    if certs:
        _section("Certificaciones", "🏅", certs)
    elif owner:
        _section(
            "Certificaciones", "🏅",
            '<p class="muted">Aún no registras certificaciones.</p>',
        )

    # ---------- Disponibilidad ----------
    work_days = _split(professional["work_days"])
    day_pills = "".join(
        f'<span class="dpill {"dpill-on" if d in work_days else ""}">{d}</span>'
        for d in DIAS_SEMANA
    )
    hours = (
        f'{professional["work_start"]} a {professional["work_end"]}'
        if professional["work_start"]
        else "No informado"
    )
    state = "🟢 Disponible para recibir solicitudes" if professional["availability"] else "🔴 No disponible por ahora"
    _section(
        "Disponibilidad", "📅",
        f'<div class="plabel">Días disponibles</div><div class="dpills">{day_pills}</div>'
        f'<div class="plabel">Horario</div><div>🕘 {escape(hours)}</div>'
        f'<div class="plabel">Estado</div><div>{state}</div>',
    )

    # ---------- Cobertura y tarifa ----------
    coverage = _split(professional["coverage"])
    _section(
        "Cobertura y tarifa", "📍",
        '<div class="plabel">Zona de cobertura</div>'
        f'<div class="chips">{_chips(coverage, "chip-trade") if coverage else "<span class=muted>Sin cobertura definida</span>"}</div>'
        '<div class="plabel">Tarifa de visita</div>'
        f'<div><b>{escape(professional["visit_fee"] or "Por definir")}</b></div>',
    )


# ------------------------------------------------------------
# Opiniones (estilo «recomendaciones»)
# ------------------------------------------------------------

def profile_reviews(professional_id):
    reviews = get_public_reviews(professional_id)

    if not reviews:
        _section(
            "Opiniones de clientes", "💬",
            '<p class="muted">Aún no hay opiniones con comentario.</p>',
        )
        return

    body = ""
    for review in reviews:
        average = round(
            (review["quality"] + review["punctuality"] + review["treatment"]) / 3, 1
        )
        body += (
            '<div class="reco">'
            '<div class="reco-avatar">C</div>'
            '<div class="reco-body">'
            f'<div><span class="stars">{stars(average)}</span> <b>{average}</b> '
            f'<span class="chip chip-trade">{escape(review["trade"] or "Servicio")}</span></div>'
            f'<div class="reco-text">“{escape(review["comment"])}”</div>'
            '<div class="who">Cliente de Overol</div>'
            "</div></div>"
        )
    _section("Opiniones de clientes", "💬", body)


# ------------------------------------------------------------
# Cabecera del perfil personal (cliente / profesional)
# ------------------------------------------------------------

def profile_user_header(user, profile):
    stats = get_client_stats(user["id"])
    role = "Cliente" if user["role"] == "cliente" else "Profesional"
    commune = profile["commune"] if profile and profile["commune"] else ""
    place = f"📍 {escape(commune)}" if commune else ""

    badges = f'<span class="pbadge">{role}</span>'
    if stats["member_since"]:
        badges += f'<span class="pbadge">Miembro desde {escape(stats["member_since"])}</span>'

    stat_html = ""
    if user["role"] == "cliente":
        stat_html = (
            '<div class="profile-stats">'
            f'<div class="pstat"><div class="pstat-n">{stats["requests"]}</div><div class="pstat-l">Solicitudes</div></div>'
            f'<div class="pstat"><div class="pstat-n">{stats["finished"]}</div><div class="pstat-l">Servicios finalizados</div></div>'
            f'<div class="pstat"><div class="pstat-n">{stats["rated"]}</div><div class="pstat-l">Evaluaciones realizadas</div></div>'
            "</div>"
        )

    st.markdown(
        _html(
            f"""
            <div class="profile-card">
                <div class="profile-cover"></div>
                <div class="profile-body">
                    <div class="profile-avatar">{escape(initials(user["name"]))}</div>
                    <h1>{escape(user["name"])}</h1>
                    <div class="profile-headline">{role} en Overol</div>
                    <div class="profile-meta">{place}</div>
                    <div class="profile-badges">{badges}</div>
                    {stat_html}
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
