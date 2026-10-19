"""Vistas del rol Profesional (Historias 014 a 025)."""

import re
import secrets
import sqlite3
from pathlib import Path

import streamlit as st

from core.constants import (
    COMUNAS,
    DIAS_SEMANA,
    ESPECIALIDADES_POR_OFICIO,
    HORAS,
    HORAS_VENCIMIENTO,
    MAX_TEXTO,
    MOTIVOS_RECHAZO,
    OFICIOS,
    UPLOAD_DIR,
)
from core.database import (
    add_trade,
    audit,
    cancel_request_by_professional,
    change_request_status,
    confirm_request_completion,
    deactivate_trade,
    get_claims_for_professional,
    get_client_rating_for_request,
    get_connection,
    get_contact_info,
    get_professional_by_user,
    get_professional_rating,
    get_requests_for_professional,
    get_trade_ratings,
    get_trades,
    get_verification_documents,
    now_str,
    reject_request,
    request_expires_at,
    update_trade,
)
from ui.components import (
    contact_box,
    empty_state,
    flash,
    hero,
    section,
    security_note,
    stars,
    status_badge,
    support_box,
)
from views.about import about_page
from ui.profile import profile_header, profile_reviews, profile_sections
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
            "ℹ️ Quiénes somos",
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

    elif menu == "ℹ️ Quiénes somos":
        about_page()


def professional_requests(user, professional):
    """Historias 020, 021, 022, 023 y 024."""
    section("📋 Solicitudes recibidas")

    requests = get_requests_for_professional(professional["id"])

    if not requests:
        empty_state(
            "📋",
            "Aún no tienes solicitudes",
            "Completa tu perfil y tu cobertura para que los clientes te encuentren.",
        )
        return

    groups = {
        "Pendientes": ["Pendiente"],
        "Aceptadas": ["Aceptada"],
        "Finalizadas": ["Finalizada"],
        "Rechazadas / Canceladas / Vencidas": ["Rechazada", "Cancelada", "Vencida"],
    }

    tabs = st.tabs(
        [
            f"{name} ({sum(1 for r in requests if r['status'] in states)})"
            for name, states in groups.items()
        ]
    )

    for tab, (name, states) in zip(tabs, groups.items()):
        with tab:
            rows = [r for r in requests if r["status"] in states]

            if not rows:
                st.caption("No hay solicitudes en esta categoría.")

            for request in rows:
                _request_card(user, professional, request)


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
    """Mi perfil: vista tipo LinkedIn arriba y, debajo, la edición en pestañas."""
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
            "verificación (en «Editar mi perfil → Verificación»)."
        )

    st.caption("Así ven tu perfil los clientes registrados:")

    profile_header(professional, anonymous=False)

    tab_view, tab_about, tab_trades, tab_verification = st.tabs(
        ["👁️ Mi perfil", "📝 Presentación", "🛠️ Oficios", "🪪 Verificación"]
    )

    with tab_view:
        profile_sections(professional, owner=True)
        profile_reviews(professional["id"])

    with tab_about:
        _about_form(user, professional)

    with tab_trades:
        _trades_manager(user, professional)

    with tab_verification:
        professional_verification_upload(user)

    security_note(
        "El RUT, el domicilio y los documentos de identidad son información sensible. "
        "No se muestran públicamente."
    )


