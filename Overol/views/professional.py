"""Vistas del rol Profesional (RF 001, 004, 005, 006, 007, 009)."""

import re
import secrets
from html import escape
from pathlib import Path

import streamlit as st

from core.constants import (
    COMUNAS,
    ESPECIALIDADES,
    ESTADOS_SOLICITUD,
    OFICIOS,
    UPLOAD_DIR,
)
from core.database import (
    audit,
    change_request_status,
    get_claims_for_professional,
    get_connection,
    get_professional_by_user,
    get_professional_rating,
    get_requests_for_professional,
    get_verification_documents,
    now_str,
)
from ui.components import (
    empty_state,
    flash,
    hero,
    initials,
    section,
    security_note,
    status_badge,
)
from views.shared import user_profile_page

MAX_UPLOAD_MB = 5

# Primeros bytes (firma) válidos para cada extensión permitida
SIGNATURES = {
    ".pdf": b"%PDF",
    ".png": b"\x89PNG",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


def professional_dashboard(user):
    professional = get_professional_by_user(user["id"])

    if not professional:
        st.error(
            "No se encontró el perfil profesional asociado a esta cuenta."
        )
        return

    hero(
        "Panel del profesional",
        "Gestiona solicitudes, perfil, disponibilidad, cobertura, reputación "
        "y capacitación profesional.",
    )

    menu = st.radio(
        "Navegación",
        [
            "📋 Solicitudes",
            "👤 Mi perfil",
            "📍 Cobertura",
            "⭐ Reputación",
            "🪪 Datos personales",
            "🎓 Desarrollo profesional",
            "🛠️ Posventa",
        ],
        horizontal=True,
        key="professional_navigation",
    )

    if menu == "📋 Solicitudes":
        professional_requests(user, professional)

    elif menu == "👤 Mi perfil":
        professional_profile(user, professional)

    elif menu == "📍 Cobertura":
        professional_coverage(user, professional)

    elif menu == "⭐ Reputación":
        professional_reputation(professional)

    elif menu == "🪪 Datos personales":
        user_profile_page(user)

    elif menu == "🎓 Desarrollo profesional":
        professional_training(user, professional)

    elif menu == "🛠️ Posventa":
        professional_claims(user, professional)


def professional_requests(user, professional):
    section("📋 Solicitudes recibidas")

    requests = get_requests_for_professional(professional["id"])

    if not requests:
        empty_state(
            "📋",
            "Aún no tienes solicitudes",
            "Completa tu perfil y tu cobertura para que los clientes te encuentren.",
        )
        return

    pending = sum(1 for r in requests if r["status"] == "Pendiente")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total", len(requests))
    m2.metric("Pendientes de responder", pending)
    m3.metric("Completadas", sum(1 for r in requests if r["status"] == "Completada"))

    status_filter = st.selectbox(
        "Filtrar por estado",
        ["Todas"] + ESTADOS_SOLICITUD,
        key="professional_requests_filter",
    )

    for request in requests:
        if status_filter != "Todas" and request["status"] != status_filter:
            continue

        rid = request["id"]

        with st.container(border=True):
            top = st.columns([4, 1])

            with top[0]:
                st.markdown(f"### Solicitud #{rid} · {request['client_name']}")

            with top[1]:
                status_badge(request["status"])

            d1, d2 = st.columns(2)

            with d1:
                st.write(f"**Servicio:** {request['service']}")
                st.write(f"**Comuna:** {request['commune']} · **Zona:** {request['home_zone']}")

            with d2:
                st.write(
                    f"**Fecha tentativa:** {request['tentative_date']} · "
                    f"{request['tentative_time']}"
                )

            st.write(f"**Descripción:** {request['description']}")

            if request["status"] == "Pendiente":
                c1, c2 = st.columns(2)

                with c1:
                    if st.button(
                        "✓ Aceptar",
                        type="primary",
                        use_container_width=True,
                        key=f"pro_accept_{rid}",
                    ):
                        _transition(user, professional, rid, "Aceptada",
                                    ["Pendiente"], "Solicitud aceptada por profesional")

                with c2:
                    if st.button(
                        "✕ Rechazar",
                        use_container_width=True,
                        key=f"pro_reject_{rid}",
                    ):
                        _transition(user, professional, rid, "Rechazada",
                                    ["Pendiente"], "Solicitud rechazada por profesional",
                                    kind="warning")

            if request["status"] == "Aceptada":
                if st.button(
                    "Marcar como completada",
                    type="primary",
                    key=f"pro_complete_{rid}",
                ):
                    _transition(user, professional, rid, "Completada",
                                ["Aceptada"], "Servicio completado por profesional")


def _transition(user, professional, request_id, new_status, allowed_from, detail, kind="success"):
    """Aplica el cambio de estado verificando estado actual y pertenencia."""
    if change_request_status(
        request_id, new_status, allowed_from, professional_id=professional["id"]
    ):
        audit(user["id"], "UPDATE", "requests", request_id, detail)
        flash(f"Solicitud #{request_id}: {new_status.lower()}.", kind)
    else:
        flash("La solicitud ya había cambiado de estado.", "warning")

    st.rerun()


def _fee_to_number(text):
    digits = re.sub(r"\D", "", text or "")
    return int(digits) if digits else 0


def professional_profile(user, professional):
    section("👤 Mi perfil profesional")

    status = professional["verification_status"]
    docs = get_verification_documents(professional["id"])

    # --- Estado de verificación ---
    if status == "Aprobado":
        st.success("✓ Tu identidad está verificada. Apareces en las búsquedas de los clientes.")
    elif status == "Rechazado":
        st.error(
            "Tu verificación fue rechazada. Sube documentos actualizados "
            "para enviarla nuevamente a revisión."
        )
    elif docs:
        st.info("⏳ Tus documentos están en revisión por el equipo de Overol.")
    else:
        st.warning(
            "Para aparecer en las búsquedas debes subir tus documentos de "
            "verificación (más abajo en esta página)."
        )

    # --- Vista previa tal como la ven los clientes ---
    specialty_chips = "".join(
        f'<span class="chip">{escape(x.strip())}</span>'
        for x in professional["specialties"].split(",")
        if x.strip()
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
                        <div class="verified">{'✓ Identidad verificada' if professional['verified'] else '⏳ Verificación pendiente'}</div>
                    </div>
                </div>
                <p><b>Oficio:</b> {escape(professional["trade"])}</p>
                <div class="chips">{specialty_chips}</div>
                <p><b>Experiencia:</b> {escape(professional["experience"] or "No informada")}</p>
                <p><b>Certificaciones:</b> {escape(professional["certifications"] or "No informadas")}</p>
                <p><b>Tarifa de visita:</b> {escape(professional["visit_fee"] or "Por definir")}</p>
            </div>
            """.splitlines()
        ),
        unsafe_allow_html=True,
    )

    # --- Edición ---
    with st.expander("✏️ Editar mi perfil profesional"):
        with st.form("professional_profile_form"):
            trade = st.selectbox(
                "Oficio principal",
                OFICIOS,
                index=OFICIOS.index(professional["trade"])
                if professional["trade"] in OFICIOS
                else 0,
            )

            current_specialties = [
                x.strip() for x in professional["specialties"].split(",") if x.strip()
            ]
            specialties = st.multiselect(
                "Especialidades",
                ESPECIALIDADES,
                default=[x for x in current_specialties if x in ESPECIALIDADES],
            )

            experience = st.text_input(
                "Experiencia",
                value=professional["experience"] or "",
                placeholder="Ej: 8 años de experiencia",
            )

            certifications = st.text_input(
                "Certificaciones",
                value=professional["certifications"] or "",
            )

            fee = st.number_input(
                "Tarifa de visita (CLP)",
                min_value=0,
                max_value=500000,
                step=1000,
                value=_fee_to_number(professional["visit_fee"]),
                help="Déjala en 0 si prefieres informarla al cliente directamente.",
            )

            saved = st.form_submit_button(
                "Guardar cambios",
                type="primary",
                use_container_width=True,
            )

        if saved:
            if not specialties:
                st.error("Selecciona al menos una especialidad.")
            else:
                fee_text = f"${fee:,}".replace(",", ".") if fee else ""

                conn = get_connection()
                conn.execute(
                    """
                    UPDATE professionals
                    SET trade = ?, specialties = ?, experience = ?,
                        certifications = ?, visit_fee = ?
                    WHERE id = ?
                    """,
                    (
                        trade,
                        ",".join(specialties),
                        experience.strip(),
                        certifications.strip(),
                        fee_text,
                        professional["id"],
                    ),
                )
                conn.commit()
                conn.close()

                audit(user["id"], "UPDATE", "professionals", professional["id"],
                      "Actualización del perfil profesional")
                flash("Perfil actualizado correctamente.")
                st.rerun()

    st.divider()
    professional_verification_upload(user)

    security_note(
        "El RUT y los documentos de identidad son información sensible. "
        "No se muestran públicamente."
    )


def professional_coverage(user, professional):
    section("📍 Cobertura y disponibilidad")

    current_coverage = [
        x.strip()
        for x in professional["coverage"].split(",")
        if x.strip()
    ]

    coverage = st.multiselect(
        "Comunas donde realizas servicios",
        COMUNAS,
        default=current_coverage,
    )

    availability = st.toggle(
        "Disponible para recibir solicitudes",
        value=bool(professional["availability"]),
    )

    if st.button(
        "Guardar cobertura",
        use_container_width=True,
        type="primary",
    ):
        conn = get_connection()

        conn.execute(
            """
            UPDATE professionals
            SET coverage = ?, availability = ?
            WHERE id = ?
            """,
            (
                ",".join(coverage),
                1 if availability else 0,
                professional["id"],
            ),
        )

        conn.commit()
        conn.close()

        audit(
            user["id"],
            "UPDATE",
            "professionals",
            professional["id"],
            "Actualización de cobertura/disponibilidad",
        )

        flash(
            "Cobertura y disponibilidad actualizadas."
        )
        st.rerun()

    st.info(
        "Los clientes podrán encontrar tu perfil cuando la comuna "
        "seleccionada esté dentro de tu cobertura."
    )


def professional_reputation(professional):
    section("⭐ Reputación")

    total, average = get_professional_rating(
        professional["id"]
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Calificación",
        f"★ {average}" if total else "Sin datos",
    )

    c2.metric(
        "Evaluaciones",
        total,
    )

    c3.metric(
        "Estado",
        "Verificado" if professional["verified"] else "Pendiente",
    )

    conn = get_connection()

    ratings = conn.execute(
        """
        SELECT
            r.*,
            u.name AS client_name
        FROM ratings r
        JOIN users u ON u.id = r.client_id
        WHERE r.professional_id = ?
        ORDER BY r.id DESC
        """,
        (professional["id"],),
    ).fetchall()

    conn.close()

    section("Historial de evaluaciones")

    if not ratings:
        st.info(
            "Todavía no tienes evaluaciones."
        )
        return

    for rating in ratings:
        average_rating = round(
            (
                rating["quality"]
                + rating["punctuality"]
                + rating["treatment"]
            ) / 3,
            1,
        )

        with st.container(border=True):
            st.markdown(
                f"### ★ {average_rating}"
            )
            st.write(
                f"**Calidad:** {rating['quality']}/5"
            )
            st.write(
                f"**Puntualidad:** {rating['punctuality']}/5"
            )
            st.write(
                f"**Trato:** {rating['treatment']}/5"
            )
            st.write(
                f"**Comentario:** "
                f"{rating['comment'] or 'Sin comentario'}"
            )

            st.caption(
                "El historial de evaluaciones se conserva "
                "para trazabilidad."
            )


def professional_training(user, professional):
    section("🎓 Centro de Desarrollo Profesional")

    conn = get_connection()
    contents = conn.execute(
        """
        SELECT *
        FROM training_content
        WHERE active = 1
        ORDER BY id
        """
    ).fetchall()

    completed = conn.execute(
        """
        SELECT content_id
        FROM training_progress
        WHERE professional_id = ?
        """,
        (professional["id"],),
    ).fetchall()

    completed_ids = {
        row["content_id"]
        for row in completed
    }

    conn.close()

    if not contents:
        st.info(
            "No hay contenidos disponibles."
        )
        return

    filter_category = st.selectbox(
        "Categoría",
        ["Todas"] + sorted({c["category"] for c in contents}),
        key="training_filter",
    )

    for content in contents:
        if (
            filter_category != "Todas"
            and content["category"] != filter_category
        ):
            continue

        with st.container(border=True):
            st.markdown(
                f"### {content['title']}"
            )

            st.caption(
                f"{content['content_type']} · "
                f"{content['category']}"
            )

            st.write(
                content["description"]
            )

            if content["external_url"]:
                st.link_button(
                    "Ver recurso oficial",
                    content["external_url"],
                )

            if content["id"] in completed_ids:
                st.success(
                    "✓ Contenido completado."
                )
            else:
                if st.button(
                    "Marcar como visto/completado",
                    key=f"training_{content['id']}",
                ):
                    conn = get_connection()

                    conn.execute(
                        """
                        INSERT OR IGNORE INTO training_progress
                        (professional_id, content_id, completed_at)
                        VALUES (?, ?, ?)
                        """,
                        (
                            professional["id"],
                            content["id"],
                            now_str(),
                        ),
                    )

                    conn.commit()
                    conn.close()

                    audit(
                        user["id"],
                        "CREATE",
                        "training_progress",
                        content["id"],
                        "Contenido completado",
                    )

                    flash(
                        "Contenido marcado como completado."
                    )
                    st.rerun()


def professional_claims(user, professional):
    section("🛠️ Reclamos de posventa")

    claims = get_claims_for_professional(
        professional["id"]
    )

    if not claims:
        empty_state("🛠️", "No tienes reclamos registrados", "Aquí aparecerán los reclamos de posventa de tus clientes.")
        return

    for claim in claims:
        with st.container(border=True):
            st.markdown(
                f"### Reclamo #{claim['id']}"
            )
            status_badge(claim["status"])

            st.write(
                f"**Cliente:** {claim['client_name']}"
            )
            st.write(
                f"**Motivo:** {claim['reason']}"
            )

            if claim["response"]:
                st.write(
                    f"**Tu respuesta:** {claim['response']}"
                )

            if claim["status"] == "Abierto":
                response = st.text_area(
                    "Respuesta al cliente",
                    key=f"claim_response_{claim['id']}",
                )

                if st.button(
                    "Responder reclamo",
                    key=f"respond_claim_{claim['id']}",
                ):
                    if not response.strip():
                        st.warning(
                            "Escribe una respuesta."
                        )
                    else:
                        conn = get_connection()

                        conn.execute(
                            """
                            UPDATE claims
                            SET response = ?,
                                status = 'En mediación',
                                updated_at = ?
                            WHERE id = ? AND professional_id = ? AND status = 'Abierto'
                            """,
                            (
                                response.strip(),
                                now_str(),
                                claim["id"],
                                professional["id"],
                            ),
                        )

                        conn.commit()
                        conn.close()

                        audit(
                            user["id"],
                            "UPDATE",
                            "claims",
                            claim["id"],
                            "Respuesta de profesional",
                        )

                        st.success(
                            "Respuesta enviada al cliente."
                        )
                        st.rerun()


def professional_verification_upload(user):
    """
    Flujo para demostrar RNF-SEG-05. No publica los archivos: guarda el archivo
    en una carpeta local de demostración y sus metadatos en la base de datos.
    """
    professional = get_professional_by_user(user["id"])

    if not professional:
        return

    section("🪪 Documentos para verificación")

    st.warning(
        "DEMO: los archivos se guardan localmente. "
        "En producción deben almacenarse en un servicio seguro "
        "con control de acceso."
    )

    docs = get_verification_documents(professional["id"])

    if docs:
        st.markdown("**Documentos enviados**")
        for doc in docs:
            st.caption(
                f"📄 {doc['document_type']} — {doc['original_name']} "
                f"· {doc['uploaded_at']}"
            )

    document_type = st.selectbox(
        "Tipo de documento",
        ["Documento de identidad", "Certificación", "Otro respaldo"],
        key="document_type",
    )

    upload_round = st.session_state.get("_upload_round", 0)

    uploaded = st.file_uploader(
        f"Selecciona un archivo (PDF, PNG o JPG · máx. {MAX_UPLOAD_MB} MB)",
        type=["pdf", "png", "jpg", "jpeg"],
        key=f"verification_upload_{upload_round}",
    )

    if uploaded and st.button(
        "Enviar documento para revisión",
        type="primary",
        key="send_document",
    ):
        content = uploaded.getvalue()
        extension = Path(uploaded.name).suffix.lower()

        # Validación real del contenido (no solo de la extensión)
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            st.error(f"El archivo supera el máximo de {MAX_UPLOAD_MB} MB.")
            return

        expected = SIGNATURES.get(extension)
        if not expected or not content.startswith(expected):
            st.error(
                "El contenido del archivo no corresponde a su extensión. "
                "Sube un PDF, PNG o JPG válido."
            )
            return

        safe_name = f"{user['id']}_{secrets.token_hex(8)}{extension}"
        (UPLOAD_DIR / safe_name).write_bytes(content)

        conn = get_connection()

        conn.execute(
            """
            INSERT INTO verification_documents
            (professional_id, document_type, original_name, stored_name, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                professional["id"],
                document_type,
                Path(uploaded.name).name,
                safe_name,
                now_str(),
            ),
        )

        # Un profesional rechazado vuelve a la cola de revisión; uno ya
        # aprobado conserva su estado al agregar respaldos adicionales.
        conn.execute(
            """
            UPDATE professionals
            SET verification_status = 'Pendiente'
            WHERE id = ? AND verification_status = 'Rechazado'
            """,
            (professional["id"],),
        )

        conn.commit()
        conn.close()

        audit(
            user["id"],
            "UPLOAD",
            "verification_documents",
            professional["id"],
            f"Documento enviado: {document_type}",
        )

        st.session_state["_upload_round"] = upload_round + 1
        flash("Documento enviado para revisión administrativa.")
        st.rerun()
