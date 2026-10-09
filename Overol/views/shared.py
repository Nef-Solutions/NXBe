"""Pantallas compartidas entre roles: perfil personal, perfil público del profesional y barra lateral."""

from datetime import datetime
from html import escape

import streamlit as st

from core.constants import COMUNAS, ROLES, ZONAS_HOGAR
from core.database import (
    audit,
    get_connection,
    get_professional_by_id,
    get_professional_rating,
    get_user_profile,
    now_str,
    save_user_profile,
)
from ui.components import flash, initials, section, security_note, stars


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

        commune = st.text_input(
            "📍 Comuna",
            placeholder="Ej: Maipú",
            key="profile_commune",
        )

        contact_preference = st.selectbox(
            "💬 ¿Cómo prefieres que te contacten?",
            ["WhatsApp", "Llamada telefónica", "Correo electrónico"],
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
        if not phone.strip():
            errors.append("Ingresa tu número de teléfono.")
        if not commune.strip():
            errors.append("Ingresa tu comuna.")
        if not service_interest.strip():
            errors.append("Cuéntanos qué necesitas o qué servicios realizas.")

        if errors:
            for error in errors:
                st.error(error)
            return False

        save_user_profile(
            user["id"],
            phone,
            commune,
            contact_preference,
            service_interest,
            bio,
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
    """Muestra y permite editar los datos personales guardados en la BD."""
    section("👤 Mi perfil personal")

    profile = get_user_profile(user["id"])

    if not profile:
        st.warning("Todavía no has completado tus datos personales.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Nombre:** {user['name']}")
        st.write(f"**Correo:** {user['email']}")
        st.write(f"**Rol:** {ROLES.get(user['role'], user['role'])}")
    with c2:
        st.write(f"**Teléfono:** {profile['phone']}")
        st.write(f"**Comuna:** {profile['commune']}")
        st.write(f"**Contacto:** {profile['contact_preference']}")

    if profile["service_interest"]:
        st.write(f"**Servicios / necesidades:** {profile['service_interest']}")
    if profile["bio"]:
        st.write(f"**Sobre mí:** {profile['bio']}")


def professional_profile_client(user_id, professional_id):
    professional = get_professional_by_id(professional_id)

    if not professional:
        st.error("Profesional no encontrado.")
        return

    total, average = get_professional_rating(professional_id)

    section(f"👤 Perfil de {professional['name']}")

    left, right = st.columns([1.1, 1])

    with left:
        specialty_chips = "".join(
            f'<span class="chip">{escape(x.strip())}</span>'
            for x in professional["specialties"].split(",")
            if x.strip()
        )
        rating_html = (
            f'<span class="stars">{stars(average)}</span> <b>{average}</b> '
            f'<span class="muted">· {total} evaluaciones</span>'
            if total
            else '<span class="muted">Aún sin evaluaciones</span>'
        )

        st.markdown(
            "".join(
                line.strip()
                for line in f"""
                <div class="card">
                    <div class="pro-head">
                        <div class="avatar">{escape(initials(professional["name"]))}</div>
                        <div>
                            <h2>{escape(professional["name"])}</h2>
                            <div class="verified">✓ Profesional verificado</div>
                        </div>
                    </div>
                    <p><b>Oficio:</b> {escape(professional["trade"])}</p>
                    <div class="chips">{specialty_chips}</div>
                    <p><b>Experiencia:</b> {escape(professional["experience"] or "No informada")}</p>
                    <p><b>Certificaciones:</b> {escape(professional["certifications"] or "No informadas")}</p>
                    <p><b>Tarifa de visita:</b> {escape(professional["visit_fee"] or "Por definir")}</p>
                    <p><b>Historial:</b> Servicios realizados y evaluaciones registradas en Overol.</p>
                    <div class="pro-rating">{rating_html}</div>
                </div>
                """.splitlines()
            ),
            unsafe_allow_html=True,
        )

        security_note(
            "El RUT y los documentos utilizados para verificación no se muestran "
            "en el perfil público. Solo se presenta el estado de verificación."
        )

    with right:
        st.markdown("### 📅 Solicitar visita")

        commune = st.selectbox(
            "Comuna del servicio",
            [
                x for x in COMUNAS
                if x in professional["coverage"].split(",")
            ] or COMUNAS,
            key=f"request_commune_{professional_id}",
        )

        home_zone = st.selectbox(
            "Zona del hogar",
            ZONAS_HOGAR,
            key=f"request_zone_{professional_id}",
        )

        date = st.date_input(
            "Fecha tentativa",
            min_value=datetime.today().date(),
            key=f"request_date_{professional_id}",
        )

        time = st.selectbox(
            "Horario tentativo",
            [
                "09:00 - 11:00",
                "11:00 - 13:00",
                "15:00 - 17:00",
                "17:00 - 19:00",
            ],
            key=f"request_time_{professional_id}",
        )

        description = st.text_area(
            "Descripción del trabajo",
            placeholder="Describe el problema o trabajo que necesitas realizar.",
            key=f"request_description_{professional_id}",
        )

        if st.button(
            "Enviar solicitud",
            use_container_width=True,
            key=f"send_request_{professional_id}",
        ):
            conn = get_connection()
            duplicated = conn.execute(
                """
                SELECT id FROM requests
                WHERE client_id = ? AND professional_id = ? AND status = 'Pendiente'
                """,
                (user_id, professional_id),
            ).fetchone()
            conn.close()

            if not description.strip():
                st.warning(
                    "La descripción del trabajo es obligatoria."
                )
            elif duplicated:
                st.warning(
                    f"Ya tienes la solicitud #{duplicated['id']} pendiente con este "
                    "profesional. Espera su respuesta o cancélala desde "
                    "«Mis solicitudes»."
                )
            else:
                conn = get_connection()

                cur = conn.execute(
                    """
                    INSERT INTO requests
                    (
                        client_id,
                        professional_id,
                        service,
                        home_zone,
                        commune,
                        tentative_date,
                        tentative_time,
                        description,
                        status,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente', ?, ?)
                    """,
                    (
                        user_id,
                        professional_id,
                        professional["trade"],
                        home_zone,
                        commune,
                        str(date),
                        time,
                        description.strip(),
                        now_str(),
                        now_str(),
                    ),
                )

                request_id = cur.lastrowid
                conn.commit()
                conn.close()

                audit(
                    user_id,
                    "CREATE",
                    "requests",
                    request_id,
                    f"Solicitud para profesional {professional_id}",
                )

                flash(
                    "Solicitud enviada. Puedes revisarla en «Mis solicitudes»."
                )
                st.session_state.pop("selected_professional", None)
                st.rerun()


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

            st.session_state.clear()
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