def professional_coverage(user, professional):
    """Historia 019: comunas, días disponibles, horas disponibles y tarifa de visita."""
    section("📍 Cobertura, días, horario y tarifa")

    current_coverage = [
        x.strip()
        for x in professional["coverage"].split(",")
        if x.strip()
    ]
    saved_days = [d for d in (professional["work_days"] or "").split(",") if d in DIAS_SEMANA]
    saved_start = professional["work_start"] or "09:00"
    saved_end = professional["work_end"] or "18:00"

    st.markdown("#### 📍 Comunas donde trabajas")
    coverage = st.multiselect(
        "Comunas donde realizas servicios",
        COMUNAS,
        default=current_coverage,
    )

    availability = st.toggle(
        "Disponible para recibir solicitudes",
        value=bool(professional["availability"]),
    )

    st.markdown("#### 📅 Días disponibles para trabajar")
    days = st.multiselect(
        "Días de la semana en que trabajas",
        DIAS_SEMANA,
        default=saved_days,
        help="Los clientes solo podrán pedirte visitas en estos días.",
    )

    st.markdown("#### 🕘 Horas disponibles")
    h1, h2 = st.columns(2)
    start = h1.selectbox(
        "Desde", HORAS,
        index=HORAS.index(saved_start) if saved_start in HORAS else 3,
    )
    end = h2.selectbox(
        "Hasta", HORAS,
        index=HORAS.index(saved_end) if saved_end in HORAS else 12,
    )

    st.markdown("#### 💰 Tarifa")
    fee = st.number_input(
        "Monto de la visita (CLP)",
        min_value=0,
        max_value=500000,
        step=1000,
        value=_fee_to_number(professional["visit_fee"]),
        help="Déjalo en 0 si prefieres informarlo directamente al cliente.",
    )

    if st.button(
        "Guardar cobertura, horario y tarifa",
        use_container_width=True,
        type="primary",
    ):
        if not days:
            st.error("Selecciona al menos un día en que trabajas.")
        elif end <= start:
            st.error("La hora de término debe ser posterior a la de inicio.")
        else:
            days = [d for d in DIAS_SEMANA if d in days]
            schedule = f"{', '.join(days)} · {start}–{end}"
            fee_text = f"${fee:,}".replace(",", ".") if fee else ""

            conn = get_connection()
            conn.execute(
                """
                UPDATE professionals
                SET coverage = ?, availability = ?, schedule = ?, visit_fee = ?,
                    work_days = ?, work_start = ?, work_end = ?
                WHERE id = ?
                """,
                (
                    ",".join(coverage),
                    1 if availability else 0,
                    schedule,
                    fee_text,
                    ",".join(days),
                    start,
                    end,
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
                "Actualización de cobertura, días, horario y tarifa",
            )
            flash("Cobertura, días, horario y tarifa actualizados. Ya se reflejan en tu perfil.")
            st.rerun()

    st.info(
        "Los clientes podrán encontrar tu perfil cuando la comuna "
        "seleccionada esté dentro de tu cobertura y tengas la disponibilidad activa. "
        "Solo podrán pedirte visitas en los días y horas que indicaste."
    )


def professional_reputation(professional):
    """Historia 025: valoración independiente por oficio."""
    section("⭐ Reputación por oficio")

    ratings_by_trade = get_trade_ratings(professional["id"])
    active = [r for r in ratings_by_trade if r["trade"]["active"]]
    inactive = [r for r in ratings_by_trade if not r["trade"]["active"]]

    cols = st.columns(min(3, max(1, len(active))))

    for i, item in enumerate(active):
        with cols[i % len(cols)]:
            st.metric(
                item["trade"]["trade"],
                f"★ {item['average']}" if item["total"] else "Sin datos",
                f"{item['total']} evaluaciones",
                delta_color="off",
            )

    if inactive:
        st.markdown("#### Oficios inactivos")
        st.caption("Su valoración histórica se conserva como información inactiva.")
        for item in inactive:
            st.write(
                f"• **{item['trade']['trade']}** — "
                f"{'★ ' + str(item['average']) if item['total'] else 'Sin datos'} "
                f"({item['total']} evaluaciones)"
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
        empty_state("⭐", "Todavía no tienes evaluaciones", "Aparecerán aquí cuando un cliente evalúe un servicio finalizado.")
        return

    for rating in ratings:
        average_rating = round(
            (rating["quality"] + rating["punctuality"] + rating["treatment"]) / 3,
            1,
        )

        with st.container(border=True):
            st.markdown(f"### {stars(average_rating)} {average_rating} · {rating['trade'] or 'Servicio'}")
            st.write(f"**Calidad:** {rating['quality']}/5 · **Puntualidad:** {rating['punctuality']}/5 · **Trato:** {rating['treatment']}/5")
            st.write(f"**Comentario:** {rating['comment'] or 'Sin comentario'}")
            st.caption("El historial de evaluaciones se conserva para trazabilidad.")


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


def _request_card(user, professional, request):
    rid = request["id"]

    with st.container(border=True):
        top = st.columns([4, 1])

        with top[0]:
            st.markdown(f"### Solicitud #{rid} · {request['client_name']}")

        with top[1]:
            status_badge(request["status"])

        d1, d2 = st.columns(2)

        with d1:
            st.write(f"**Oficio:** {request['trade'] or request['service']}")
            st.write(f"**Comuna:** {request['commune']} · **Zona:** {request['home_zone']}")

        with d2:
            st.write(
                f"**Fecha tentativa:** {request['tentative_date']} · "
                f"{request['tentative_time']}"
            )

        st.write(f"**Descripción:** {request['description']}")

        # ---------- Pendiente: aceptar o rechazar con motivo ----------
        if request["status"] == "Pendiente":
            expires = request_expires_at(request["created_at"])
            st.caption(
                f"⏳ Responde antes del {expires:%d-%m-%Y a las %H:%M}; "
                f"pasado ese plazo la solicitud vence. "
                "🔒 Los datos de contacto del cliente se habilitan al aceptar."
            )

            if st.button(
                "✓ Aceptar solicitud",
                type="primary",
                use_container_width=True,
                key=f"pro_accept_{rid}",
            ):
                _transition(user, professional, rid, "Aceptada",
                            ["Pendiente"], "Solicitud aceptada por profesional")

            with st.expander("✕ Rechazar solicitud"):
                reason = st.selectbox(
                    "Motivo del rechazo",
                    MOTIVOS_RECHAZO,
                    key=f"reject_reason_{rid}",
                )

                detail = ""
                if reason == "Otro":
                    detail = st.text_input(
                        "Explica el motivo",
                        key=f"reject_detail_{rid}",
                    )

                if st.button("Confirmar rechazo", key=f"pro_reject_{rid}"):
                    if reason == "Otro" and not detail.strip():
                        st.warning("Cuando eliges «Otro» debes explicar el motivo.")
                    elif reject_request(rid, professional["id"], reason, detail):
                        audit(user["id"], "UPDATE", "requests", rid,
                              f"Solicitud rechazada: {reason}")
                        flash(f"Solicitud #{rid} rechazada.", "warning")
                        st.rerun()
                    else:
                        flash("La solicitud ya había cambiado de estado.", "warning")
                        st.rerun()

        # ---------- Vencida / Cancelada ----------
        if request["status"] == "Vencida":
            st.info(
                f"Esta solicitud venció: no se respondió dentro de {HORAS_VENCIMIENTO} horas."
            )

        if request["status"] == "Cancelada":
            if request["cancelled_by"] == "profesional":
                st.caption(f"Cancelaste esta solicitud. Motivo: {request['cancel_reason']}")
            else:
                st.warning("El cliente canceló esta solicitud.")

        # ---------- Rechazada: motivo registrado ----------
        if request["status"] == "Rechazada":
            reason = request["reject_reason"] or "Sin motivo informado"
            detail = f" — {request['reject_detail']}" if request["reject_detail"] else ""
            st.caption(f"Motivo registrado: {reason}{detail}")

        # ---------- Contacto del cliente: solo tras aceptar ----------
        if request["status"] in ("Aceptada", "Finalizada"):
            contact_box(
                get_contact_info(request["client_id"]),
                "Datos de contacto del cliente",
            )

        # ---------- Aceptada: confirmar finalización (ambas partes) ----------
        if request["status"] == "Aceptada":
            if request["professional_confirmed"]:
                st.info(
                    "✓ Ya confirmaste la finalización. "
                    "Falta la confirmación del cliente."
                )
            else:
                if request["client_confirmed"]:
                    st.info(
                        "El cliente ya confirmó que el servicio terminó. "
                        "Falta tu confirmación."
                    )

                if st.button(
                    "Confirmar finalización del servicio",
                    type="primary",
                    key=f"pro_complete_{rid}",
                ):
                    outcome = confirm_request_completion(
                        rid, "professional", professional_id=professional["id"]
                    )

                    if outcome == "Finalizada":
                        audit(user["id"], "UPDATE", "requests", rid,
                              "Servicio finalizado por confirmación de ambas partes")
                        flash("Servicio finalizado. Ya puedes calificar al cliente.")
                    elif outcome == "Esperando":
                        audit(user["id"], "UPDATE", "requests", rid,
                              "Profesional confirmó la finalización")
                        flash("Confirmación registrada. Falta la del cliente.", "info")
                    else:
                        flash("La solicitud ya había cambiado de estado.", "warning")
                    st.rerun()

        # ---------- Aceptada: cancelar indicando el motivo ----------
        if request["status"] == "Aceptada":
            with st.expander("✕ Cancelar solicitud"):
                st.warning(
                    "Al cancelar, el cliente verá el motivo que escribas. "
                    "Esta acción no se puede deshacer."
                )
                reason = st.text_area(
                    "Motivo de la cancelación",
                    max_chars=MAX_TEXTO,
                    placeholder="Explica por qué cancelas esta solicitud.",
                    key=f"pro_cancel_reason_{rid}",
                )

                if st.button("Confirmar cancelación", key=f"pro_cancel_{rid}"):
                    ok, message = cancel_request_by_professional(
                        rid, professional["id"], reason
                    )

                    if ok:
                        audit(user["id"], "UPDATE", "requests", rid,
                              "Solicitud cancelada por profesional")
                        flash(f"Solicitud #{rid} cancelada.", "warning")
                        st.rerun()
                    else:
                        st.error(message)

        # ---------- Finalizada: calificar al cliente ----------
        if request["status"] == "Finalizada":
            _client_rating_block(user, professional, request)

        # ---------- Mensajes a soporte sobre esta solicitud ----------
        support_box(user, rid, "profesional")


def _client_rating_block(user, professional, request):
    """Historia 024: el profesional califica al cliente tras finalizar el servicio."""
    rid = request["id"]
    existing = get_client_rating_for_request(rid)

    if existing:
        st.success(f"✓ Calificaste a este cliente: {'★' * existing['score']}{'☆' * (5 - existing['score'])}")
        return

    st.markdown("#### ⭐ Calificar al cliente")

    score = st.slider("Puntaje", 1, 5, 5, key=f"client_score_{rid}")
    comment = st.text_input("Comentario (opcional)", key=f"client_comment_{rid}")

    if st.button("Guardar calificación", type="primary", key=f"save_client_rating_{rid}"):
        conn = get_connection()

        try:
            cur = conn.execute(
                """
                INSERT INTO client_ratings
                (request_id, professional_id, client_id, score, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (rid, professional["id"], request["client_id"], score,
                 comment.strip(), now_str()),
            )
            rating_id = cur.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            flash("Este cliente ya fue calificado en este servicio.", "warning")
            st.rerun()
        finally:
            conn.close()

        audit(user["id"], "CREATE", "client_ratings", rating_id,
              f"Calificación al cliente de la solicitud {rid}")
        flash("Calificación al cliente registrada.")
        st.rerun()


def _years_or_none(value):
    return int(value) if value else None


def _trades_manager(user, professional):
    pid = professional["id"]

    section("🛠️ Mis oficios")
    st.caption(
        "Cada oficio tiene su propia experiencia, especialidades, certificaciones "
        "y valoración. Los datos de experiencia y especialidades son opcionales."
    )

    active = get_trades(pid)

    for trade in active:
        tid = trade["id"]
        specialty_catalog = ESPECIALIDADES_POR_OFICIO.get(trade["trade"], [])
        current = [x for x in (trade["specialties"] or "").split(",") if x in specialty_catalog]

        with st.expander(f"🔧 {trade['trade']}"):
            with st.form(f"trade_form_{tid}"):
                years = st.number_input(
                    "Años de experiencia (0 = no informar)",
                    min_value=0,
                    max_value=60,
                    step=1,
                    value=trade["years_experience"] or 0,
                )
                specialties = st.multiselect(
                    "Especialidades",
                    specialty_catalog,
                    default=current,
                )
                certifications = st.text_input(
                    "Certificaciones (opcional)",
                    value=trade["certifications"] or "",
                )
                saved = st.form_submit_button(
                    "Guardar oficio", type="primary", use_container_width=True
                )

            if saved:
                update_trade(tid, pid, _years_or_none(years), specialties, certifications)
                audit(user["id"], "UPDATE", "professional_trades", tid,
                      f"Oficio actualizado: {trade['trade']}")
                flash(f"Oficio «{trade['trade']}» actualizado.")
                st.rerun()

            # --- Eliminar con confirmación (no borra el historial de valoraciones) ---
            if st.session_state.get(f"confirm_del_{tid}"):
                st.warning(
                    f"¿Eliminar el oficio «{trade['trade']}»? Su historial de "
                    "valoraciones se conserva como información inactiva."
                )
                c1, c2 = st.columns(2)

                if c1.button("Sí, eliminar", type="primary", key=f"del_yes_{tid}"):
                    st.session_state.pop(f"confirm_del_{tid}", None)

                    if deactivate_trade(tid, pid):
                        audit(user["id"], "DELETE", "professional_trades", tid,
                              f"Oficio eliminado (desactivado): {trade['trade']}")
                        flash(f"Oficio «{trade['trade']}» eliminado.", "warning")
                    else:
                        flash("Debes mantener al menos un oficio activo.", "warning")
                    st.rerun()

                if c2.button("Cancelar", key=f"del_no_{tid}"):
                    st.session_state.pop(f"confirm_del_{tid}", None)
                    st.rerun()
            else:
                if st.button("🗑️ Eliminar oficio", key=f"del_{tid}"):
                    st.session_state[f"confirm_del_{tid}"] = True
                    st.rerun()

    # --- Agregar o reactivar un oficio ---
    all_trades = get_trades(pid, active_only=False)
    active_names = [t["trade"] for t in active]
    inactive = {t["trade"]: t for t in all_trades if not t["active"]}
    available = [o for o in OFICIOS if o not in active_names]

    if available:
        with st.expander("➕ Agregar un oficio"):
            new_trade = st.selectbox("Oficio", available, key="add_trade_select")

            if new_trade in inactive:
                total, _ = get_professional_rating(pid, new_trade)
                st.info(
                    f"Ya tuviste este oficio. Al agregarlo de nuevo se recupera "
                    f"su valoración histórica ({total} evaluaciones)."
                )

            years = st.number_input(
                "Años de experiencia (0 = no informar)",
                min_value=0, max_value=60, step=1,
                key=f"add_years_{new_trade}",
            )
            specialties = st.multiselect(
                "Especialidades (opcional)",
                ESPECIALIDADES_POR_OFICIO.get(new_trade, []),
                key=f"add_specs_{new_trade}",
            )
            certifications = st.text_input(
                "Certificaciones (opcional)",
                key=f"add_certs_{new_trade}",
            )

            if st.button("Agregar oficio", type="primary", key="add_trade_button"):
                result = add_trade(
                    pid, new_trade, _years_or_none(years), specialties, certifications
                )
                audit(user["id"], "CREATE", "professional_trades", pid,
                      f"Oficio {result}: {new_trade}")
                flash(f"Oficio «{new_trade}» {result}.")
                st.rerun()

    if inactive:
        st.caption(
            "Oficios inactivos (su valoración histórica se conserva): "
            + ", ".join(inactive)
        )


def _about_form(user, professional):
    """Presentación del profesional: se muestra en su tarjeta y en su perfil."""
    section("📝 Mi presentación")

    with st.form("about_form"):
        about = st.text_area(
            "Cuéntales a los clientes quién eres y cómo trabajas",
            value=professional["about"] or "",
            max_chars=300,
            placeholder="Ej: Gasfiter con 8 años de experiencia. Trabajo ordenado y con presupuesto claro.",
        )
        saved = st.form_submit_button("Guardar presentación", use_container_width=True)

    if saved:
        conn = get_connection()
        conn.execute(
            "UPDATE professionals SET about = ? WHERE id = ?",
            (about.strip(), professional["id"]),
        )
        conn.commit()
        conn.close()

        audit(user["id"], "UPDATE", "professionals", professional["id"],
              "Presentación del perfil actualizada")
        flash("Presentación actualizada.")
        st.rerun()
