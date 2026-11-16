"""Pantallas compartidas entre roles: perfil personal, perfil público del profesional y barra lateral."""

from datetime import date
from html import escape

import streamlit as st

from core import api_client, catalog_api, requests_api
from core.constants import (
    COMUNAS,
    FRANJAS_HORARIAS,
    MAX_TEXTO,
    PREFERENCIAS_CONTACTO,
    ROLES,
)
from core.oficios import GRUPOS_OFICIOS
from core.security import validate_password_strength, validate_phone
from core.session import end_session, load_user
from ui.components import SIDE_SECTIONS_SLOT, flash, section, security_note
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


def _change_password_form(expanded=False):
    """Cambio de contraseña (POST /auth/password/change/)."""
    with st.expander("🔑 Cambiar contraseña", expanded=expanded):
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
    """Historia 006: el usuario modifica sus datos; nombre, RUT y correo quedan bloqueados.
    Desde el menú lateral se puede abrir solo «Editar datos» o solo «Cambiar contraseña»."""
    focus = st.session_state.get(PROFILE_FOCUS_KEY, "perfil")

    if focus == "contrasena":
        section("🔑 Cambiar contraseña")
        _change_password_form(expanded=True)
        return

    section("✏️ Editar mis datos" if focus == "editar" else "👤 Mi perfil personal")

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

    if focus != "editar":
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
    """Oficios de la portada (lista oficial del equipo, por categorías): cada uno es un botón que
    lleva al catálogo filtrado por ese oficio (nombre del backend). Estilo en style.css
    («st-key-cat_grid_»): una grilla que se acomoda sola al ancho de la pantalla."""
    for g, (icon, title, oficios) in enumerate(GRUPOS_OFICIOS):
        st.markdown(
            f'<div class="cat-group-title">{icon} {escape(title)} <span>({len(oficios)})</span></div>',
            unsafe_allow_html=True,
        )
        with st.container(key=f"cat_grid_{nav_key}_{g}"):
            cols = st.columns(len(oficios))

            for col, (label, trade, emoji) in zip(cols, oficios):
                with col:
                    st.button(
                        f"{emoji} {label}",
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

        _request_form(viewer, professional)

        security_note(
            "Los datos de contacto del profesional se habilitan cuando "
            "acepta tu solicitud. El RUT, el domicilio y los documentos de "
            "verificación nunca se muestran."
        )


def _request_form(viewer, professional):
    """Historia 010: solicitud de visita (POST /api/requests/). El backend valida días,
    horario, cobertura y duplicados; aquí se ofrecen solo opciones válidas."""
    pid = professional["id"]

    if professional["work_days"]:
        st.caption(
            f"📅 Trabaja: {professional['work_days'].replace(',', ', ')}"
            + (f" · 🕘 {professional['work_start']}–{professional['work_end']}" if professional["work_start"] else "")
        )

    if not professional["work_start"] or not professional["work_end"]:
        st.warning("Este profesional todavía no configuró su horario de atención, así que aún no recibe solicitudes.")
        return

    trades = catalog_api.trades(professional)
    trade = st.selectbox("Oficio requerido", [t["trade"] for t in trades], key=f"request_trade_{pid}")
    specialties = next((t["specialty_list"] for t in trades if t["trade"] == trade), [])

    if not specialties:
        st.warning(f"Este profesional aún no registra especialidades de {trade}, así que no se puede solicitar ese oficio.")
        return

    names = [s["name"] for s in specialties]
    specialty = st.selectbox("Especialidad", names, key=f"request_specialty_{trade}_{pid}")

    coverage = [c for c in professional["coverage"].split(",") if c]
    commune = st.selectbox("Comuna del servicio", coverage or COMUNAS, key=f"request_commune_{pid}")

    work_days = [d for d in professional["work_days"].split(",") if d]
    visit_date = st.date_input(
        "Fecha tentativa",
        value=requests_api.next_work_date(work_days),
        min_value=date.today(),
        format="DD-MM-YYYY",
        key=f"request_date_{pid}",
    )

    slots = [
        s for s in FRANJAS_HORARIAS
        if professional["work_start"] <= s.split(" - ")[0] and s.split(" - ")[1] <= professional["work_end"]
    ]
    if not slots:
        st.warning("Ninguna franja horaria coincide con el horario de este profesional.")
        return
    visit_time = st.selectbox("Horario tentativo", slots, key=f"request_time_{pid}")

    st.text_input(
        "Dirección de la visita",
        value=viewer["address"],
        disabled=True,
        key=f"request_address_{pid}",
        help="Se usa la dirección de tu cuenta. Puedes cambiarla en «Mi perfil».",
    )

    description = st.text_area(
        "Descripción del trabajo",
        max_chars=MAX_TEXTO,
        placeholder="Describe el problema o trabajo que necesitas realizar.",
        key=f"request_description_{pid}",
    )

    if not st.button("Solicitar visita", type="primary", use_container_width=True, key=f"send_request_{pid}"):
        return

    if not description.strip():
        st.warning("Describe el trabajo que necesitas.")
        return
    if not viewer["address"]:
        st.warning("Agrega tu dirección en «Mi perfil» para solicitar una visita.")
        return

    try:
        requests_api.create_request(
            pid,
            specialties[names.index(specialty)]["id"],
            description,
            visit_date,
            visit_time,
            commune,
            viewer["address"],
        )
    except api_client.ApiError as error:
        st.error(f"No se pudo enviar la solicitud. {error}")
        return

    flash("Solicitud enviada. Puedes revisarla en «Mis solicitudes».")
    close_professional()
    st.rerun()


PROFILE_FOCUS_KEY = "_profile_focus"

# Opciones de «Mi cuenta» en el menú lateral: (etiqueta, destino). «Mi perfil» ya está en
# los botones de sección; solo el admin, que no lo tiene en su barra, lo ve aquí.
ADMIN_ACCOUNT_OPTIONS = [
    ("👤 Mi perfil", "perfil"),
]
ACCOUNT_OPTIONS = [
    ("🔑 Cambiar contraseña", "contrasena"),
]
PROFESSIONAL_OPTIONS = [
    ("💳 Suscripción", "💳 Suscripción"),
    ("🪪 Verificación", "🪪 Verificación"),
]
NAV_KEYS = {"cliente": "client_navigation", "profesional": "professional_navigation", "admin": "admin_navigation"}
PREV_KEYS = {"cliente": "_client_prev_menu", "profesional": "_pro_prev_menu", "admin": "_admin_prev_menu"}


def _go_account(role, target):
    """Callback del menú lateral: abre la pantalla elegida (antes de redibujar la barra)."""
    nav, prev = NAV_KEYS[role], PREV_KEYS[role]
    if target in ("perfil", "editar", "contrasena"):
        st.session_state[PROFILE_FOCUS_KEY] = target
        if role != "admin":  # el admin ve su perfil dentro de la sección en que está
            st.session_state[nav] = "👤 Mi perfil"
    else:
        st.session_state.pop(PROFILE_FOCUS_KEY, None)
        st.session_state[nav] = target
    # Se marca como sección vigente para que el cambio de sección no descarte la elección
    st.session_state[prev] = st.session_state.get(nav)
    close_professional()


def sidebar(user):
    with st.sidebar:
        st.markdown("## 🦺 Overol")
        st.write(f"Hola, **{user['name']}**")

        # Botones de sección: los dibuja nav_bar aquí (la navegación está solo en este menú)
        st.session_state[SIDE_SECTIONS_SLOT] = st.container(key="side_sections")

        st.divider()
        st.markdown("##### Mi cuenta")

        options = (
            (ADMIN_ACCOUNT_OPTIONS if user["role"] == "admin" else [])
            + ACCOUNT_OPTIONS
            + (PROFESSIONAL_OPTIONS if user["role"] == "profesional" else [])
        )
        with st.container(key="side_menu"):
            for label, target in options:
                st.button(
                    label,
                    key=f"side_{target.split(' ')[-1].lower()}",
                    use_container_width=True,
                    on_click=_go_account,
                    args=(user["role"], target),
                )

        st.divider()
        _logout_button()


def _logout_button():
    if st.button(
        "Cerrar sesión",
        use_container_width=True,
        key="logout_button",
    ):
        # Anula el token en el backend y borra la sesión del servidor y la cookie
        end_session()
        flash("Sesión cerrada correctamente.", "info")

        st.rerun()


def pending_profile_sidebar(user):
    """Menú lateral mínimo mientras faltan los datos personales: el usuario puede salir."""
    with st.sidebar:
        st.markdown("## 🦺 Overol")
        st.write(f"Hola, **{user['name']}**")
        st.caption("Completa tus datos para usar Overol.")
        st.divider()
        _logout_button()
