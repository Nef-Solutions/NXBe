"""Pantalla de inicio de sesión, registro y recuperación de contraseña."""

import re
import sqlite3

import streamlit as st

from core import api_client
from core.constants import (
    COMUNAS,
    MAX_INTENTOS_LOGIN,
    MINUTOS_BLOQUEO,
    OFICIOS,
    PRIVACY_POLICY_VERSION,
    use_api,
)
from core.database import (
    insert_trade,
    audit,
    count_login_failures,
    get_lock_remaining,
    get_connection,
    get_professional_by_user,
    get_user_by_email,
    get_user_profile,
    now_str,
    save_user_profile,
    sync_professional_summary,
    upsert_api_user,
)
from core.security import (
    hash_password,
    normalize_rut,
    validate_email,
    validate_password_strength,
    validate_phone,
    validate_rut_dv,
    validate_rut_format,
    verify_password,
)
from core.session import create_session
from ui.components import flash



# Mismos caracteres que acepta el backend en nombres y apellidos (sanitize_person_name)
NOMBRE_VALIDO = re.compile(r"[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s']+")


# Modo api: el backend bloquea la cuenta tras 3 fallos (hasta 6 horas) y responde 401
# igual que ante una clave incorrecta, así que el front no puede saber si está bloqueada.
API_BLOQUEO_AVISO = (
    "Si ya te equivocaste 3 veces, tu cuenta puede estar bloqueada por seguridad hasta 6 horas."
)


def lock_message(seconds):
    minutes, secs = divmod(int(seconds), 60)
    if use_api():
        return (
            f"Demasiados intentos fallidos: el ingreso desde este equipo está pausado por "
            f"{MINUTOS_BLOQUEO} minutos ({minutes} min {secs:02d} s restantes). "
            "Además, por seguridad tu cuenta puede estar bloqueada hasta 6 horas."
        )
    return (
        f"Demasiados intentos fallidos: el ingreso está bloqueado por {MINUTOS_BLOQUEO} minutos. "
        f"Podrás intentarlo de nuevo en {minutes} min {secs:02d} s."
    )

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
    "register_certifications",
    "register_coverage",
    "register_privacy",
]

