"""Pantallas compartidas entre roles: perfil personal, perfil público del profesional y barra lateral."""

import streamlit as st

from core import api_client, catalog_api
from core.constants import (
    COMUNAS,
    OFICIOS_INFO,
    PREFERENCIAS_CONTACTO,
    ROLES,
)
from core.security import validate_password_strength, validate_phone
from core.session import end_session, load_user
from ui.components import flash, section, security_note
from ui.profile import (
    profile_header,
    profile_reviews,
    profile_sections,
    profile_user_header,
)


def _save_me(**fields):
    """PATCH /auth/me/ y recarga el usuario de la sesión. Devuelve False si falló."""
    try:
        api_client.update_me(**fields)
        load_user()
    except api_client.ApiError as error:
        st.error(f"No se pudieron guardar tus datos en el servidor. {error}")
        return False
    return True


def _professional_fields(user, prefix):
    """Preferencia de contacto, titular y presentación (solo profesionales: el backend
    guarda estos datos en el perfil profesional e ignora los de un cliente)."""
    preference = st.selectbox(
        "💬 ¿Cómo prefieres que te contacten?",
        PREFERENCIAS_CONTACTO,
        index=PREFERENCIAS_CONTACTO.index(user["contact_preference"])
        if user["contact_preference"] in PREFERENCIAS_CONTACTO
        else 0,
        key=f"{prefix}_contact_preference",
    )
    headline = st.text_input(
        "🛠️ Titular",
        value=user["headline"],
        max_chars=160,
        placeholder="Ej: Gasfiter certificado · Fugas y calefont",
        key=f"{prefix}_headline",
    )
    bio = st.text_area(
        "📝 Cuéntanos brevemente sobre ti y tu experiencia",
        value=user["bio"],
        max_chars=500,
        placeholder="Ej: Trabajo hace 5 años realizando reparaciones domiciliarias...",
        key=f"{prefix}_bio",
    )
    return {"contact_preference": preference, "headline": headline, "bio": bio}


def _commune_options(current):
    return COMUNAS if not current or current in COMUNAS else [current] + COMUNAS


def personal_questions_screen(user):
    """Formulario obligatorio inicial: teléfono, dirección y comuna (y, para el profesional,
    su presentación). Se guarda en el backend con PATCH /auth/me/."""
    section("👤 Completa tu perfil")

    role_label = ROLES.get(user["role"], user["role"])
    st.info(
        f"Estás ingresando como **{role_label}**. "
        "Antes de entrar a la plataforma necesitamos algunos datos para tu perfil."
    )

    with st.form("personal_profile_form", clear_on_submit=False):
        phone = st.text_input(
            "📱 Número de teléfono",
            value=user["phone"],
            placeholder="Ej: +56 9 1234 5678",
            key="profile_phone",
        )

        address = st.text_input(
            "🏠 Dirección",
            value=user["address"],
            placeholder="Ej: Av. Principal 1234",
            key="profile_address",
        )

        communes = _commune_options(user["commune"])
        commune = st.selectbox(
            "📍 Comuna",
            communes,
            index=communes.index(user["commune"]) if user["commune"] in communes else 0,
            key="profile_commune",
        )

        extra = _professional_fields(user, "profile") if user["role"] == "profesional" else {}

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

        if errors:
            for error in errors:
                st.error(error)
            return False

        if not _save_me(phone=phone, address=address, commune=commune, **extra):
            return False

        flash("Datos guardados. Entrando a tu perfil...")
        st.rerun()

    return True


def _change_password_form():
    """Cambio de contraseña (POST /auth/password/change/)."""
    with st.expander("🔑 Cambiar contraseña"):
        with st.form("change_password_form", clear_on_submit=True):
            current = st.text_input("Contraseña actual", type="password", key="pwd_current")
            new = st.text_input(
                "Nueva contraseña",
                type="password",
                help="Mínimo 8 caracteres, con al menos una letra y un número.",
                key="pwd_new",
            )
            confirm = st.text_input("Confirmar nueva contraseña", type="password", key="pwd_confirm")
            submitted = st.form_submit_button("Cambiar contraseña", use_container_width=True)

        if not submitted:
            return

        problems = validate_password_strength(new)
        if not current:
            st.error("Ingresa tu contraseña actual.")
        elif problems:
            st.error("La nueva contraseña necesita " + ", ".join(problems) + ".")
        elif new != confirm:
            st.error("Las contraseñas no coinciden.")
        else:
            try:
                api_client.change_password(current, new)
            except api_client.ApiError as error:
                messages = (
                    api_client.field_messages(error.data, "current_password")
                    + api_client.field_messages(error.data, "new_password")
                )
                st.error(
                    "No se pudo cambiar la contraseña:\n\n" + "\n".join(f"- {m}" for m in messages)
                    if messages else f"No se pudo cambiar la contraseña. {error}"
                )
                return
            st.success("Contraseña actualizada. Úsala la próxima vez que ingreses.")


