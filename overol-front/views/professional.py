"""Vistas del rol Profesional (Historias 014 a 025)."""

import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from core import api_client, catalog_api, requests_api
from core.constants import (
    COMUNAS,
    DIAS_SEMANA,
    HORAS,
    MAX_TEXTO,
    MOTIVOS_RECHAZO,
    pantallas_visibles,
)
from core.session import load_user
from ui.components import (
    contact_box,
    empty_state,
    flash,
    hero,
    nav_bar,
    notifications_page,
    section,
    status_badge,
    support_box,
)
from ui.profile import profile_header, profile_reviews, profile_sections
from views import payments
from views.about import about_page
from views.shared import PROFILE_FOCUS_KEY, user_profile_page

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
        "ℹ️ Quiénes somos",
    ])

    badges = {}
    if "🔔 Notificaciones" in options:
        badges["🔔 Notificaciones"] = api_client.unread_notifications()
    if "🛠️ Reclamos" in options:
        try:
            badges["🛠️ Reclamos"] = sum(1 for c in requests_api.list_claims() if c["raw_status"] == "OPEN")
        except api_client.ApiError:
            pass

    menu = nav_bar("professional_navigation", options, badges=badges)

    # Al cambiar de sección se olvida la opción elegida en el menú lateral
    if st.session_state.get("_pro_prev_menu") != menu:
        st.session_state.pop(PROFILE_FOCUS_KEY, None)
        st.session_state["_pro_prev_menu"] = menu

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
        professional_profile(user)

    elif menu == "📍 Cobertura":
        professional_coverage(user)

    elif menu == "💳 Suscripción":
        professional_subscription(user)

    elif menu == "🪪 Verificación":
        professional_verification(user)

    elif menu == "🛠️ Reclamos":
        professional_claims(user)

    elif menu == "🎓 Desarrollo profesional":
        professional_training(user)

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


def professional_profile(user):
    """Mi perfil: datos personales, vista pública con reputación y oficios."""
    _verification_banner(user)

    tab_data, tab_public, tab_trades = st.tabs(["👤 Datos personales", "👁️ Vista pública y reputación", "🛠️ Oficios"])

    with tab_data:
        user_profile_page(user)

    with tab_public:
        professional_reputation(user)

    with tab_trades:
        _trades_manager(user)


def professional_reputation(user):
    """Historia 025: perfil como lo ven los clientes, con la valoración y las opiniones
    (GET /api/catalog/professionals/{id}/). El backend aún no valora por oficio."""
    pid = user.get("professional_profile_id")
    try:
        professional = catalog_api.get_professional(pid) if pid else None
    except api_client.ApiError as error:
        st.error(f"No se pudo cargar tu perfil público. {error}")
        return

    if not professional:
        st.info(
            "Tu perfil público aparece cuando estás **verificado** y tienes una **suscripción vigente** "
            "(«💳 Suscripción»). Mientras tanto, los clientes no te ven en el catálogo."
        )
        return

    total, average = catalog_api.rating(professional)
    c1, c2 = st.columns(2)
    c1.metric("Valoración promedio", f"{average:.1f} ★" if average else "Sin valoraciones")
    c2.metric("Opiniones", total or 0)
    st.caption("Así ven tu perfil los clientes registrados:")
    profile_header(professional, anonymous=False)
    profile_sections(professional)
    profile_reviews(professional)


