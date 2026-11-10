"""Vistas del rol Administrador (RF 001, 008, 009)."""

from datetime import date, datetime
from html import escape
from math import ceil
from pathlib import Path

import streamlit as st

from core.constants import ESTADOS_RECLAMO, MAX_TEXTO, ROLES
from core.database import (
    AUDIT_SYSTEM,
    add_support_message,
    add_verification_message,
    audit,
    count_unread_verification_messages,
    decide_verification,
    get_all_claims,
    get_audit_filters,
    get_audit_log,
    get_connection,
    get_support_inbox,
    get_support_thread,
    get_verification_documents,
    get_verification_messages,
    legacy_plain_documents,
    mark_support_thread_read,
    mark_verification_messages_read,
    now_str,
    read_verification_document,
    set_support_ticket_status,
    set_user_active,
)

AUDIT_PAGE_SIZE = 20
from views.about import about_page
from ui.components import (
    empty_state,
    flash,
    hero,
    metric_card,
    nav_bar,
    section,
    security_note,
    status_badge,
    thread_message,
)


def admin_dashboard(user):
    menu = nav_bar(
        "admin_navigation",
        [
            "📊 Indicadores",
            "🪪 Verificación",
            "👥 Usuarios",
            "⭐ Moderación",
            "🛠️ Reclamos",
            "🎓 Contenidos",
            "📜 Trazabilidad",
            "💬 Soporte",
            "ℹ️ Quiénes somos",
        ],
        badges={"🪪 Verificación": count_unread_verification_messages()},
    )

    hero(
        "Panel de administración",
        "Gestiona verificaciones, usuarios, reputación, reclamos, contenidos "
        "y trazabilidad de las acciones críticas.",
    )

    if menu == "📊 Indicadores":
        admin_summary()

    elif menu == "🪪 Verificación":
        admin_verification(user)

    elif menu == "👥 Usuarios":
        admin_users(user)

    elif menu == "⭐ Moderación":
        admin_moderation(user)

    elif menu == "🛠️ Reclamos":
        admin_claims(user)

    elif menu == "🎓 Contenidos":
        admin_training(user)

    elif menu == "📜 Trazabilidad":
        admin_audit(user)

    elif menu == "💬 Soporte":
        admin_support(user)

    elif menu == "ℹ️ Quiénes somos":
        about_page()


def admin_summary():
    section("📊 Indicadores de la plataforma")

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
    professionals = conn.execute(
        """
        SELECT
            p.*,
            u.name,
            u.rut,
            u.email,
            (SELECT COUNT(*) FROM verification_messages m WHERE m.professional_id = p.id) AS messages,
            (SELECT COUNT(*) FROM verification_messages m
             WHERE m.professional_id = p.id AND m.from_admin = 0 AND m.read_by_admin = 0) AS unread
        FROM professionals p
        JOIN users u ON u.id = p.user_id
        WHERE p.verification_status = 'Pendiente'
           OR EXISTS (SELECT 1 FROM verification_messages m WHERE m.professional_id = p.id)
        ORDER BY p.verification_status != 'Pendiente', unread DESC, p.id
        """
    ).fetchall()
    conn.close()

    legacy = legacy_plain_documents()
    if legacy:
        st.warning(
            f"Hay {len(legacy)} archivo(s) antiguo(s) sin cifrar en documentos_verificacion/. "
            "Ya tienen su copia cifrada, pero no se borraron automáticamente: "
            "elimínalos cuando el equipo lo confirme."
        )

    if not professionals:
        st.success("No existen solicitudes de verificación pendientes ni mensajes.")
        return

    pending_total = sum(1 for p in professionals if p["verification_status"] == "Pendiente")
    unread_total = sum(p["unread"] for p in professionals)
    st.caption(f"{pending_total} pendientes de revisión · {unread_total} mensajes sin leer")

    for professional in professionals:
        pid = professional["id"]
        documents = get_verification_documents(pid)
        pending = professional["verification_status"] == "Pendiente"

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
                _document_row(user, doc)

            security_note(
                "Los documentos se guardan cifrados y solo los administradores pueden abrirlos. "
                "Cada vez que se abre uno queda registrado en la bitácora."
            )

            _verification_thread_admin(user, professional)

            if not pending:
                st.caption(
                    f"Decisión: {professional['verification_status']}"
                    + (f" · Motivo: {professional['verification_reason']}"
                       if professional["verification_reason"] else "")
                )
                continue

            # Aprobar o rechazar con motivo: va al hilo, a la bitácora y a la notificación
            with st.form(f"verif_decision_form_{pid}", clear_on_submit=True):
                reason = st.text_area(
                    "Motivo de la decisión",
                    max_chars=MAX_TEXTO,
                    placeholder="Se le informa al profesional y queda en la bitácora.",
                    key=f"verif_reason_{pid}",
                )
                c1, c2 = st.columns(2)
                with c1:
                    approve = st.form_submit_button(
                        "✓ Aprobar verificación",
                        type="primary",
                        use_container_width=True,
                        key=f"admin_approve_{pid}",
                    )
                with c2:
                    reject = st.form_submit_button(
                        "✕ Rechazar verificación",
                        use_container_width=True,
                        key=f"admin_reject_{pid}",
                    )

            if approve or reject:
                ok, error = decide_verification(user["id"], pid, bool(approve), reason)

                if not ok:
                    st.error(error)
                else:
                    flash(
                        "Profesional aprobado." if approve else "Profesional rechazado.",
                        "success" if approve else "warning",
                    )
                    st.rerun()