def user_profile_page(user):
    """Historia 006: el usuario modifica sus datos; nombre, RUT y correo quedan bloqueados."""
    section("👤 Mi perfil personal")

    profile_user_header(user)

    c1, c2, c3 = st.columns(3)
    c1.text_input("Nombre", value=user["name"], disabled=True, key="ro_name")
    c2.text_input("RUT", value=user["rut"], disabled=True, key="ro_rut")
    c3.text_input("Correo", value=user["email"], disabled=True, key="ro_email")
    st.caption(
        "El nombre, el RUT y el correo no se pueden modificar directamente. "
        "Si necesitas corregirlos, solicita una revisión a Overol."
    )

    with st.form("edit_personal_form"):
        phone = st.text_input("📱 Teléfono", value=user["phone"], key="edit_phone")
        address = st.text_input("🏠 Dirección", value=user["address"], key="edit_address")

        communes = _commune_options(user["commune"])
        commune = st.selectbox(
            "📍 Comuna",
            communes,
            index=communes.index(user["commune"]) if user["commune"] in communes else 0,
            key="edit_commune",
        )

        extra = _professional_fields(user, "edit") if user["role"] == "profesional" else {}

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
        elif _save_me(phone=phone, address=address, commune=commune, **extra):
            flash("Tus datos fueron actualizados.")
            st.rerun()

    _change_password_form()


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

    try:
        exists = catalog_api.get_professional(professional_id) is not None
    except api_client.ApiError:
        exists = False

    if exists:
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
    """Categorías de oficios: cada tarjeta (ícono, oficio y descripción) es un botón que
    lleva a la lista de profesionales. Estilo en style.css («st-key-cat_grid_»)."""
    with st.container(key=f"cat_grid_{nav_key}"):
        cols = st.columns(len(OFICIOS_INFO))

        for col, (icon, trade, description) in zip(cols, OFICIOS_INFO):
            with col:
                # Los saltos de línea se muestran gracias a «white-space: pre-line» en el CSS
                st.button(
                    f"{icon}\n**{trade}**\n{description}",
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


def _load_professional(professional_id, anonymous=False):
    """Profesional del catálogo (base local o backend). Muestra el error y devuelve None."""
    try:
        professional = catalog_api.get_professional(professional_id, anonymous=anonymous)
    except api_client.ApiError as error:
        st.error(f"No se pudo cargar el perfil del profesional. {error}")
        return None

    if not professional:
        st.error("Profesional no encontrado.")
    return professional


def professional_profile_public(professional_id):
    """Historia 003: perfil público para visitantes (sin datos personales)."""
    professional = _load_professional(professional_id, anonymous=True)

    if not professional:
        return

    profile_header(professional, anonymous=True)

    left, right = st.columns([1.7, 1])

    with left:
        profile_sections(professional)
        profile_reviews(professional)

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


def professional_profile_client(viewer, professional_id):
    # Solo los clientes pueden ver perfiles individuales y agendar visitas
    if not viewer or viewer["role"] != "cliente":
        st.error("Solo los clientes pueden ver perfiles de profesionales y agendar visitas.")
        return

    professional = _load_professional(professional_id)

    if not professional:
        return

    profile_header(professional, anonymous=False)

    left, right = st.columns([1.7, 1])

    with left:
        profile_sections(professional)
        profile_reviews(professional)

    with right:
        st.markdown("### 📅 Solicitar visita")

        # Etapa C: aquí vuelve el formulario, enviando la solicitud a POST /api/requests/
        st.info(
            "**Disponible pronto.** Muy luego podrás solicitar una visita a este "
            "profesional directamente desde su perfil."
        )

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
            # Anula el token en el backend y borra la sesión del servidor y la cookie
            end_session()
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
