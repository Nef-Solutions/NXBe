"""Vistas del rol Administrador (RF 001, 008, 009)."""

import streamlit as st

from core.constants import ESTADOS_RECLAMO, ROLES, UPLOAD_DIR
from core.database import (
    audit,
    get_all_claims,
    get_connection,
    get_verification_documents,
    now_str,
)
from ui.components import (
    empty_state,
    flash,
    hero,
    metric_card,
    section,
    security_note,
    status_badge,
)


def admin_dashboard(user):
    hero(
        "Panel de administración",
        "Gestiona verificaciones, usuarios, reputación, reclamos, contenidos "
        "y trazabilidad de las acciones críticas.",
    )

    menu = st.radio(
        "Navegación administrativa",
        [
            "📊 Resumen",
            "🪪 Verificación",
            "👥 Usuarios",
            "⭐ Moderación",
            "🛠️ Posventa",
            "🎓 Contenidos",
            "📜 Trazabilidad",
        ],
        horizontal=True,
        key="admin_navigation",
    )

    if menu == "📊 Resumen":
        admin_summary()

    elif menu == "🪪 Verificación":
        admin_verification(user)

    elif menu == "👥 Usuarios":
        admin_users(user)

    elif menu == "⭐ Moderación":
        admin_moderation(user)

    elif menu == "🛠️ Posventa":
        admin_claims(user)

    elif menu == "🎓 Contenidos":
        admin_training(user)

    elif menu == "📜 Trazabilidad":
        admin_audit(user)


def admin_summary():
    section("📊 Resumen de la plataforma")

    conn = get_connection()

    def count(sql):
        return conn.execute(sql).fetchone()["n"]

    metrics = [
        ("👥", "Usuarios", count("SELECT COUNT(*) AS n FROM users")),
        ("👷", "Profesionales", count("SELECT COUNT(*) AS n FROM professionals")),
        ("✅", "Verificados", count("SELECT COUNT(*) AS n FROM professionals WHERE verified = 1")),
        ("⏳", "Pendientes", count(
            "SELECT COUNT(*) AS n FROM professionals WHERE verification_status = 'Pendiente'"
        )),
        ("📋", "Solicitudes", count("SELECT COUNT(*) AS n FROM requests")),
        ("🛠️", "Reclamos", count("SELECT COUNT(*) AS n FROM claims")),
    ]

    request_rows = conn.execute(
        """
        SELECT status, COUNT(*) AS total
        FROM requests
        GROUP BY status
        """
    ).fetchall()

    claim_rows = conn.execute(
        """
        SELECT status, COUNT(*) AS total
        FROM claims
        GROUP BY status
        """
    ).fetchall()

    conn.close()

    cols = st.columns(6)
    for col, (icon, label, value) in zip(cols, metrics):
        with col:
            metric_card(value, label, icon)

    left, right = st.columns(2)

    with left:
        section("Estado de solicitudes")
        if request_rows:
            st.bar_chart(
                {row["status"]: row["total"] for row in request_rows},
                color="#F59E0B",
            )
        else:
            empty_state("📋", "Aún no hay solicitudes")

    with right:
        section("Estado de reclamos")
        if claim_rows:
            st.bar_chart(
                {row["status"]: row["total"] for row in claim_rows},
                color="#111827",
            )
        else:
            empty_state("🛠️", "Aún no hay reclamos")


