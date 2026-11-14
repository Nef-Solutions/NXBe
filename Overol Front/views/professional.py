"""Vistas del rol Profesional (Historias 014 a 025)."""

import re
import secrets
from datetime import datetime
from pathlib import Path

import streamlit as st

from core.constants import (
    COMUNAS,
    DIAS_SEMANA,
    ESPECIALIDADES_POR_OFICIO,
    HORAS,
    MAX_TEXTO,
    MOTIVOS_RECHAZO,
    UPLOAD_DIR,
    pantallas_visibles,
)
from core import api_client, requests_api
from core.session import load_user
from core.security import encrypt_document
from core.database import (
    add_trade,
    audit,
    deactivate_trade,
    get_connection,
    get_professional_by_user,
    get_professional_rating,
    get_trade_ratings,
    get_trades,
    add_verification_message,
    get_verification_documents,
    get_verification_messages,
    now_str,
    update_trade,
)
from ui.components import (
    contact_box,
    empty_state,
    flash,
    hero,
    nav_bar,
    notifications_page,
    section,
    security_note,
    stars,
    status_badge,
    support_box,
    thread_message,
)
from views import payments
from views.about import about_page
from views.assistant import assistant_page
from views.shared import user_profile_page
from ui.profile import profile_header, profile_reviews, profile_sections

MAX_UPLOAD_MB = 5

