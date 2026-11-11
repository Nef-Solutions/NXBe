"""Pantalla de inicio de sesión, registro y recuperación de contraseña (todo contra el backend)."""

import re
import unicodedata

import streamlit as st

from core import api_client
from core.constants import COMUNAS, OFICIOS, PRIVACY_POLICY_VERSION
from core.security import (
    normalize_rut,
    validate_email,
    validate_password_strength,
    validate_phone,
    validate_rut_dv,
    validate_rut_format,
)
from core.session import start_session
from ui.components import flash


# Mismos caracteres que acepta el backend en nombres y apellidos (sanitize_person_name)
NOMBRE_VALIDO = re.compile(r"[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s']+")

# El backend bloquea la cuenta 5 minutos tras 3 fallos y, mientras dure, responde 429
# con retry_after (segundos). El front ya no cuenta intentos por su cuenta.
BLOQUEO_AVISO = "Tras 3 intentos fallidos, la cuenta se bloquea por seguridad durante 5 minutos."
MINUTOS_BLOQUEO = 5

# Usuarios que crea `python manage.py seed_demo` en el backend
DEMO_PASSWORD = "OverolDemo123!"
DEMO_USERS = [
    ("🏠 Cliente", "cliente1@demo.overol.cl", "demo_cliente"),
    ("🛠️ Profesional", "profesional1@demo.overol.cl", "demo_profesional"),
    ("🛡️ Administrador", "admin@demo.overol.cl", "demo_admin"),
]