def _trades_manager(user):
    """Historia 018: oficios del profesional (GET/POST/PATCH/DELETE /api/professionals/me/trades/)."""
    try:
        trades = api_client.list_my_trades()
        categories = {c["id"]: c["name"] for c in api_client.get_categories()}
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar tus oficios. {error}")
        return

    st.caption(
        "Cada oficio tiene sus especialidades: los clientes eligen una al solicitarte una visita. "
        "Un oficio desactivado deja de recibir solicitudes."
    )

    for trade in trades:
        tid = trade["id"]
        name = categories.get(trade.get("category_id"), f"Oficio #{trade.get('category_id')}")
        active = trade.get("is_active", True)
        with st.container(border=True):
            st.markdown(f"**{name}** · {trade.get('years_experience') or 0} años de experiencia"
                        + ("" if active else " · ⛔ desactivado"))
            if trade.get("description"):
                st.caption(trade["description"])
            if not active:
                st.caption("Por ahora el backend no permite reactivar un oficio desactivado.")
                continue

            with st.expander("Editar"):
                years = st.number_input("Años de experiencia", 0, 60, int(trade.get("years_experience") or 0),
                                        key=f"trade_years_{tid}")
                description = st.text_input("Descripción", value=trade.get("description") or "",
                                            max_chars=MAX_TEXTO, key=f"trade_desc_{tid}")
                options = _specialty_options(trade.get("category_id"))
                extra = st.multiselect("Agregar especialidades", [s["name"] for s in options], key=f"trade_specs_{tid}",
                                       help="Las especialidades se agregan; por ahora no se pueden quitar.")
                if st.button("Guardar cambios", key=f"trade_save_{tid}"):
                    fields = {"years_experience": int(years), "description": description.strip()}
                    if extra:
                        fields["specialties"] = [s["id"] for s in options if s["name"] in extra]
                    _trade_call(api_client.update_trade, f"Oficio «{name}» actualizado.", tid, **fields)
                if st.button("Desactivar oficio", key=f"trade_off_{tid}"):
                    _trade_call(api_client.deactivate_trade, f"Oficio «{name}» desactivado.", tid)

    used = {t.get("category_id") for t in trades}
    available = {cid: name for cid, name in categories.items() if cid not in used}
    if not available:
        return

    st.markdown("#### ➕ Agregar un oficio")
    names = sorted(available.values())
    new_name = st.selectbox("Oficio", names, key="trade_new_category")
    new_id = next(cid for cid, name in available.items() if name == new_name)
    options = _specialty_options(new_id)
    if options:
        new_specs = st.multiselect("Especialidades", [s["name"] for s in options], key=f"trade_new_specs_{new_id}")
    else:
        new_specs = []
        st.warning(f"«{new_name}» todavía no tiene especialidades en el servidor: no recibirás solicitudes de ese oficio.")
    new_years = st.number_input("Años de experiencia", 0, 60, 0, key="trade_new_years")
    new_desc = st.text_input("Descripción (opcional)", max_chars=MAX_TEXTO, key="trade_new_desc")

    if st.button("Agregar oficio", type="primary", key="trade_add"):
        if options and not new_specs:
            st.warning("Elige al menos una especialidad.")
            return
        ids = [s["id"] for s in options if s["name"] in new_specs]
        _trade_call(api_client.add_trade, f"Oficio «{new_name}» agregado.", new_id, new_years, new_desc, ids)


def _specialty_options(category_id):
    try:
        return api_client.get_specialties(category_id) if category_id else []
    except api_client.ApiError:
        return []


def _trade_call(func, success, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except api_client.ApiError as error:
        st.error(f"No se pudo guardar el oficio. {error}")
        return
    st.cache_data.clear()  # el catálogo cacheado debe mostrar el cambio
    flash(success)
    st.rerun()


def professional_training(user):
    """Historia 007: centro de desarrollo profesional (GET /api/professional-center/content/).
    El backend no permite consultar el progreso: lo completado se recuerda en la sesión."""
    section("🎓 Centro de Desarrollo Profesional")

    try:
        contents = api_client.list_content()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar los contenidos. {error}")
        return

    if not contents:
        empty_state("🎓", "Aún no hay contenidos", "El equipo de Overol publicará aquí guías y cursos.")
        return

    done = st.session_state.setdefault("_completed_content", set())
    st.caption(f"Completaste {len(done & {c['id'] for c in contents})} de {len(contents)} contenidos en esta sesión.")

    for module, label in api_client.MODULOS_CONTENIDO.items():
        items = sorted((c for c in contents if c.get("module") == module), key=lambda c: c.get("order", 0))
        if not items:
            continue
        st.markdown(f"#### {label}")
        for content in items:
            cid = content["id"]
            with st.container(border=True):
                st.markdown(f"**{content.get('title', '')}**" + (" · ✅ completado" if cid in done else ""))
                if content.get("description"):
                    st.caption(content["description"])
                if content.get("url"):
                    st.link_button("Abrir contenido", content["url"])
                if cid not in done and st.button("Marcar como completado", key=f"content_done_{cid}"):
                    try:
                        api_client.complete_content(cid)
                    except api_client.ApiError as error:
                        if error.status != 400:  # 400: ya estaba registrado como completado
                            st.error(f"No se pudo registrar tu avance. {error}")
                            continue
                    done.add(cid)
                    st.rerun()