def _open_document(admin_id, document_id):
    # Callback: descifra y registra en la bitácora quién abrió el documento (una vez por apertura).
    data, error = read_verification_document(document_id, admin_id, log=True)

    if error:
        flash(error, "error")
    else:
        st.session_state[f"_doc_open_{document_id}"] = True


def _close_document(document_id):
    st.session_state.pop(f"_doc_open_{document_id}", None)


def _document_row(user, doc):
    """Documento de verificación: se descifra solo cuando el administrador lo abre."""
    row = st.columns([4, 1])
    row[0].caption(
        f"📄 {doc['document_type']} — {doc['original_name']} · {doc['uploaded_at']}"
        + ("" if doc["encrypted"] else " · ⚠️ sin cifrar")
    )

    if not st.session_state.get(f"_doc_open_{doc['id']}"):
        row[1].button(
            "🔓 Ver documento",
            key=f"view_doc_{doc['id']}",
            on_click=_open_document,
            args=(user["id"], doc["id"]),
        )
        return

    data, error = read_verification_document(doc["id"], user["id"])

    if error:
        row[1].caption(error)
        return

    row[1].button("Ocultar", key=f"hide_doc_{doc['id']}", on_click=_close_document, args=(doc["id"],))

    if Path(doc["original_name"]).suffix.lower() in (".png", ".jpg", ".jpeg"):
        try:
            st.image(data, caption=doc["original_name"])
        except Exception:
            # Un archivo con firma válida pero dañado no debe botar la pantalla
            st.caption("No se puede mostrar la vista previa de esta imagen; descárgala para revisarla.")

    st.download_button(
        "Descargar",
        data=data,
        file_name=doc["original_name"],
        key=f"download_doc_{doc['id']}",
    )


def _verification_thread_admin(user, professional):
    """Hilo de mensajes con el profesional sobre su verificación."""
    pid = professional["id"]
    unread = professional["unread"]
    label = f"💬 Mensajes de verificación ({professional['messages']})" + (
        f" · 🔴 {unread} sin leer" if unread else ""
    )

    with st.expander(label, expanded=bool(unread)):
        messages = get_verification_messages(pid)

        if not messages:
            st.caption("Todavía no hay mensajes con este profesional.")

        for message in messages:
            thread_message(
                "Equipo Overol" if message["from_admin"] else professional["name"],
                message["created_at"],
                message["body"],
                message["from_admin"],
            )

        with st.form(f"verif_reply_form_{pid}", clear_on_submit=True):
            body = st.text_area(
                "Escribir al profesional",
                max_chars=MAX_TEXTO,
                key=f"verif_reply_text_{pid}",
            )
            sent = st.form_submit_button("Enviar mensaje", key=f"verif_reply_send_{pid}")

        if sent:
            ok, error = add_verification_message(pid, user["id"], body, from_admin=True)

            if not ok:
                st.error(error)
            else:
                audit(user["id"], "VERIFY_MESSAGE", "professionals", pid, "Mensaje al profesional")
                flash("Mensaje enviado al profesional.")
                st.rerun()

        if unread:
            st.button(
                "Marcar como leído",
                key=f"verif_read_{pid}",
                on_click=mark_verification_messages_read,
                args=(pid,),
            )


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

            # Motivo obligatorio: queda en la bitácora y se informa al usuario
            with st.expander(f"{action_label} cuenta"):
                with st.form(f"user_status_form_{account['id']}", clear_on_submit=True):
                    reason = st.text_area(
                        f"Motivo para {action_label.lower()} la cuenta",
                        max_chars=MAX_TEXTO,
                        placeholder="Se registra en la bitácora y se le muestra al usuario.",
                        key=f"user_reason_{account['id']}",
                    )
                    sent = st.form_submit_button(
                        action_label,
                        type="primary",
                        key=f"toggle_user_{account['id']}",
                    )

                if sent:
                    ok, error = set_user_active(user["id"], account["id"], not account["active"], reason)

                    if not ok:
                        st.error(error)
                    else:
                        flash("Cuenta suspendida." if account["active"] else "Cuenta reactivada.")
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
    section("🛠️ Reclamos y mediación")

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