def api_lock_message(retry_after):
    """Mensaje del 429 del backend, con los minutos que faltan (redondeados hacia arriba)."""
    try:
        minutes = max(1, -(-int(retry_after) // 60))
    except (TypeError, ValueError):
        minutes = MINUTOS_BLOQUEO
    unit = "minuto" if minutes == 1 else "minutos"
    return f"Cuenta bloqueada por intentos fallidos. Intenta de nuevo en {minutes} {unit}."


REGISTER_KEYS = [
    "register_name",
    "register_lastname",
    "register_rut",
    "register_email",
    "register_phone",
    "register_commune",
    "register_address",
    "register_password",
    "register_confirm",
    "register_role",
    "register_trade",
    "register_years",
    "register_coverage",
    "register_privacy",
]


def _fill_demo(email, password):
    # Callback: completa el formulario de ingreso con un usuario de demostración.
    st.session_state["login_email"] = email
    st.session_state["login_password"] = password


def login_screen():
    st.markdown(
        """
        <div class="login-head">
            <div class="logo">🦺 OVEROL</div>
            <h1>Conecta con profesionales</h1>
            <p>Plataforma de servicios para el hogar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Limpia el formulario después de un registro exitoso.
    # Debe hacerse ANTES de crear los widgets.
    if st.session_state.pop("_clear_register", False):
        for key in REGISTER_KEYS:
            st.session_state.pop(key, None)

    login_tab, register_tab = st.tabs(
        ["🔑 Iniciar sesión", "📝 Crear cuenta"]
    )

    with login_tab:
        st.markdown("### Iniciar sesión")

        # Se usa un formulario para que escribir en los campos no provoque reruns.
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "Correo electrónico",
                placeholder="correo@ejemplo.cl",
                key="login_email",
            )

            password = st.text_input(
                "Contraseña",
                type="password",
                key="login_password",
            )

            remember = st.checkbox(
                "Mantener mi sesión iniciada por 7 días en este dispositivo",
                value=True,
                key="login_remember",
            )

            login_submitted = st.form_submit_button(
                "Ingresar",
                use_container_width=True,
                type="primary",
            )

        if login_submitted:
            email_clean = email.strip().lower()

            if not email_clean or not password:
                st.error("Ingresa tu correo y tu contraseña.")
            else:
                _login(email_clean, password, remember)

        _password_recovery()

        st.markdown("---")
        st.caption(
            "Usuarios de demostración del backend (`python manage.py seed_demo`): "
            "elige uno y pulsa «Ingresar»."
        )

        cols = st.columns(len(DEMO_USERS))
        for col, (label, demo_email, key) in zip(cols, DEMO_USERS):
            with col:
                st.button(
                    label,
                    key=key,
                    use_container_width=True,
                    on_click=_fill_demo,
                    args=(demo_email, DEMO_PASSWORD),
                )

        st.code(
            "\n".join(f"{label.split(' ', 1)[1]:<15}{demo_email}" for label, demo_email, _ in DEMO_USERS)
            + f"\nContraseña     {DEMO_PASSWORD}"
        )

    with register_tab:
        _register_form()


def _login(email_clean, password, remember):
    """Valida las credenciales en el backend (POST /auth/token/) y abre la sesión."""
    try:
        api_client.login(email_clean, password)
        start_session(remember)
    except api_client.ApiError as error:
        api_client.clear_tokens()
        if error.status in (400, 401):
            st.error("Correo o contraseña incorrectos. " + BLOQUEO_AVISO)
        elif error.status == 429:
            data = error.data if isinstance(error.data, dict) else {}
            st.error(api_lock_message(data.get("retry_after")))
        else:
            st.error(str(error))
        return
    except ValueError as error:
        api_client.clear_tokens()
        st.error(f"No se pudo iniciar sesión: {error}")
        return

    st.rerun()


def _password_recovery():
    """Historia 007: el backend envía un enlace para restablecer la contraseña.
    Por ahora el correo se imprime en la consola del backend (sin servidor de correo)."""
    with st.expander("¿Olvidaste tu contraseña?"):
        with st.form("recovery_form", clear_on_submit=True):
            r_email = st.text_input("Correo electrónico de tu cuenta", key="recovery_email")
            submitted = st.form_submit_button("Enviar instrucciones", use_container_width=True)

        if not submitted:
            return

        if not validate_email(r_email):
            st.error("Ingresa un correo válido.")
            return

        try:
            detail = api_client.reset_password(r_email)
        except api_client.ApiError as error:
            st.error(f"No se pudo enviar la solicitud. {error}")
            return

        st.success(
            detail or "Si el correo está registrado, recibirás instrucciones para recuperar tu contraseña."
        )


def _register_form():
    """Historias 005 y 014: registro de cliente y de profesional."""
    st.markdown("### Crear cuenta")

    tipo = st.radio(
        "Tipo de cuenta",
        ["Cliente", "Profesional"],
        horizontal=True,
        key="register_role",
    )

    n1, n2 = st.columns(2)
    nombre = n1.text_input("Nombre", key="register_name")
    apellido = n2.text_input("Apellido", key="register_lastname")

    r1, r2 = st.columns(2)
    rut = r1.text_input("RUT", placeholder="12345678-5", key="register_rut")
    email = r2.text_input("Correo electrónico", key="register_email")

    t1, t2 = st.columns(2)
    telefono = t1.text_input(
        "Teléfono", placeholder="+56 9 1234 5678", key="register_phone"
    )
    comuna = t2.selectbox("Comuna", COMUNAS, key="register_commune")

    direccion = st.text_input(
        "Dirección de domicilio" if tipo == "Profesional" else "Dirección",
        placeholder="Ej: Av. Principal 1234",
        key="register_address",
        help="Es un dato privado: no se muestra a otros usuarios."
        if tipo == "Profesional"
        else None,
    )

    oficio = ""
    anios = None
    comunas_trabajo = []

    if tipo == "Profesional":
        st.info(
            "Tu cuenta quedará con estado «Pendiente de verificación». "
            "Podrás completar tu perfil profesional una vez que ingreses."
        )

        o1, o2 = st.columns(2)
        oficio = o1.selectbox("Oficio principal", OFICIOS, key="register_trade")
        anios = o2.number_input(
            "Años de experiencia (opcional)",
            min_value=0,
            max_value=60,
            step=1,
            key="register_years",
        )
        comunas_trabajo = st.multiselect(
            "Comunas donde trabajas",
            COMUNAS,
            key="register_coverage",
            help="Los clientes te encontrarán en estas comunas.",
        )

    p1, p2 = st.columns(2)
    password = p1.text_input(
        "Contraseña",
        type="password",
        help="Mínimo 8 caracteres, con al menos una letra y un número.",
        key="register_password",
    )
    confirm = p2.text_input(
        "Confirmar contraseña", type="password", key="register_confirm"
    )

    acepta_privacidad = st.checkbox(
        "Acepto la política de privacidad y los términos de uso de Overol "
        f"(versión {PRIVACY_POLICY_VERSION}).",
        key="register_privacy",
    )

    if not st.button(
        "Crear cuenta",
        use_container_width=True,
        type="primary",
        key="register_button",
    ):
        return

    errores = []

    if not nombre.strip() or not apellido.strip():
        errores.append("Ingresa tu nombre y tu apellido.")

    # Misma regla del backend (sanitize_person_name), para avisar antes de enviar
    else:
        for etiqueta, valor in (("nombre", nombre), ("apellido", apellido)):
            if not NOMBRE_VALIDO.fullmatch(valor.strip()):
                errores.append(
                    f"El {etiqueta} solo puede tener letras, espacios y apóstrofes "
                    "(sin guiones, números ni otros signos). "
                    "Por ahora, escribe «Ana María» en vez de «Ana-María»."
                )

    if not validate_rut_format(rut):
        errores.append("El RUT debe tener formato válido, por ejemplo 12345678-5.")
    elif not validate_rut_dv(rut):
        errores.append("El RUT no es válido: revisa el dígito verificador.")

    if not validate_email(email):
        errores.append("Ingresa un correo válido.")

    if tipo == "Profesional" and not comunas_trabajo:
        errores.append("Selecciona al menos una comuna donde trabajas.")

    if not validate_phone(telefono):
        errores.append("Ingresa un teléfono válido (8 a 15 dígitos).")

    if not direccion.strip():
        errores.append("Ingresa tu dirección.")

    faltantes = validate_password_strength(password)
    if faltantes:
        errores.append("La contraseña necesita " + ", ".join(faltantes) + ".")

    if password != confirm:
        errores.append("Las contraseñas no coinciden.")

    if not acepta_privacidad:
        errores.append("Debes aceptar la política de privacidad y los términos de uso.")

    # Correo o RUT repetidos los informa el backend (400 con el campo)
    if errores:
        for error in errores:
            st.error(error)
        return

    role = "cliente" if tipo == "Cliente" else "profesional"

    if not _register_api(
        nombre, apellido, rut, email, telefono, direccion, comuna, role, password,
        oficio, anios, comunas_trabajo,
    ):
        return

    flash("Cuenta creada correctamente. Ya puedes iniciar sesión.")
    st.session_state["_clear_register"] = True
    st.rerun()


def _plain(text):
    """Minúsculas y sin tildes, para comparar nombres de oficios."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text.strip().lower())
        if unicodedata.category(c) != "Mn"
    )


def _backend_category_id(oficio):
    """Id del oficio en el catálogo del backend. Muestra el error y devuelve None si no existe."""
    try:
        categories = api_client.get_categories()
    except api_client.ApiError as error:
        st.error(f"No se pudo consultar la lista de oficios del servidor. {error}")
        return None

    for category in categories:
        if _plain(category.get("name", "")) == _plain(oficio):
            return category["id"]

    available = ", ".join(sorted(c.get("name", "") for c in categories)) or "ninguno todavía"
    st.error(
        f"El oficio «{oficio}» todavía no está disponible en el servidor de Overol, "
        "así que no se pudo crear la cuenta. "
        f"Por ahora puedes registrarte con uno de estos oficios: {available}."
    )
    return None


def _show_register_error(error):
    """Errores del registro; las reglas de contraseña del backend se muestran como lista."""
    password_messages = api_client.field_messages(error.data, "password")
    if not password_messages:
        st.error(str(error))
        return

    st.error(
        "La contraseña no cumple las reglas de seguridad del servidor:\n\n"
        + "\n".join(f"- {message}" for message in password_messages)
    )
    others = {k: v for k, v in error.data.items() if k != "password"}
    if others:
        st.error(api_client.error_text(error.status, others))


def _register_api(nombre, apellido, rut, email, telefono, direccion, comuna, role, password,
                  oficio="", anios=None, comunas_trabajo=()):
    """Crea la cuenta en el backend (POST /auth/register/). Devuelve True si se creó."""
    payload = {
        "email": email.strip().lower(),
        "first_name": nombre.strip(),
        "last_name": apellido.strip(),
        "phone": telefono.strip(),
        "rut": normalize_rut(rut),
        "address": direccion.strip(),
        "commune": comuna,
        "role": "CLIENT" if role == "cliente" else "PROFESSIONAL",
        "password": password,
        "privacy_policy_accepted": True,
        "privacy_policy_version": PRIVACY_POLICY_VERSION,
    }
    if role == "profesional":
        # El backend ignora sin avisar un oficio que no conoce: se valida antes de enviarlo
        category_id = _backend_category_id(oficio)
        if category_id is None:
            return False
        # La tarifa se completa después en el perfil
        payload["professional_profile"] = {
            "visit_fee": 0,
            "coverage_communes": list(comunas_trabajo),
            "categories": [{"category": category_id, "years_experience": int(anios or 0)}],
        }

    try:
        api_client.register(payload)
    except api_client.ApiError as error:
        _show_register_error(error)
        return False

    return True