def admin_verification(user):
    section("🪪 Verificación de identidad y certificaciones")

    conn = get_connection()
    pending = conn.execute(
        """
        SELECT
            p.*,
            u.name,
            u.rut,
            u.email
        FROM professionals p
        JOIN users u ON u.id = p.user_id
        WHERE p.verification_status = 'Pendiente'
        ORDER BY p.id
        """
    ).fetchall()
    conn.close()

    if not pending:
        st.success("No existen solicitudes de verificación pendientes.")
        return

    for professional in pending:
        pid = professional["id"]
        documents = get_verification_documents(pid)

        with st.container(border=True):
            top = st.columns([4, 1])
            with top[0]:
                st.markdown(f"### {professional['name']}")
            with top[1]:
                status_badge(professional["verification_status"])

            d1, d2 = st.columns(2)
            with d1:
                st.write(f"**Oficio:** {professional['trade']}")
                st.write(f"**RUT:** {professional['rut']}")
                st.write(f"**Correo:** {professional['email']}")
            with d2:
                st.write(f"**Experiencia:** {professional['experience'] or 'No informada'}")
                st.write(f"**Certificaciones:** {professional['certifications'] or 'No informadas'}")

            st.markdown("**Documentos adjuntos**")

            if not documents:
                st.warning(
                    "Este profesional aún no ha subido documentos. "
                    "No debería aprobarse sin respaldo."
                )

            for doc in documents:
                file_path = UPLOAD_DIR / doc["stored_name"]
                row = st.columns([4, 1])
                row[0].caption(
                    f"📄 {doc['document_type']} — {doc['original_name']} · {doc['uploaded_at']}"
                )
                if file_path.exists():
                    row[1].download_button(
                        "Descargar",
                        data=file_path.read_bytes(),
                        file_name=doc["original_name"],
                        key=f"download_doc_{doc['id']}",
                    )
                else:
                    row[1].caption("Archivo no disponible")

            security_note(
                "Los documentos solo son visibles para administradores. "
                "En una implementación real deben almacenarse con control de acceso."
            )

            c1, c2 = st.columns(2)

            with c1:
                if st.button(
                    "✓ Aprobar verificación",
                    type="primary",
                    use_container_width=True,
                    key=f"admin_approve_{pid}",
                ):
                    _set_verification(user, pid, True)

            with c2:
                if st.button(
                    "✕ Rechazar verificación",
                    use_container_width=True,
                    key=f"admin_reject_{pid}",
                ):
                    _set_verification(user, pid, False)


def _set_verification(user, professional_id, approved):
    conn = get_connection()
    conn.execute(
        """
        UPDATE professionals
        SET verified = ?, verification_status = ?
        WHERE id = ? AND verification_status = 'Pendiente'
        """,
        (1 if approved else 0, "Aprobado" if approved else "Rechazado", professional_id),
    )
    conn.commit()
    conn.close()

    audit(
        user["id"],
        "VERIFY",
        "professionals",
        professional_id,
        "Verificación aprobada" if approved else "Verificación rechazada",
    )

    flash(
        "Profesional aprobado." if approved else "Profesional rechazado.",
        "success" if approved else "warning",
    )
    st.rerun()


