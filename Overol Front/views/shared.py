"""Pantallas compartidas entre roles: perfil personal, perfil público del profesional y barra lateral."""

from datetime import datetime
from html import escape

import streamlit as st

from core import api_client
from core.constants import (
    COMUNAS,
    FRANJAS_HORARIAS,
    OFICIOS_INFO,
    PREFERENCIAS_CONTACTO,
    ROLES,
    ZONAS_HOGAR,
    use_api,
)
from core.database import (
    audit,
    create_request,
    get_professional_by_id,
    get_trades,
    get_user,
    get_user_profile,
    next_work_date,
    save_user_profile,
)
from core.security import validate_phone
from core.session import delete_session
from ui.components import flash, section, security_note
from ui.profile import (
    profile_header,
    profile_reviews,
    profile_sections,
    profile_user_header,
)


def _update_profile_api(phone, address, commune):
    """Modo api: envía teléfono, dirección y comuna al backend (lo único que acepta PATCH /me/).
    Devuelve False si falló; en modo local no hace nada y devuelve True."""
    if not use_api():
        return True

    try:
        api_client.update_me(phone, address, commune)
    except api_client.ApiError as error:
        st.error(f"No se pudieron guardar tus datos en el servidor. {error}")
        return False

    return True


def personal_questions_screen(user):
    """Formulario obligatorio inicial para completar el perfil personal."""
    section("👤 Completa tu perfil")

    role_label = ROLES.get(user["role"], user["role"])
    st.info(
        f"Estás ingresando como **{role_label}**. "
        "Antes de entrar a la plataforma necesitamos algunos datos para tu perfil."
    )

    with st.form("personal_profile_form", clear_on_submit=False):
        phone = st.text_input(
            "📱 Número de teléfono",
            placeholder="Ej: +56 9 1234 5678",
            key="profile_phone",
        )

        address = st.text_input(
            "🏠 Dirección",
            placeholder="Ej: Av. Principal 1234",
            key="profile_address",
        )

        commune = st.selectbox(
            "📍 Comuna",
            COMUNAS,
            key="profile_commune",
        )

        contact_preference = st.selectbox(
            "💬 ¿Cómo prefieres que te contacten?",
            PREFERENCIAS_CONTACTO,
            key="profile_contact_preference",
        )

        if user["role"] == "cliente":
            service_interest = st.text_input(
                "🏠 ¿Qué tipo de ayuda buscas normalmente en Overol?",
                placeholder="Ej: gasfitería, electricidad, reparaciones...",
                key="profile_service_interest",
            )
            bio = ""
        else:
            service_interest = st.text_input(
                "🛠️ ¿Qué servicios realizas?",
                placeholder="Ej: instalaciones, reparaciones, mantención...",
                key="profile_service_interest",
            )
            bio = st.text_area(
                "📝 Cuéntanos brevemente sobre ti y tu experiencia",
                placeholder="Ej: Trabajo hace 5 años realizando reparaciones domiciliarias...",
                key="profile_bio",
            )

        submitted = st.form_submit_button(
            "Guardar mis datos y entrar a Overol",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        errors = []
        if not validate_phone(phone):
            errors.append("Ingresa un teléfono válido (8 a 15 dígitos).")

        if not address.strip():
            errors.append("Ingresa tu dirección.")
        if not service_interest.strip():
            errors.append("Cuéntanos qué necesitas o qué servicios realizas.")

        if errors:
            for error in errors:
                st.error(error)
            return False

        if not _update_profile_api(phone, address, commune):
            return False

        save_user_profile(
            user["id"],
            phone,
            commune,
            contact_preference,
            service_interest,
            bio,
            address,
        )

        audit(
            user["id"],
            "UPDATE_PROFILE",
            "user_profiles",
            user["id"],
            "Datos personales iniciales guardados",
        )

        flash("Datos guardados. Entrando a tu perfil...")
        st.rerun()

    return True


def user_profile_page(user):
    """Historia 006: el usuario modifica sus datos; nombre y RUT quedan bloqueados."""
    section("👤 Mi perfil personal")

    profile = get_user_profile(user["id"])

    if not profile:
        st.warning("Todavía no has completado tus datos personales.")
        return

    profile_user_header(user, profile)

    c1, c2, c3 = st.columns(3)
    c1.text_input("Nombre", value=user["name"], disabled=True, key="ro_name")
    c2.text_input("RUT", value=user["rut"] or "", disabled=True, key="ro_rut")
    c3.text_input("Correo", value=user["email"], disabled=True, key="ro_email")
    st.caption(
        "El nombre y el RUT no se pueden modificar directamente. "
        "Si necesitas corregirlos, solicita una revisión a Overol."
    )

    with st.form("edit_personal_form"):
        phone = st.text_input("📱 Teléfono", value=profile["phone"] or "")
        address = st.text_input("🏠 Dirección", value=profile["address"] or "")

        communes = COMUNAS if profile["commune"] in COMUNAS else [profile["commune"]] + COMUNAS
        commune = st.selectbox(
            "📍 Comuna",
            communes,
            index=communes.index(profile["commune"]) if profile["commune"] in communes else 0,
        )

        preference = st.selectbox(
            "💬 Preferencia de contacto",
            PREFERENCIAS_CONTACTO,
            index=PREFERENCIAS_CONTACTO.index(profile["contact_preference"])
            if profile["contact_preference"] in PREFERENCIAS_CONTACTO
            else 0,
        )

        interest_label = (
            "🏠 Servicios o necesidades habituales"
            if user["role"] == "cliente"
            else "🛠️ Servicios que realizas"
        )
        interest = st.text_input(interest_label, value=profile["service_interest"] or "")

        bio = ""
        if user["role"] == "profesional":
            bio = st.text_area("📝 Sobre mí", value=profile["bio"] or "")

        saved = st.form_submit_button(
            "Guardar cambios", type="primary", use_container_width=True
        )

    if saved:
        errors = []

        if not validate_phone(phone):
            errors.append("Ingresa un teléfono válido (8 a 15 dígitos).")
        if not address.strip():
            errors.append("Ingresa tu dirección.")

        if errors:
            for error in errors:
                st.error(error)
        elif _update_profile_api(phone, address, commune):
            save_user_profile(
                user["id"], phone, commune, preference, interest, bio, address
            )
            audit(user["id"], "UPDATE_PROFILE", "user_profiles", user["id"],
                  "Datos personales modificados")
            flash("Tus datos fueron actualizados.")
            st.rerun()


def open_professional(professional_id):
    """Abre el perfil de un profesional como página propia (queda en la URL: ?profesional=ID)."""
    st.session_state["selected_professional"] = professional_id
    st.query_params["profesional"] = str(professional_id)


def close_professional():
    st.session_state.pop("selected_professional", None)
    try:
        del st.query_params["profesional"]
    except KeyError:
        pass


def apply_deeplink(nav_key, target, prev_key):
    """Si la URL trae ?profesional=ID, abre directamente el perfil de ese profesional.
    Debe llamarse ANTES de crear el menú de navegación."""
    raw = st.query_params.get("profesional")

    if not raw or st.session_state.get("_deeplink_done"):
        return

    st.session_state["_deeplink_done"] = True

    try:
        professional_id = int(raw)
    except ValueError:
        return

    if get_professional_by_id(professional_id):
        st.session_state["selected_professional"] = professional_id
        st.session_state[nav_key] = target
        st.session_state[prev_key] = target


def _go_category(nav_key, target, trade):
    # Se ejecuta como callback: puede modificar el estado de widgets antes del rerun.
    st.session_state[nav_key] = target
    st.session_state["search_trade"] = trade
    close_professional()


def go_to(nav_key, target):
    """Callback para botones que cambian de sección."""
    st.session_state[nav_key] = target
    close_professional()


def category_buttons(nav_key, target):
    """Categorías de oficios como botones que llevan a la lista de profesionales."""
    cols = st.columns(len(OFICIOS_INFO))

    for col, (icon, trade, description) in zip(cols, OFICIOS_INFO):
        with col:
            st.markdown(
                "".join(
                    line.strip()
                    for line in f"""
                    <div class="card category-card">
                        <div class="icon">{icon}</div>
                        <h3>{escape(trade)}</h3>
                        <div class="muted">{escape(description)}</div>
                    </div>
                    """.splitlines()
                ),
                unsafe_allow_html=True,
            )
            st.button(
                "Ver profesionales",
                key=f"cat_{nav_key}_{trade}",
                on_click=_go_category,
                args=(nav_key, target, trade),
                use_container_width=True,
            )


def go_login_button(key, label="🔑 Iniciar sesión o registrarme"):
    """Lleva al visitante a la pantalla de acceso."""
    if st.button(label, key=key, type="primary", use_container_width=True):
        st.session_state["show_login"] = True
        st.rerun()


def render_profile_card(professional, anonymous, owner=False):
    """Perfil completo tipo LinkedIn: cabecera con portada y secciones."""
    profile_header(professional, anonymous)
    profile_sections(professional, owner=owner)


def render_reviews(professional_id):
    """Opiniones de clientes (sin nombres)."""
    profile_reviews(professional_id)


def professional_profile_public(professional_id):
    """Historia 003: perfil público para visitantes (sin datos personales)."""
    professional = get_professional_by_id(professional_id)

    if not professional:
        st.error("Profesional no encontrado.")
        return

    profile_header(professional, anonymous=True)

    left, right = st.columns([1.7, 1])

    with left:
        profile_sections(professional)
        profile_reviews(professional_id)

    with right:
        st.markdown(
            """<div class="psection"><h3><span class="psection-icon">📅</span>¿Quieres solicitar una visita?</h3><p class="muted">Para solicitar una visita necesitas una cuenta. Registrarte es gratis y toma un minuto.</p></div>""",
            unsafe_allow_html=True,
        )
        go_login_button(f"go_login_profile_{professional_id}")

        security_note(
            "Por privacidad, el nombre, teléfono, correo, RUT y dirección "
            "del profesional no se muestran públicamente."
        )


def professional_profile_client(user_id, professional_id):
    # Solo los clientes pueden ver perfiles individuales y agendar visitas
    viewer = get_user(user_id)

    if not viewer or viewer["role"] != "cliente":
        st.error("Solo los clientes pueden ver perfiles de profesionales y agendar visitas.")
        return

    professional = get_professional_by_id(professional_id)

    if not professional:
        st.error("Profesional no encontrado.")
        return

    profile_header(professional, anonymous=False)

    left, right = st.columns([1.7, 1])

    with left:
        profile_sections(professional)
        profile_reviews(professional_id)

    with right:
        st.markdown("### 📅 Solicitar visita")

        work_days = [d for d in (professional["work_days"] or "").split(",") if d]

        if work_days:
            st.caption(
                f"📅 Trabaja: {', '.join(work_days)}"
                + (
                    f" · 🕘 {professional['work_start']}–{professional['work_end']}"
                    if professional["work_start"]
                    else ""
                )
            )

        trade_names = [t["trade"] for t in get_trades(professional_id)]

        trade = st.selectbox(
            "Oficio requerido",
            trade_names,
            key=f"request_trade_{professional_id}",
        )

        coverage = [x for x in COMUNAS if x in professional["coverage"].split(",")]
        commune = st.selectbox(
            "Comuna del servicio",
            coverage or COMUNAS,
            key=f"request_commune_{professional_id}",
        )

        home_zone = st.selectbox(
            "Zona del hogar",
            ZONAS_HOGAR,
            key=f"request_zone_{professional_id}",
        )

        # La fecha propuesta por defecto es el próximo día en que el profesional trabaja
        date = st.date_input(
            "Fecha tentativa",
            value=next_work_date(professional["work_days"]),
            min_value=datetime.today().date(),
            key=f"request_date_{professional_id}",
        )

        slots = [
            s for s in FRANJAS_HORARIAS
            if not professional["work_start"]
            or (
                professional["work_start"] <= s.split(" - ")[0]
                and s.split(" - ")[1] <= professional["work_end"]
            )
        ]

        if not slots:
            st.warning("Ninguna franja horaria disponible coincide con el horario del profesional.")

        time = st.selectbox(
            "Horario tentativo",
            slots or FRANJAS_HORARIAS,
            key=f"request_time_{professional_id}",
        )

        description = st.text_area(
            "Descripción del trabajo",
            placeholder="Describe el problema o trabajo que necesitas realizar.",
            key=f"request_description_{professional_id}",
        )

        if st.button(
            "Solicitar visita",
            type="primary",
            use_container_width=True,
            key=f"send_request_{professional_id}",
        ):
            ok, result = create_request(
                user_id, professional_id, trade, home_zone, commune, date, time, description
            )

            if not ok:
                st.warning(result)
            else:
                audit(
                    user_id,
                    "CREATE",
                    "requests",
                    result,
                    f"Solicitud para profesional {professional_id} ({trade})",
                )

                flash("Solicitud enviada. Puedes revisarla en «Mis solicitudes».")
                close_professional()
                st.rerun()

        security_note(
            "Los datos de contacto del profesional se habilitan cuando "
            "acepta tu solicitud. El RUT, el domicilio y los documentos de "
            "verificación nunca se muestran."
        )


def sidebar(user):
    with st.sidebar:
        st.markdown("## 🦺 Overol")

        st.write(
            f"Hola, **{user['name']}**"
        )

        st.caption(
            f"Rol: {ROLES.get(user['role'], user['role'])}"
        )

        st.divider()

        if st.button(
            "Cerrar sesión",
            use_container_width=True,
            key="logout_button",
        ):
            audit(
                user["id"],
                "LOGOUT",
                "users",
                user["id"],
                "Cierre de sesión",
            )

            # Se elimina la sesión persistente (base de datos + cookie del navegador)
            delete_session(st.session_state.get("session_token"))

            st.session_state.clear()
            st.session_state["_clear_cookie"] = True
            flash("Sesión cerrada correctamente.", "info")

            st.rerun()

        st.divider()

        st.markdown("### 📌 Requisitos contemplados")

        st.caption("RF/Epic 001 · Registro y verificación")
        st.caption("RF/Epic 002 · Búsqueda")
        st.caption("RF/Epic 003 · Chatbot")
        st.caption("RF/Epic 004 · Solicitud de visita")
        st.caption("RF/Epic 005 · Cobertura")
        st.caption("RF/Epic 006 · Reputación")
        st.caption("RF/Epic 007 · Capacitación")
        st.caption("RF/Epic 008 · Administración")
        st.caption("RF/Epic 009 · Posventa")

        st.divider()

        st.markdown("### 🔐 RNF contemplados")

        st.caption("Autenticación")
        st.caption("Roles")
        st.caption("Protección de credenciales")
        st.caption("Separación público/privado")
        st.caption("Integridad")
        st.caption("Persistencia")
        st.caption("Trazabilidad")
        st.caption("Modularidad")