def _audit_reset_page():
    # Callback: al cambiar un filtro se vuelve a la primera página.
    st.session_state["audit_page"] = 1


def _audit_go(delta):
    st.session_state["audit_page"] = max(1, st.session_state.get("audit_page", 1) + delta)


def admin_audit(user):
    section("📜 Bitácora de auditoría")

    st.write(
        "Registro de las acciones relevantes realizadas dentro de la plataforma."
    )

    users, actions, first, last = get_audit_filters()

    if not first:
        st.info(
            "Todavía no existen registros de trazabilidad."
        )
        return

    user_options = {"Todos": None, "Sistema (acciones automáticas)": AUDIT_SYSTEM}
    for account in users:
        label = f"{account['name']} · {ROLES.get(account['role'], account['role'])} · #{account['id']}"
        user_options[label] = account["id"]

    first_day = datetime.strptime(first[:10], "%Y-%m-%d").date()
    last_day = max(datetime.strptime(last[:10], "%Y-%m-%d").date(), date.today())

    c1, c2, c3 = st.columns(3)

    with c1:
        who = st.selectbox("Usuario", list(user_options), key="audit_user", on_change=_audit_reset_page)

    with c2:
        action = st.selectbox(
            "Tipo de acción", ["Todas", *actions], key="audit_action", on_change=_audit_reset_page
        )

    with c3:
        dates = st.date_input(
            "Rango de fechas",
            value=(first_day, last_day),
            min_value=first_day,
            max_value=last_day,
            format="DD/MM/YYYY",
            key="audit_dates",
            on_change=_audit_reset_page,
        )

    # Mientras se elige el rango, el calendario entrega solo la fecha inicial
    date_from = dates[0] if len(dates) > 0 else None
    date_to = dates[1] if len(dates) > 1 else None
    filters = (user_options[who], None if action == "Todas" else action, date_from, date_to)

    page = st.session_state.get("audit_page", 1)
    logs, total = get_audit_log(*filters, limit=AUDIT_PAGE_SIZE, offset=(page - 1) * AUDIT_PAGE_SIZE)
    pages = max(1, ceil(total / AUDIT_PAGE_SIZE))

    if page > pages:
        page = st.session_state["audit_page"] = pages
        logs, total = get_audit_log(*filters, limit=AUDIT_PAGE_SIZE, offset=(page - 1) * AUDIT_PAGE_SIZE)

    st.caption(f"{total} registros · página {page} de {pages}")

    if not logs:
        st.info("No hay registros con esos filtros.")
        return

    for log in logs:
        target = f" #{log['entity_id']}" if log["entity_id"] else ""
        who_name = log["user_name"] or "Sistema"
        role = ROLES.get(log["user_role"], log["user_role"]) if log["user_role"] else "Automático"
        detail = f'<div class="audit-detail">{escape(log["details"])}</div>' if log["details"] else ""

        with st.container(border=True):
            st.markdown(
                "".join(
                    line.strip()
                    for line in f"""
                    <div class="audit-entry">
                        <div><b>{escape(log["created_at"])}</b> · {escape(log["action"])} · {escape(log["entity"])}{target}</div>
                        <div class="who">Usuario: {escape(who_name)} · Rol: {escape(role)}</div>
                        {detail}
                    </div>
                    """.splitlines()
                ),
                unsafe_allow_html=True,
            )

    p1, _, p3 = st.columns([1, 2, 1])

    with p1:
        st.button(
            "← Más recientes",
            key="audit_prev",
            disabled=page <= 1,
            on_click=_audit_go,
            args=(-1,),
            use_container_width=True,
        )

    with p3:
        st.button(
            "Más antiguos →",
            key="audit_next",
            disabled=page >= pages,
            on_click=_audit_go,
            args=(1,),
            use_container_width=True,
        )