def admin_users(user):
    section("👥 Gestión de usuarios")

    conn = get_connection()

    users = conn.execute(
        """
        SELECT id, name, rut, email, role, active, created_at
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    for account in users:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(
                [2.3, 1, 2.5, 1]
            )

            with c1:
                st.write(
                    f"**{account['name']}**"
                )
                st.caption(
                    account["rut"]
                )

            with c2:
                st.write(
                    ROLES.get(
                        account["role"],
                        account["role"],
                    )
                )

            with c3:
                st.write(
                    account["email"]
                )

            with c4:
                if account["active"]:
                    status_badge("Activo")
                else:
                    status_badge("Suspendido")

            if account["id"] == user["id"]:
                st.caption(
                    "No puedes suspender tu propia cuenta."
                )
                continue

            action_label = (
                "Suspender"
                if account["active"]
                else "Reactivar"
            )

            if st.button(
                action_label,
                key=f"toggle_user_{account['id']}",
            ):
                new_status = 0 if account["active"] else 1

                conn = get_connection()

                conn.execute(
                    """
                    UPDATE users
                    SET active = ?
                    WHERE id = ?
                    """,
                    (
                        new_status,
                        account["id"],
                    ),
                )

                conn.commit()
                conn.close()

                audit(
                    user["id"],
                    "UPDATE",
                    "users",
                    account["id"],
                    (
                        "Usuario suspendido"
                        if new_status == 0
                        else "Usuario reactivado"
                    ),
                )

                flash(
                    "Estado de usuario actualizado."
                )
                st.rerun()


def admin_moderation(user):
    section("⭐ Moderación de reseñas")

    conn = get_connection()

    ratings = conn.execute(
        """
        SELECT
            r.*,
            uc.name AS client_name,
            up.name AS professional_name
        FROM ratings r
        JOIN users uc ON uc.id = r.client_id
        JOIN professionals p ON p.id = r.professional_id
        JOIN users up ON up.id = p.user_id
        ORDER BY r.id DESC
        """
    ).fetchall()

    reports = conn.execute(
        """
        SELECT
            rp.*,
            r.comment,
            up.name AS professional_name
        FROM reports rp
        JOIN ratings r ON r.id = rp.rating_id
        JOIN professionals p ON p.id = r.professional_id
        JOIN users up ON up.id = p.user_id
        ORDER BY rp.id DESC
        """
    ).fetchall()

    conn.close()

    if not ratings:
        st.info(
            "No existen evaluaciones."
        )
    else:
        for rating in ratings:
            average = round(
                (
                    rating["quality"]
                    + rating["punctuality"]
                    + rating["treatment"]
                ) / 3,
                1,
            )

            with st.container(border=True):
                st.markdown(
                    f"### {rating['professional_name']} · ★ {average}"
                )
                st.write(
                    f"Cliente: {rating['client_name']}"
                )
                st.write(
                    rating["comment"] or "Sin comentario"
                )

                c1, c2 = st.columns(2)

                with c1:
                    if st.button(
                        "Mantener reseña",
                        key=f"keep_rating_{rating['id']}",
                    ):
                        audit(
                            user["id"],
                            "MODERATE",
                            "ratings",
                            rating["id"],
                            "Reseña mantenida",
                        )
                        st.success(
                            "Reseña mantenida."
                        )

                with c2:
                    if st.button(
                        "Reportar reseña",
                        key=f"report_rating_{rating['id']}",
                    ):
                        conn = get_connection()

                        conn.execute(
                            """
                            INSERT INTO reports
                            (rating_id, reason, status, created_at)
                            VALUES (?, ?, 'Pendiente', ?)
                            """,
                            (
                                rating["id"],
                                "Reportada para revisión administrativa.",
                                now_str(),
                            ),
                        )

                        conn.commit()
                        conn.close()

                        audit(
                            user["id"],
                            "CREATE",
                            "reports",
                            rating["id"],
                            "Reseña reportada",
                        )

                        flash(
                            "Reseña reportada."
                        , kind="warning")
                        st.rerun()

    section("Reportes pendientes")

    if not reports:
        st.info(
            "No existen reportes registrados."
        )
    else:
        for report in reports:
            with st.container(border=True):
                status_badge(report["status"])
                st.write(
                    f"Profesional: {report['professional_name']}"
                )
                st.write(
                    f"Motivo: {report['reason']}"
                )

                if report["status"] == "Pendiente":
                    if st.button(
                        "Cerrar revisión",
                        key=f"close_report_{report['id']}",
                    ):
                        conn = get_connection()

                        conn.execute(
                            """
                            UPDATE reports
                            SET status = 'Revisado'
                            WHERE id = ?
                            """,
                            (report["id"],),
                        )

                        conn.commit()
                        conn.close()

                        audit(
                            user["id"],
                            "MODERATE",
                            "reports",
                            report["id"],
                            "Reporte revisado",
                        )

                        flash(
                            "Reporte revisado."
                        )
                        st.rerun()


def admin_claims(user):
    section("🛠️ Posventa y mediación")

    claims = get_all_claims()

    if not claims:
        st.info(
            "No existen reclamos."
        )
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
                f"**Profesional:** {claim['professional_name']}"
            )

            st.write(
                f"**Motivo:** {claim['reason']}"
            )

            if claim["response"]:
                st.write(
                    f"**Respuesta:** {claim['response']}"
                )

            if claim["status"] != "Cerrado":
                new_status = st.selectbox(
                    "Estado",
                    ESTADOS_RECLAMO,
                    index=(
                        ESTADOS_RECLAMO.index(claim["status"])
                        if claim["status"] in ESTADOS_RECLAMO
                        else 0
                    ),
                    key=f"claim_status_{claim['id']}",
                )

                resolution = st.text_area(
                    "Registro de resolución / mediación",
                    key=f"claim_resolution_{claim['id']}",
                )

                if st.button(
                    "Guardar resolución",
                    key=f"save_claim_{claim['id']}",
                ):
                    conn = get_connection()

                    conn.execute(
                        """
                        UPDATE claims
                        SET status = ?,
                            response = CASE
                                WHEN ? <> '' THEN ?
                                ELSE response
                            END,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            new_status,
                            resolution.strip(),
                            resolution.strip(),
                            now_str(),
                            claim["id"],
                        ),
                    )

                    conn.commit()
                    conn.close()

                    audit(
                        user["id"],
                        "UPDATE",
                        "claims",
                        claim["id"],
                        f"Estado={new_status}",
                    )

                    flash(
                        "Resolución registrada."
                    )
                    st.rerun()


