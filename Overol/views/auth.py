"""Pantalla de inicio de sesión y registro."""

import sqlite3

import streamlit as st

from core.constants import OFICIOS
from core.database import (
    audit,
    count_recent_failed_logins,
    get_connection,
    get_user_by_email,
    now_str,
)
from core.security import (
    hash_password,
    normalize_rut,
    validate_email,
    validate_password_strength,
    validate_rut_dv,
    validate_rut_format,
    verify_password,
)
from ui.components import flash

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 10

REGISTER_KEYS = [
    "register_name",
    "register_rut",
    "register_email",
    "register_password",
    "register_confirm",
    "register_role",
    "register_trade",
    "register_experience",
    "register_certifications",
]


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

    # Limpia el formulario de registro después de un registro exitoso.
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

            login_submitted = st.form_submit_button(
                "Ingresar",
                use_container_width=True,
                type="primary",
            )

        if login_submitted:
            email_clean = email.strip().lower()

            if not email_clean or not password:
                st.error("Ingresa tu correo y tu contraseña.")

            elif count_recent_failed_logins(email_clean) >= MAX_FAILED_LOGINS:
                st.error(
                    "Demasiados intentos fallidos. "
                    f"Espera {LOCKOUT_MINUTES} minutos e inténtalo nuevamente."
                )

            else:
                user = get_user_by_email(email_clean)

                if user and not user["active"]:
                    st.error("Esta cuenta se encuentra desactivada.")

                elif not user or not verify_password(password, user["password_hash"]):
                    audit(
                        user["id"] if user else None,
                        "LOGIN_FAILED",
                        "users",
                        user["id"] if user else None,
                        email_clean,
                    )
                    st.error("Correo o contraseña incorrectos.")

                else:
                    st.session_state.user_id = user["id"]
                    st.session_state.authenticated = True
                    audit(
                        user["id"],
                        "LOGIN",
                        "users",
                        user["id"],
                        "Inicio de sesión exitoso",
                    )
                    st.rerun()

        st.markdown("---")
        st.caption("Usuarios de demostración:")
        st.code(
            "admin@overol.cl / admin123\n"
            "cliente@overol.cl / cliente123\n"
            "carlos@overol.cl / profesional123"
        )

    with register_tab:
        st.markdown("### Crear cuenta")

        nombre = st.text_input("Nombre completo", key="register_name")

        rut = st.text_input(
            "RUT",
            placeholder="12345678-5",
            key="register_rut",
        )

        email = st.text_input("Correo electrónico", key="register_email")

        password = st.text_input(
            "Contraseña",
            type="password",
            help="Mínimo 8 caracteres, con al menos una letra y un número.",
            key="register_password",
        )

        confirm = st.text_input(
            "Confirmar contraseña",
            type="password",
            key="register_confirm",
        )

        tipo = st.radio(
            "Tipo de cuenta",
            ["Cliente", "Profesional"],
            horizontal=True,
            key="register_role",
        )

        oficio = experiencia = certificaciones = ""

        if tipo == "Profesional":
            st.info(
                "Al registrarte como profesional se solicitará información "
                "para la posterior verificación administrativa."
            )

            oficio = st.selectbox(
                "Oficio principal",
                OFICIOS,
                key="register_trade",
            )

            experiencia = st.text_input(
                "Experiencia",
                placeholder="Ej: 5 años",
                key="register_experience",
            )

            certificaciones = st.text_input(
                "Certificaciones",
                placeholder="Ej: Certificación de gasfitería",
                key="register_certifications",
            )

        if st.button(
            "Crear cuenta",
            use_container_width=True,
            type="primary",
            key="register_button",
        ):
            errores = []

            if not nombre.strip():
                errores.append("Ingresa tu nombre.")

            if not validate_rut_format(rut):
                errores.append("El RUT debe tener formato válido, por ejemplo 12345678-5.")
            elif not validate_rut_dv(rut):
                errores.append("El RUT no es válido: revisa el dígito verificador.")

            if not validate_email(email):
                errores.append("Ingresa un correo válido.")

            faltantes = validate_password_strength(password)
            if faltantes:
                errores.append("La contraseña necesita " + ", ".join(faltantes) + ".")

            if password != confirm:
                errores.append("Las contraseñas no coinciden.")

            if not errores:
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
            conn = get_connection()

            try:
                cur = conn.execute(
                    """
                    INSERT INTO users
                    (name, rut, email, password_hash, role, active, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        nombre.strip(),
                        normalize_rut(rut),
                        email.strip().lower(),
                        hash_password(password),
                        role,
                        now_str(),
                    ),
                )

                user_id = cur.lastrowid

                if role == "profesional":
                    conn.execute(
                        """
                        INSERT INTO professionals
                        (user_id, trade, specialties, certifications,
                         experience, visit_fee, verified,
                         verification_status, availability, coverage)
                        VALUES (?, ?, ?, ?, ?, '', 0, 'Pendiente', 1, '')
                        """,
                        (
                            user_id,
                            oficio,
                            oficio,
                            certificaciones.strip(),
                            experiencia.strip(),
                        ),
                    )

                conn.commit()

            except sqlite3.IntegrityError:
                conn.rollback()
                st.error("El correo o el RUT ya están registrados.")
                return

            finally:
                conn.close()

            audit(user_id, "REGISTER", "users", user_id, f"Registro como {role}")

            flash("Cuenta creada correctamente. Ya puedes iniciar sesión.")
            st.session_state["_clear_register"] = True
            st.rerun()