def _set_ticket_status(admin_id, request_id, user_id, status):
    # Callback: cambia el estado del ticket antes de redibujar la bandeja.
    if set_support_ticket_status(request_id, user_id, status):
        audit(admin_id, "SUPPORT_TICKET_STATUS", "requests", request_id,
              f"Ticket del usuario {user_id}: {status}")
        flash(f"Ticket marcado como {status.lower()}." if status == "Resuelto" else "Ticket reabierto.")


def admin_support(user):
    """Bandeja de tickets de soporte que clientes y profesionales abren sobre sus solicitudes."""
    section("💬 Tickets de soporte")

    threads = get_support_inbox()

    if not threads:
        empty_state(
            "💬",
            "No hay tickets de soporte",
            "Aquí aparecerán los tickets que clientes y profesionales abran sobre sus solicitudes.",
        )
        return

    open_total = sum(1 for t in threads if t["ticket_status"] == "Abierto")
    unread_total = sum(t["unread"] or 0 for t in threads)
    st.caption(
        f"{open_total} abiertos · {len(threads) - open_total} resueltos · "
        f"{unread_total} mensajes sin leer"
    )

    status_filter = st.radio(
        "Mostrar",
        ["Abiertos", "Resueltos", "Todos"],
        horizontal=True,
        key="support_filter",
    )
    wanted = {"Abiertos": "Abierto", "Resueltos": "Resuelto"}.get(status_filter)
    threads = [t for t in threads if wanted is None or t["ticket_status"] == wanted]

    if not threads:
        st.info(f"No hay tickets {status_filter.lower()}.")
        return

    for thread in threads:
        rid, uid = thread["request_id"], thread["user_id"]
        unread = thread["unread"] or 0

        label = (
            f"Ticket #{thread['ticket_id']} · {thread['subject']} · {thread['ticket_status']}"
            f" · Solicitud #{rid} · {thread['user_name']} ({ROLES.get(thread['user_role'], thread['user_role'])})"
            f" · {thread['trade'] or 'Servicio'} · {thread['request_status']}"
            + (f" · 🔴 {unread} sin leer" if unread else "")
        )

        with st.expander(label, expanded=bool(unread)):
            st.markdown(f"**Asunto:** {escape(thread['subject'] or '')}", unsafe_allow_html=True)
            status_badge(thread["ticket_status"])
            for message in get_support_thread(rid, uid):
                who = "Soporte Overol" if message["from_admin"] else thread["user_name"]
                css = "support-admin" if message["from_admin"] else "support-user"
                st.markdown(
                    "".join(
                        line.strip()
                        for line in f"""
                        <div class="support-msg {css}">
                            <div class="who">{escape(who)} · {escape(message["created_at"])}</div>
                            <div>{escape(message["body"])}</div>
                        </div>
                        """.splitlines()
                    ),
                    unsafe_allow_html=True,
                )

            with st.form(f"support_reply_form_{rid}_{uid}", clear_on_submit=True):
                body = st.text_area(
                    "Responder",
                    max_chars=MAX_TEXTO,
                    key=f"support_reply_text_{rid}_{uid}",
                )
                sent = st.form_submit_button(
                    "Enviar respuesta",
                    type="primary",
                    key=f"support_reply_send_{rid}_{uid}",
                )

            if sent:
                ok, error = add_support_message(rid, uid, body, from_admin=True)

                if not ok:
                    st.error(error)
                else:
                    mark_support_thread_read(rid, uid)
                    audit(user["id"], "SUPPORT_REPLY", "requests", rid,
                          f"Respuesta de soporte al usuario {uid}")
                    flash("Respuesta enviada.")
                    st.rerun()

            if unread and st.button("Marcar como leído", key=f"support_read_{rid}_{uid}"):
                mark_support_thread_read(rid, uid)
                st.rerun()

            if thread["ticket_status"] == "Abierto":
                st.button(
                    "✓ Marcar como resuelto",
                    key=f"support_resolve_{rid}_{uid}",
                    on_click=_set_ticket_status,
                    args=(user["id"], rid, uid, "Resuelto"),
                )
            else:
                st.button(
                    "Reabrir ticket",
                    key=f"support_reopen_{rid}_{uid}",
                    on_click=_set_ticket_status,
                    args=(user["id"], rid, uid, "Abierto"),
                )