def admin_training(user):
    section("🎓 Centro de Desarrollo Profesional")

    conn = get_connection()

    contents = conn.execute(
        """
        SELECT *
        FROM training_content
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    for content in contents:
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
                st.write(
                    f"Recurso oficial: {content['external_url']}"
                )

            if content["active"]:
                if st.button(
                    "Desactivar contenido",
                    key=f"disable_training_{content['id']}",
                ):
                    conn = get_connection()

                    conn.execute(
                        """
                        UPDATE training_content
                        SET active = 0
                        WHERE id = ?
                        """,
                        (content["id"],),
                    )

                    conn.commit()
                    conn.close()

                    audit(
                        user["id"],
                        "UPDATE",
                        "training_content",
                        content["id"],
                        "Contenido desactivado",
                    )

                    flash(
                        "Contenido desactivado."
                    )
                    st.rerun()
            else:
                if st.button(
                    "Activar contenido",
                    key=f"enable_training_{content['id']}",
                ):
                    conn = get_connection()

                    conn.execute(
                        """
                        UPDATE training_content
                        SET active = 1
                        WHERE id = ?
                        """,
                        (content["id"],),
                    )

                    conn.commit()
                    conn.close()

                    audit(
                        user["id"],
                        "UPDATE",
                        "training_content",
                        content["id"],
                        "Contenido activado",
                    )

                    flash(
                        "Contenido activado."
                    )
                    st.rerun()

    st.markdown("---")
    st.markdown("### ➕ Crear contenido")

    title = st.text_input(
        "Título",
        key="new_training_title",
    )

    category = st.selectbox(
        "Categoría",
        ["Tributario", "Seguridad", "Gestión"],
        key="new_training_category",
    )

    content_type = st.selectbox(
        "Tipo",
        ["Guía", "Video"],
        key="new_training_type",
    )

    description = st.text_area(
        "Descripción",
        key="new_training_description",
    )

    external_url = st.text_input(
        "URL externa opcional",
        key="new_training_url",
    )

    if st.button(
        "Crear contenido",
        use_container_width=True,
        key="create_training",
    ):
        if not title.strip() or not description.strip():
            st.warning(
                "Completa título y descripción."
            )
        else:
            conn = get_connection()

            cur = conn.execute(
                """
                INSERT INTO training_content
                (title, category, content_type, description, external_url, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    title.strip(),
                    category,
                    content_type,
                    description.strip(),
                    external_url.strip(),
                ),
            )

            content_id = cur.lastrowid

            conn.commit()
            conn.close()

            audit(
                user["id"],
                "CREATE",
                "training_content",
                content_id,
                "Contenido creado",
            )

            st.success(
                "Contenido creado."
            )
            st.rerun()


def admin_audit(user):
    section("📜 Trazabilidad de información")

    st.write(
        "Registro de acciones relevantes realizadas dentro del prototipo."
    )

    conn = get_connection()

    logs = conn.execute(
        """
        SELECT
            a.*,
            u.name AS user_name,
            u.role AS user_role
        FROM audit_log a
        LEFT JOIN users u ON u.id = a.user_id
        ORDER BY a.id DESC
        LIMIT 200
        """
    ).fetchall()

    conn.close()

    if not logs:
        st.info(
            "Todavía no existen registros de trazabilidad."
        )
        return

    for log in logs:
        with st.container(border=True):
            st.write(
                f"**{log['created_at']}** · "
                f"{log['action']} · "
                f"{log['entity']}"
            )

            st.caption(
                f"Usuario: {log['user_name'] or 'Sistema'} "
                f"· Rol: {log['user_role'] or 'N/A'}"
            )

            if log["entity_id"]:
                st.write(
                    f"ID de entidad: {log['entity_id']}"
                )

            if log["details"]:
                st.write(
                    f"Detalle: {log['details']}"
                )