# Primeros bytes (firma) válidos para cada extensión permitida
SIGNATURES = {
    ".pdf": b"%PDF",
    ".png": b"\x89PNG",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


def professional_dashboard(user):
    options = pantallas_visibles("profesional", [
        "📋 Solicitudes",
        "🔔 Notificaciones",
        "👤 Mi perfil",
        "📍 Cobertura",
        "💳 Suscripción",
        "🪪 Verificación",
        "🛠️ Reclamos",
        "🎓 Desarrollo profesional",
        "🤖 Asistente",
        "ℹ️ Quiénes somos",
    ])

    # Desarrollo profesional aún usa el perfil profesional de SQLite; mientras esté
    # oculta (PANTALLAS_PENDIENTES_API) no se consulta la base.
    professional = None
    if "🎓 Desarrollo profesional" in options:
        professional = get_professional_by_user(user["id"])

    badges = {}
    if "🔔 Notificaciones" in options:
        badges["🔔 Notificaciones"] = api_client.unread_notifications()
    if "🛠️ Reclamos" in options:
        try:
            badges["🛠️ Reclamos"] = sum(1 for c in requests_api.list_claims() if c["raw_status"] == "OPEN")
        except api_client.ApiError:
            pass

    menu = nav_bar("professional_navigation", options, badges=badges)

    hero(
        "Panel del profesional",
        "Gestiona solicitudes, perfil, disponibilidad, cobertura, reputación "
        "y capacitación profesional.",
    )

    if menu == "📋 Solicitudes":
        professional_requests(user)

    elif menu == "🔔 Notificaciones":
        notifications_page(user)

    elif menu == "👤 Mi perfil":
        # Etapa B: datos personales y presentación desde /auth/me/.
        # Etapa F: vuelve professional_profile (vista pública, oficios y verificación).
        _verification_banner(user)
        user_profile_page(user)

    elif menu == "📍 Cobertura":
        professional_coverage(user)

    elif menu == "💳 Suscripción":
        professional_subscription(user)

    elif menu == "🪪 Verificación":
        professional_verification(user)

    elif menu == "🤖 Asistente":
        assistant_page(user)

    elif menu == "🛠️ Reclamos":
        professional_claims(user)

    elif menu == "🎓 Desarrollo profesional":
        professional_training(user, professional)

    elif menu == "ℹ️ Quiénes somos":
        about_page()


def _verification_banner(user):
    """Estado de verificación según /auth/me/ (verification_status)."""
    status = user.get("verification_status")
    if status == "APPROVED":
        st.success("✓ Tu identidad está verificada. Apareces en las búsquedas de los clientes.")
    elif status == "REJECTED":
        st.error(
            "Tu verificación fue rechazada. Escríbele a Overol para revisar tu caso "
            "(el envío de documentos desde aquí estará disponible pronto)."
        )
    else:
        st.info(
            "⏳ Tu cuenta está pendiente de verificación. Un administrador de Overol "
            "revisará tus datos; cuando te aprueben, aparecerás en las búsquedas."
        )


def professional_requests(user):
    """Historias 020 a 023: solicitudes recibidas (GET /api/requests/)."""
    section("📋 Solicitudes recibidas")

    try:
        requests = requests_api.list_requests()
        tickets = api_client.list_tickets()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar tus solicitudes. {error}")
        return

    if not requests:
        empty_state(
            "📋",
            "Aún no tienes solicitudes",
            "Completa tu perfil y tu cobertura para que los clientes te encuentren.",
        )
        return

    groups = {
        "Pendientes": ["PENDING"],
        "Aceptadas": ["ACCEPTED", "PROFESSIONAL_FINISHED"],
        "Finalizadas": ["COMPLETED"],
        "Rechazadas / Canceladas / Vencidas": ["REJECTED", "CANCELLED", "EXPIRED", "FORCED_CLOSED"],
    }

    tabs = st.tabs(
        [
            f"{name} ({sum(1 for r in requests if r['raw_status'] in states)})"
            for name, states in groups.items()
        ]
    )

    for tab, (name, states) in zip(tabs, groups.items()):
        with tab:
            rows = [r for r in requests if r["raw_status"] in states]

            if not rows:
                st.caption("No hay solicitudes en esta categoría.")

            for request in rows:
                _request_card(user, request, [t for t in tickets if t.get("visit") == request["id"]])


def _pro_action(rid, name, success, reason=None, kind="success"):
    """Envía la acción al backend y recarga. Si la solicitud ya cambió (409), lo informa."""
    try:
        updated = requests_api.action(rid, name, reason)
    except api_client.ApiError as error:
        if error.status == 400:
            st.error(str(error))  # motivo inválido: se queda en el formulario
            return
        flash(str(error), "warning")
    else:
        if updated["raw_status"] == "COMPLETED":
            success = "Servicio finalizado por ambas partes."
        flash(success, kind)
    st.rerun()


def _request_card(user, request, tickets):
    rid = request["id"]
    raw = request["raw_status"]

    with st.container(border=True):
        top = st.columns([4, 1])

        with top[0]:
            st.markdown(f"### Solicitud #{rid} · {request['client_name']}")

        with top[1]:
            status_badge(request["status"])

        d1, d2 = st.columns(2)

        with d1:
            st.write(f"**Oficio:** {request['trade']} · {request['specialty']}")
            st.write(f"**Comuna:** {request['commune']}")

        with d2:
            st.write(f"**Fecha tentativa:** {request['date']} · {request['time']}")

        st.write(f"**Descripción:** {request['description']}")

        # ---------- Pendiente: aceptar o rechazar con motivo ----------
        if raw == "PENDING":
            st.caption(
                (f"⏳ Responde antes del {request['expires_at']}; pasado ese plazo la solicitud vence. "
                 if request["expires_at"] else "")
                + "🔒 Los datos de contacto del cliente se habilitan al aceptar."
            )

            if st.button("✓ Aceptar solicitud", type="primary", use_container_width=True, key=f"pro_accept_{rid}"):
                _pro_action(rid, "accept", f"Solicitud #{rid} aceptada.")

            with st.expander("✕ Rechazar solicitud"):
                reason = st.selectbox("Motivo del rechazo", MOTIVOS_RECHAZO, key=f"reject_reason_{rid}")

                detail = st.text_input(
                    "Explica el motivo" if reason == "Otro" else "Detalle (opcional)",
                    max_chars=MAX_TEXTO - 60,
                    key=f"reject_detail_{rid}",
                )

                if st.button("Confirmar rechazo", key=f"pro_reject_{rid}"):
                    if reason == "Otro" and not detail.strip():
                        st.warning("Cuando eliges «Otro» debes explicar el motivo.")
                    else:
                        text = reason if not detail.strip() else f"{reason} — {detail.strip()}"
                        _pro_action(rid, "reject", f"Solicitud #{rid} rechazada.", text[:MAX_TEXTO], "warning")

        if raw == "EXPIRED":
            st.info("Esta solicitud venció: no se respondió dentro del plazo.")

        if raw == "CANCELLED":
            if request["cancelled_by"] == "PROFESSIONAL":
                st.caption(f"Cancelaste esta solicitud. Motivo: {request['cancel_reason']}")
            else:
                st.warning("El cliente canceló esta solicitud.")

        if raw == "REJECTED":
            st.caption(f"Motivo registrado: {request['rejection_reason'] or 'Sin motivo informado'}")

        if raw == "FORCED_CLOSED":
            st.info("El equipo de Overol cerró esta solicitud.")

        # ---------- Contacto del cliente: el backend lo entrega solo tras aceptar ----------
        if request["contact"]:
            contact_box({"name": request["client_name"], **request["contact"]}, "Datos de contacto del cliente")

        # ---------- Confirmar finalización (ambas partes) ----------
        if raw == "PROFESSIONAL_FINISHED":
            st.info("✓ Ya confirmaste la finalización. Falta la confirmación del cliente.")

        if raw == "ACCEPTED":
            if request["client_confirmed"]:
                st.info("El cliente ya confirmó que el servicio terminó. Falta tu confirmación.")

            if st.button("Confirmar finalización del servicio", type="primary", key=f"pro_complete_{rid}"):
                _pro_action(rid, "finish", "Confirmación registrada. Falta la del cliente.")

            # ---------- Cancelar indicando el motivo ----------
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
                    if not reason.strip():
                        st.warning("Escribe el motivo de la cancelación.")
                    else:
                        _pro_action(rid, "cancel_professional", f"Solicitud #{rid} cancelada.", reason.strip(), "warning")

        # ---------- Finalizada: calificar al cliente ----------
        if raw == "COMPLETED":
            _client_rating_block(request)

        # ---------- Tickets de soporte sobre esta solicitud ----------
        support_box(user, rid, "profesional", tickets)


def _fee_to_number(value):
    """Tarifa como entero: acepta 15000, "15000", "15000.00" (backend) o "$15.000"."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        digits = re.sub(r"\D", "", str(value or ""))
        return int(digits) if digits else 0


def professional_profile(user, professional):
    """Mi perfil: vista tipo LinkedIn arriba y, debajo, la edición en pestañas."""
    status = professional["verification_status"]
    docs = get_verification_documents(professional["id"])

    # --- Estado de verificación ---
    if status == "Aprobado":
        st.success("✓ Tu identidad está verificada. Apareces en las búsquedas de los clientes.")
    elif status == "Rechazado":
        reason = professional["verification_reason"]
        st.error(
            "Tu verificación fue rechazada. Sube documentos actualizados "
            "para enviarla nuevamente a revisión."
            + (f" Motivo: {reason}" if reason else "")
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
        profile_reviews(professional)

    with tab_about:
        _about_form(user, professional)

    with tab_trades:
        _trades_manager(user, professional)

    with tab_verification:
        professional_verification_upload(user)
        _verification_messages(user, professional)

    security_note(
        "El RUT, el domicilio y los documentos de identidad son información sensible. "
        "No se muestran públicamente."
    )


def professional_coverage(user):
    """Historia 019: comunas, días y horas disponibles (GET/PATCH /api/professionals/me/
    availability/) y tarifa de visita (PATCH /api/auth/me/)."""
    section("📍 Cobertura, días, horario y tarifa")

    try:
        current = requests_api.get_availability()
    except api_client.ApiError as error:
        st.error(f"No se pudo cargar tu disponibilidad. {error}")
        return

    saved_start = current["work_start"] or "09:00"
    saved_end = current["work_end"] or "18:00"

    if not current["work_start"] or not current["work_days"]:
        st.warning("Todavía no configuras tus días y horario: los clientes no pueden pedirte visitas hasta que lo hagas.")

    st.markdown("#### 📍 Comunas donde trabajas")
    coverage = st.multiselect(
        "Comunas donde realizas servicios",
        list(dict.fromkeys(COMUNAS + current["coverage_communes"])),
        default=current["coverage_communes"],
        key="cov_communes",
    )

    availability = st.toggle(
        "Disponible para recibir solicitudes",
        value=current["is_available"],
        key="cov_available",
    )

    st.markdown("#### 📅 Días disponibles para trabajar")
    days = st.multiselect(
        "Días de la semana en que trabajas",
        DIAS_SEMANA,
        default=current["work_days"],
        help="Los clientes solo podrán pedirte visitas en estos días.",
        key="cov_days",
    )

    st.markdown("#### 🕘 Horas disponibles")
    h1, h2 = st.columns(2)
    start = h1.selectbox("Desde", HORAS, index=HORAS.index(saved_start) if saved_start in HORAS else 3, key="cov_start")
    end = h2.selectbox("Hasta", HORAS, index=HORAS.index(saved_end) if saved_end in HORAS else 12, key="cov_end")

    st.markdown("#### 💰 Tarifa")
    fee = st.number_input(
        "Monto de la visita (CLP)",
        min_value=0,
        max_value=500000,
        step=1000,
        value=_fee_to_number(user.get("visit_fee")),
        help="Déjalo en 0 si prefieres informarlo directamente al cliente.",
        key="cov_fee",
    )

    if st.button(
        "Guardar cobertura, horario y tarifa",
        use_container_width=True,
        type="primary",
        key="save_coverage",
    ):
        if not coverage:
            st.error("Selecciona al menos una comuna donde trabajas.")
        elif not days:
            st.error("Selecciona al menos un día en que trabajas.")
        elif end <= start:
            st.error("La hora de término debe ser posterior a la de inicio.")
        else:
            days = [d for d in DIAS_SEMANA if d in days]
            try:
                api_client.update_availability(days, start, end, availability, coverage)
                if int(fee) != _fee_to_number(user.get("visit_fee")):
                    api_client.update_me(visit_fee=int(fee))
                    load_user()
            except api_client.ApiError as error:
                st.error(f"No se pudo guardar tu disponibilidad en el servidor. {error}")
                return

            flash("Cobertura, días, horario y tarifa actualizados. Ya se reflejan en tu perfil.")
            st.rerun()

    st.info(
        "Los clientes podrán encontrar tu perfil cuando la comuna "
        "seleccionada esté dentro de tu cobertura y tengas la disponibilidad activa. "
        "Solo podrán pedirte visitas en los días y horas que indicaste."
    )


def _fecha_hora(value):
    """Fecha ISO del backend como dd-mm-aaaa HH:MM (hora local)."""
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    return (parsed.astimezone() if parsed.tzinfo else parsed).strftime("%d-%m-%Y %H:%M")


def professional_subscription(user):
    """Suscripción mensual (GET/POST /api/payments/professional-subscription/...) con Webpay."""
    section("💳 Suscripción")

    back = payments.pop_return("subscription")

    try:
        data = api_client.get_subscription()
    except api_client.ApiError as error:
        st.error(f"No se pudo consultar tu suscripción. {error}")
        return

    status = data.get("status")
    latest = data.get("latest_payment") or {}

    # ---------- Vuelta de Webpay: se muestra el estado REAL, no el parámetro de la URL ----------
    if back:
        payment = payments.payment_status_text(latest.get("status"))
        if status == "ACTIVE" and latest.get("status") == "AUTHORIZED":
            st.success(f"✅ Pago confirmado. Tu suscripción está vigente hasta el {_fecha_hora(data.get('expires_at'))}.")
        elif latest.get("status") == "PENDING":
            st.info("Tu pago todavía figura pendiente en Overol. Revisa de nuevo en unos minutos.")
        else:
            st.error(f"El pago no se completó (estado: {payment}). Tu suscripción no cambió y no se hizo ningún cargo.")
        st.session_state.pop(payments.PENDING_KEY, None)

    plan = data.get("plan") or {}
    amount = _fee_to_number(data.get("amount"))
    label = {"ACTIVE": "Vigente", "EXPIRED": "Vencida", "INACTIVE": "Sin suscripción"}.get(status, status or "—")

    c1, c2, c3 = st.columns(3)
    c1.metric("Estado", label)
    c2.metric("Vigente hasta", _fecha_hora(data.get("expires_at"))[:10] or "—")
    c3.metric("Monto", f"${amount:,}".replace(",", ".") if amount else "—")
    st.caption(
        f"Plan: {plan.get('name', 'Suscripción profesional')} · "
        f"{plan.get('duration_months', 1)} mes(es). La renovación es manual: no hay cobro automático."
        + (f" Último pago: {payments.payment_status_text(latest.get('status'))}." if latest else "")
    )

    if status != "ACTIVE":
        st.warning(
            "Sin una suscripción vigente **no apareces en el catálogo** y los clientes no pueden "
            "enviarte solicitudes."
        )

    pending = st.session_state.get(payments.PENDING_KEY)
    if pending and pending.get("key") == "subscription":
        st.info("Tu pago está listo. Continúa en Webpay:")
        payments.webpay_form(pending["url"], pending["token"], "subscription")
        if st.button("Cancelar y volver", key="sub_cancel"):
            st.session_state.pop(payments.PENDING_KEY, None)
            st.rerun()
        return

    if st.button(
        "Renovar con Webpay" if status == "ACTIVE" else "Pagar con Webpay",
        type="primary",
        use_container_width=True,
        key="sub_pay",
    ):
        try:
            started = api_client.start_subscription_payment()
        except api_client.ApiError as error:
            st.error(f"No se pudo iniciar el pago. {error}")
            return
        st.session_state[payments.PENDING_KEY] = {"url": started["url"], "token": started["token"], "key": "subscription"}
        st.rerun()

    if status == "ACTIVE":
        st.caption("Si renuevas antes de que venza, el mes nuevo se suma a tu fecha de vencimiento.")


def professional_verification(user):
    """Cédula (GET/POST /api/auth/verification/documents/) y mensajes con Overol."""
    section("🪪 Verificación de identidad")
    _verification_banner(user)

    try:
        info = api_client.get_verification_documents()
    except api_client.ApiError as error:
        st.error(f"No se pudo consultar tu verificación. {error}")
        return

    docs = info.get("documents") or {}
    st.markdown(
        f"**Frente de la cédula:** {'✅ cargado' if docs.get('front_uploaded') else '⏳ falta'}  \n"
        f"**Reverso de la cédula:** {'✅ cargado' if docs.get('back_uploaded') else '⏳ falta'}"
    )
    st.caption(
        "Sube ambos lados en JPG o PNG (hasta 5 MB) o PDF (hasta 10 MB). Un administrador los revisa; "
        "al subir un documento nuevo, tu verificación vuelve a quedar en revisión. Los archivos son privados."
    )

    f1, f2 = st.columns(2)
    front = f1.file_uploader("Frente de la cédula", type=["jpg", "jpeg", "png", "pdf"], key="ver_front")
    back = f2.file_uploader("Reverso de la cédula", type=["jpg", "jpeg", "png", "pdf"], key="ver_back")

    if st.button("Enviar documentos", type="primary", key="ver_send"):
        files, errors = {}, []
        for field, upload in (("id_card_front", front), ("id_card_back", back)):
            if upload is None:
                continue
            problem = _document_problem(upload)
            if problem:
                errors.append(problem)
            else:
                files[field] = (upload.name, upload.getvalue(), upload.type or "application/octet-stream")
        if errors:
            for problem in errors:
                st.error(problem)
        elif not files:
            st.warning("Elige al menos un archivo.")
        else:
            try:
                api_client.upload_verification_documents(files)
                load_user()
            except api_client.ApiError as error:
                st.error(f"No se pudieron enviar los documentos. {error}")
            else:
                flash("Documentos enviados. Quedan en revisión del equipo de Overol.")
                st.rerun()

    _verification_thread()


def _document_problem(upload):
    """Valida extensión, tamaño y firma del archivo antes de enviarlo (el backend también valida)."""
    ext = Path(upload.name).suffix.lower()
    data = upload.getvalue()
    limit = 10 if ext == ".pdf" else 5
    if ext not in SIGNATURES:
        return f"«{upload.name}»: debe ser JPG, PNG o PDF."
    if len(data) > limit * 1024 * 1024:
        return f"«{upload.name}» supera {limit} MB."
    if not data.startswith(SIGNATURES[ext]):
        return f"«{upload.name}» no parece un {ext[1:].upper()} válido."
    return None


def _verification_thread():
    """Mensajes del profesional al equipo de verificación (GET/POST /auth/verification/messages/)."""
    st.markdown("#### 💬 Mensajes con el equipo de verificación")
    try:
        messages = api_client.get_verification_messages()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar tus mensajes. {error}")
        return

    if not messages:
        st.caption("Aún no hay mensajes.")
    for item in messages:
        with st.container(border=True):
            st.markdown(f"**Tú** · {_fecha_hora(item.get('created_at'))}")
            st.write(item.get("message", ""))
            if item.get("admin_response"):
                st.markdown(f"**Overol** · {_fecha_hora(item.get('resolved_at'))}")
                st.write(item["admin_response"])

    text = st.text_area("Escribe al equipo de Overol", max_chars=MAX_TEXTO, key="ver_message")
    if st.button("Enviar mensaje", key="ver_message_send"):
        if not text.strip():
            st.warning("Escribe un mensaje.")
            return
        try:
            api_client.send_verification_message(text)
        except api_client.ApiError as error:
            st.error(f"No se pudo enviar el mensaje. {error}")
            return
        flash("Mensaje enviado al equipo de verificación.")
        st.rerun()


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


def professional_claims(user):
    """Reclamos de posventa de sus servicios (GET /api/claims/): responder o pedir mediación."""
    section("🛠️ Reclamos de posventa")

    try:
        claims = requests_api.list_claims()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar los reclamos. {error}")
        return

    if not claims:
        empty_state("🛠️", "No tienes reclamos registrados", "Aquí aparecerán los reclamos de posventa de tus clientes.")
        return

    for claim in claims:
        cid = claim["id"]
        with st.container(border=True):
            st.markdown(f"### Reclamo #{cid}")
            status_badge(claim["status"])
            st.caption(f"Solicitud #{claim['visit']} · abierto el {claim['created_at']}")
            st.write(f"**Motivo:** {claim['description']}")

            if claim["professional_response"]:
                st.write(f"**Tu respuesta:** {claim['professional_response']}")
            if claim["admin_resolution"]:
                st.write(f"**Resolución de Overol:** {claim['admin_resolution']}")

            if claim["raw_status"] == "OPEN":
                response = st.text_area("Respuesta al cliente", key=f"claim_response_{cid}", max_chars=MAX_TEXTO)
                if st.button("Responder reclamo", key=f"respond_claim_{cid}"):
                    if not response.strip():
                        st.warning("Escribe una respuesta.")
                    else:
                        _claim_action(cid, "respond", "Respuesta enviada al cliente.", response=response.strip())

            if claim["raw_status"] in ("OPEN", "PROFESSIONAL_RESPONDED"):
                if st.button("Pedir mediación de Overol", key=f"escalate_claim_{cid}"):
                    _claim_action(cid, "escalate", "Reclamo enviado a mediación de Overol.")


def _claim_action(claim_id, name, success, **payload):
    try:
        requests_api.claim_action(claim_id, name, **payload)
    except api_client.ApiError as error:
        st.error(f"No se pudo actualizar el reclamo. {error}")
        return
    flash(success)
    st.rerun()


def _client_rating_block(request):
    """Historia 024: el profesional califica al cliente (POST /api/ratings/ con el mismo servicio)."""
    rid = request["id"]
    rated = st.session_state.setdefault("_rated_visits", set())

    if rid in rated:
        st.success("✓ Ya calificaste a este cliente.")
        return

    with st.expander("⭐ Calificar al cliente"):
        c1, c2, c3 = st.columns(3)
        quality = c1.slider("Claridad del encargo", 1, 5, 5, key=f"client_quality_{rid}")
        punctuality = c2.slider("Puntualidad", 1, 5, 5, key=f"client_punctuality_{rid}")
        treatment = c3.slider("Trato", 1, 5, 5, key=f"client_treatment_{rid}")
        comment = st.text_input("Comentario (opcional)", max_chars=MAX_TEXTO, key=f"client_comment_{rid}")

        if st.button("Guardar calificación", type="primary", key=f"save_client_rating_{rid}"):
            try:
                requests_api.rate(rid, quality, punctuality, treatment, comment)
            except api_client.ApiError as error:
                if requests_api.already_rated(error):
                    rated.add(rid)
                    flash("Ya habías calificado a este cliente.", "info")
                    st.rerun()
                st.error(f"No se pudo guardar la calificación. {error}")
                return
            rated.add(rid)
            flash("Calificación al cliente registrada.")
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

    st.info(
        "🔐 Tus documentos se guardan cifrados. Solo el equipo de administración "
        "de Overol puede abrirlos y cada acceso queda registrado."
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

        try:
            encrypted = encrypt_document(content)
        except ImportError:
            st.error("No se pudo guardar el documento: falta instalar el paquete cryptography.")
            return

        safe_name = f"{user['id']}_{secrets.token_hex(8)}{extension}.enc"
        (UPLOAD_DIR / safe_name).write_bytes(encrypted)

        conn = get_connection()

        conn.execute(
            """
            INSERT INTO verification_documents
            (professional_id, document_type, original_name, stored_name, uploaded_at, encrypted)
            VALUES (?, ?, ?, ?, ?, 1)
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


def _verification_messages(user, professional):
    """Hilo con el equipo de Overol sobre la verificación (máx. 500 caracteres por mensaje)."""
    pid = professional["id"]

    section("💬 Mensajes con el equipo de Overol")

    messages = get_verification_messages(pid)

    if not messages:
        st.caption(
            "¿Tienes dudas sobre tu verificación? Escríbenos aquí; "
            "te responderemos en este mismo lugar."
        )

    for message in messages:
        thread_message(
            "Equipo Overol" if message["from_admin"] else "Tú",
            message["created_at"],
            message["body"],
            message["from_admin"],
        )

    with st.form(f"verif_msg_form_{pid}", clear_on_submit=True):
        body = st.text_area(
            "Tu mensaje",
            max_chars=MAX_TEXTO,
            placeholder="Ej.: Subí mi cédula por ambos lados, ¿falta algo?",
            key=f"verif_msg_text_{pid}",
        )
        sent = st.form_submit_button("Enviar mensaje", key=f"verif_msg_send_{pid}")

    if sent:
        ok, error = add_verification_message(pid, user["id"], body)

        if not ok:
            st.error(error)
        else:
            audit(user["id"], "VERIFY_MESSAGE", "professionals", pid, "Mensaje al administrador")
            flash("Mensaje enviado al equipo de Overol.")
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
    available = [o for o in ESPECIALIDADES_POR_OFICIO if o not in active_names]  # etapa F: del backend

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