RECOVERY_KEYS = [
    "recovery_email",
    "recovery_rut",
    "recovery_phone",
    "recovery_password",
    "recovery_confirm",
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

    # Limpia formularios después de un registro / recuperación exitosos.
    # Debe hacerse ANTES de crear los widgets.
    if st.session_state.pop("_clear_register", False):
        for key in REGISTER_KEYS:
            st.session_state.pop(key, None)

    if st.session_state.pop("_clear_recovery", False):
        for key in RECOVERY_KEYS:
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

            elif get_lock_remaining(email_clean) > 0:
                st.error(lock_message(get_lock_remaining(email_clean)))

            elif use_api():
                _login_api(email_clean, password, remember)

            else:
                user = get_user_by_email(email_clean)

                if user and not user["active"]:
                    st.error("Esta cuenta se encuentra desactivada.")

                elif not user or not verify_password(password, user["password_hash"]):
                    _login_failed(user["id"] if user else None, email_clean)

                else:
                    _login_success(user["id"], email_clean, remember)

        # Modo api: el backend aún no tiene correo configurado, así que se oculta la recuperación
        if not use_api():
            _password_recovery()

        st.markdown("---")
        st.caption("Usuarios de demostración: elige uno y pulsa «Ingresar».")

        d1, d2, d3 = st.columns(3)
        for col, (label, email, pwd, key) in zip(
            (d1, d2, d3),
            [
                ("🏠 Cliente", "cliente@overol.cl", "cliente123", "demo_cliente"),
                ("🛠️ Profesional", "carlos@overol.cl", "profesional123", "demo_profesional"),
                ("🛡️ Administrador", "admin@overol.cl", "admin123", "demo_admin"),
            ],
        ):
            with col:
                st.button(
                    label,
                    key=key,
                    use_container_width=True,
                    on_click=_fill_demo,
                    args=(email, pwd),
                )

        st.code(
            "Cliente        cliente@overol.cl / cliente123\n"
            "Profesional    carlos@overol.cl / profesional123\n"
            "Administrador  admin@overol.cl / admin123"
        )

    with register_tab:
        _register_form()


def _login_failed(user_id, email_clean):
    """Registra el intento fallido y muestra cuántos quedan antes del bloqueo local."""
    audit(user_id, "LOGIN_FAILED", "users", user_id, email_clean)

    remaining_attempts = MAX_INTENTOS_LOGIN - count_login_failures(email_clean)

    if remaining_attempts <= 0:
        st.error(lock_message(get_lock_remaining(email_clean)))
    elif use_api():
        st.error("Correo o contraseña incorrectos. " + API_BLOQUEO_AVISO)
    else:
        st.error(
            "Correo o contraseña incorrectos. "
            f"Te quedan {remaining_attempts} intento(s) antes del bloqueo."
        )


def _login_success(user_id, email_clean, remember, api_refresh=""):
    st.session_state.user_id = user_id
    st.session_state.authenticated = True
    st.session_state.pop("show_login", None)

    # Un ingreso exitoso reinicia el contador de fallos
    audit(user_id, "LOGIN_RESET", "users", user_id, email_clean)
    audit(user_id, "LOGIN", "users", user_id, "Inicio de sesión exitoso")

    if remember:
        token = create_session(user_id, api_refresh=api_refresh)
        st.session_state["session_token"] = token
        st.session_state["_set_cookie"] = token
    else:
        st.session_state["_clear_cookie"] = True

    st.rerun()


def _login_api(email_clean, password, remember):
    """Modo api: valida las credenciales en el backend y crea el usuario espejo local."""
    try:
        me = api_client.login(email_clean, password)
        user_id = upsert_api_user(me)
    except api_client.ApiError as error:
        api_client.clear_tokens()
        if error.status in (400, 401):
            local = get_user_by_email(email_clean)
            _login_failed(local["id"] if local else None, email_clean)
        else:
            st.error(str(error))
        return
    except ValueError as error:
        api_client.clear_tokens()
        st.error(f"No se pudo iniciar sesión: {error}")
        return

    _login_success(user_id, email_clean, remember, api_client.get_refresh_token())


def _password_recovery():
    """Historia 007: recuperar la contraseña verificando la identidad del usuario."""
    with st.expander("¿Olvidaste tu contraseña?"):
        st.caption(
            "Para verificar tu identidad ingresa el correo, el RUT y el teléfono "
            "con los que te registraste."
        )

        with st.form("recovery_form"):
            r_email = st.text_input("Correo electrónico", key="recovery_email")
            r_rut = st.text_input("RUT", placeholder="12345678-5", key="recovery_rut")
            r_phone = st.text_input("Teléfono registrado", key="recovery_phone")
            r_new = st.text_input(
                "Nueva contraseña",
                type="password",
                help="Mínimo 8 caracteres, con al menos una letra y un número.",
                key="recovery_password",
            )
            r_confirm = st.text_input(
                "Confirmar nueva contraseña",
                type="password",
                key="recovery_confirm",
            )
            submitted = st.form_submit_button(
                "Cambiar contraseña", use_container_width=True
            )

        if not submitted:
            return

        email_clean = r_email.strip().lower()

        locked = get_lock_remaining(
            email_clean, action="RECOVERY_FAILED", reset_action="RECOVERY_RESET"
        )
        if locked > 0:
            st.error(lock_message(locked))
            return

        user = get_user_by_email(email_clean) if email_clean else None
        profile = get_user_profile(user["id"]) if user else None

        phone_ok = True
        if profile and profile["phone"]:
            phone_ok = re.sub(r"\D", "", r_phone) == re.sub(r"\D", "", profile["phone"])

        identity_ok = bool(
            user
            and user["active"]
            and user["rut"] == normalize_rut(r_rut)
            and phone_ok
        )

        if not identity_ok:
            audit(
                user["id"] if user else None,
                "RECOVERY_FAILED",
                "users",
                user["id"] if user else None,
                email_clean,
            )
            st.error("Los datos ingresados no coinciden con ninguna cuenta.")
            return

        problems = validate_password_strength(r_new)
        if problems:
            st.error("La contraseña necesita " + ", ".join(problems) + ".")
            return

        if r_new != r_confirm:
            st.error("Las contraseñas no coinciden.")
            return

        conn = get_connection()
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(r_new), user["id"]),
        )
        conn.commit()
        conn.close()

        audit(user["id"], "PASSWORD_RESET", "users", user["id"],
              "Contraseña restablecida")
        audit(user["id"], "RECOVERY_RESET", "users", user["id"], email_clean)
        flash("Contraseña actualizada. Ya puedes iniciar sesión.")
        st.session_state["_clear_recovery"] = True
        st.rerun()


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

    oficio = certificaciones = ""
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
        certificaciones = st.text_input(
            "Certificaciones (opcional)",
            placeholder="Ej: Certificación SEC clase D",
            key="register_certifications",
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

    # Modo api: el backend Django responde 500 ante otros caracteres; se valida aquí mientras tanto
    elif use_api():
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

    # En modo api los duplicados los valida el backend
    if not errores and not use_api():
        if get_user_by_email(email):
            errores.append("Ya existe una cuenta con ese correo.")

        conn = get_connection()
        existing_rut = conn.execute(
            "SELECT id FROM users WHERE rut = ?",
            (normalize_rut(rut),),
        ).fetchone()
        conn.close()

        if existing_rut:
            errores.append("Ya existe una cuenta asociada a ese RUT.")

    if errores:
        for error in errores:
            st.error(error)
        return

    role = "cliente" if tipo == "Cliente" else "profesional"
    full_name = f"{nombre.strip()} {apellido.strip()}"

    if use_api():
        user_id = _register_api(
            nombre, apellido, rut, email, telefono, direccion, comuna, role, password
        )
        if user_id is None:
            return

        # El backend todavía no guarda oficio, experiencia ni cobertura:
        # quedan en el espejo local para que el panel del profesional funcione.
        if role == "profesional" and not get_professional_by_user(user_id):
            conn = get_connection()
            try:
                _insert_local_professional(
                    conn, user_id, oficio, anios, certificaciones, comunas_trabajo
                )
                conn.commit()
            finally:
                conn.close()

    else:
        conn = get_connection()

        try:
            cur = conn.execute(
                """
                INSERT INTO users
                (name, rut, email, password_hash, role, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    full_name,
                    normalize_rut(rut),
                    email.strip().lower(),
                    hash_password(password),
                    role,
                    now_str(),
                ),
            )

            user_id = cur.lastrowid

            if role == "profesional":
                _insert_local_professional(
                    conn, user_id, oficio, anios, certificaciones, comunas_trabajo
                )

            conn.commit()

        except sqlite3.IntegrityError:
            conn.rollback()
            st.error("El correo o el RUT ya están registrados.")
            return

        finally:
            conn.close()

    save_user_profile(
        user_id,
        telefono,
        comuna,
        "WhatsApp",
        oficio if role == "profesional" else "",
        "",
        direccion,
    )

    audit(user_id, "REGISTER", "users", user_id, f"Registro como {role}")
    audit(user_id, "PRIVACY_ACCEPTED", "users", user_id,
          f"Política de privacidad versión {PRIVACY_POLICY_VERSION}")

    flash("Cuenta creada correctamente. Ya puedes iniciar sesión.")
    st.session_state["_clear_register"] = True
    st.rerun()


def _insert_local_professional(conn, user_id, oficio, anios, certificaciones, comunas_trabajo):
    cur = conn.execute(
        """
        INSERT INTO professionals
        (user_id, trade, specialties, certifications,
         experience, visit_fee, verified,
         verification_status, availability, coverage)
        VALUES (?, ?, ?, '', '', '', 0, 'Pendiente', 1, ?)
        """,
        (user_id, oficio, oficio, ",".join(comunas_trabajo)),
    )
    professional_id = cur.lastrowid
    insert_trade(
        conn,
        professional_id,
        oficio,
        int(anios) if anios else None,
        [],
        certificaciones,
    )
    sync_professional_summary(conn, professional_id)


def _register_api(nombre, apellido, rut, email, telefono, direccion, comuna, role, password):
    """Modo api: crea la cuenta en el backend y su espejo local. Devuelve el id local o None."""
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
        # El backend exige un objeto no vacío; la tarifa se completa después en el perfil
        payload["professional_profile"] = {"visit_fee": 0}

    try:
        api_client.register(payload)
    except api_client.ApiError as error:
        st.error(str(error))
        return None

    return upsert_api_user(payload)
