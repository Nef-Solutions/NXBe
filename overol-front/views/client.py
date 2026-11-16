"""Vistas del rol Cliente (RF 002, 003, 004, 006, 009)."""

import streamlit as st

from core import api_client, catalog_api, requests_api
from core.constants import (
    FEE_NOTE,
    MAX_TEXTO,
    COMUNAS,
    pantallas_visibles,
)
from ui.components import (
    _when,
    contact_box,
    empty_state,
    flash,
    format_professional_card,
    hero,
    hold_to_confirm,
    nav_bar,
    notifications_page,
    section,
    status_badge,
    support_box,
)
from views.about import about_page
from views.home import home_page
from views.shared import (
    PROFILE_FOCUS_KEY,
    apply_deeplink,
    close_professional,
    open_professional,
    professional_profile_client,
    professional_profile_public,
    user_profile_page,
)


def client_dashboard(user):
    # ?profesional=ID abre directamente el perfil de ese profesional
    apply_deeplink("client_navigation", "🔎 Buscar profesionales", "_client_prev_menu")

    options = pantallas_visibles("cliente", [
        "🏠 Inicio",
        "🔎 Buscar profesionales",
        "📋 Mis solicitudes",
        "🛠️ Mis reclamos",
        "🔔 Notificaciones",
        "👤 Mi perfil",
        "ℹ️ Quiénes somos",
    ])
    badges = {}
    if "🔔 Notificaciones" in options:
        badges["🔔 Notificaciones"] = api_client.unread_notifications()

    menu = nav_bar("client_navigation", options, badges=badges)

    hero(
        "Encuentra al profesional que necesitas para tu hogar",
        "Busca por especialidad y ubicación, revisa perfiles verificados, "
        "solicita una visita y evalúa el servicio.",
    )

    # Al cambiar de sección se descarta el perfil abierto, para que no
    # "aparezca" solo en otra pantalla.
    if st.session_state.get("_client_prev_menu") != menu:
        close_professional()
        st.session_state.pop(PROFILE_FOCUS_KEY, None)
        st.session_state["_client_prev_menu"] = menu

    if menu == "🏠 Inicio":
        client_home()

    elif menu == "🔎 Buscar profesionales":
        client_search(user)

    elif menu == "📋 Mis solicitudes":
        client_requests(user)

    elif menu == "🛠️ Mis reclamos":
        client_claims(user)

    elif menu == "🔔 Notificaciones":
        notifications_page(user)

    elif menu == "👤 Mi perfil":
        user_profile_page(user)

    elif menu == "ℹ️ Quiénes somos":
        about_page()


def client_home():
    home_page(
        "cliente",
        "client_navigation",
        "_client_prev_menu",
        "🔎 Buscar profesionales",
        show_hero=False,
    )


def _show_selected_profile(user):
    """Si hay un profesional seleccionado, muestra su perfil con botón de volver.
    `user` es None cuando navega un visitante (perfil público, sin datos personales).
    Devuelve True cuando mostró el perfil (el llamador debe terminar su render)."""
    selected = st.session_state.get("selected_professional")

    if not selected:
        return False

    if st.button("← Volver a la lista de profesionales", key="back_from_profile"):
        close_professional()
        st.rerun()

    if user is None:
        professional_profile_public(selected)
    else:
        professional_profile_client(user, selected)

    return True


def _professional_grid(professionals, key_prefix, anonymous=False):
    """Muestra tarjetas en filas de 3 columnas con botón «Ver perfil». Cada fila va en su
    propio contenedor para que las tarjetas tengan el mismo alto (estilo «st-key-pro_grid_»)."""
    for start in range(0, len(professionals), 3):
        with st.container(key=f"pro_grid_{key_prefix}_{start}"):
            cols = st.columns(3)

            for col, professional in zip(cols, professionals[start:start + 3]):
                with col:
                    format_professional_card(professional, anonymous=anonymous)

                    if st.button(
                        "Ver perfil" if anonymous else "Ver perfil y solicitar visita",
                        key=f"{key_prefix}_{professional['id']}",
                        use_container_width=True,
                    ):
                        open_professional(professional["id"])
                        st.rerun()


def _clear_search():
    # Callback de «Limpiar búsqueda»: borra la palabra clave y vuelve los filtros a «Todas».
    st.session_state["search_text"] = ""
    st.session_state["search_trade"] = "Todas"
    st.session_state["search_commune"] = "Todas"
    for key in [k for k in st.session_state if str(k).startswith("search_specialty_")]:
        del st.session_state[key]


def client_search(user):
    """Historias 002, 008 y 4.16 (palabra clave). `user` es None para visitantes."""
    if _show_selected_profile(user):
        return

    anonymous = user is None

    section("🔎 Buscar profesionales")

    text = st.text_input(
        "Buscar por palabra clave",
        key="search_text",
        max_chars=100,
        placeholder="Busca por oficio, especialidad o palabra clave (ej. fuga, enchufe, pintar)",
        label_visibility="collapsed",
    ).strip()

    try:
        trade_options = catalog_api.trade_options()
    except api_client.ApiError as error:
        st.error(f"No se pudo cargar el catálogo de profesionales. {error}")
        return

    # Modo api: un oficio del front que el backend aún no tiene (p. ej. desde la portada)
    missing_trade = st.session_state.get("search_trade", "Todas")
    if missing_trade not in ["Todas"] + trade_options:
        st.session_state["search_trade"] = "Todas"
        st.info(f"El oficio «{missing_trade}» todavía no está disponible en el catálogo. Te mostramos todos los oficios.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        trade = st.selectbox(
            "Oficio",
            ["Todas"] + trade_options,
            key="search_trade",
        )

    try:
        specialty_options = catalog_api.specialty_options(trade)
    except api_client.ApiError as error:
        st.error(f"No se pudo cargar el catálogo de profesionales. {error}")
        return

    with c2:
        # La clave depende del oficio: al cambiarlo, la especialidad se reinicia.
        specialty = st.selectbox(
            "Especialidad",
            ["Todas"] + specialty_options,
            key=f"search_specialty_{trade}",
        )

    with c3:
        commune = st.selectbox(
            "Zona de cobertura (comuna)",
            ["Todas"] + COMUNAS,
            key="search_commune",
        )

    with c4:
        order = st.selectbox(
            "Ordenar por",
            ["Mejor evaluados", "Nombre"],
            key="search_order",
        )

    try:
        professionals = catalog_api.list_professionals(
            trade=trade,
            specialty=specialty,
            commune=commune,
            anonymous=anonymous,
        )
    except api_client.ApiError as error:
        st.error(f"No se pudo cargar el catálogo de profesionales. {error}")
        return

    # El visitante ve tarjetas anónimas: buscar por nombre le revelaría quién es cada uno.
    professionals = catalog_api.search_professionals(professionals, text, include_name=not anonymous)

    if order == "Mejor evaluados":
        professionals = sorted(
            professionals,
            key=lambda p: catalog_api.rating(p)[1],
            reverse=True,
        )
    else:
        # El backend no los entrega ordenados por nombre
        professionals = sorted(professionals, key=lambda p: (p["name"], p["id"]))

    st.write(f"**{len(professionals)} profesionales disponibles**")

    if not professionals:
        filters_on = any(value != "Todas" for value in (trade, specialty, commune))

        if text:
            title = f"No encontramos profesionales para «{text}»"
            hint = "Prueba con otras palabras (ej. fuga, enchufe, mueble, pintar)"
            hint += " o quita algunos filtros." if filters_on else "."
        else:
            title = "No encontramos profesionales con esos filtros"
            hint = "Prueba ampliando la comuna o cambiando el oficio o la especialidad."

        empty_state("🔍", title, hint)  # empty_state escapa el texto

        if text or filters_on:
            st.button("Limpiar búsqueda", key="search_clear", on_click=_clear_search)
        return

    _professional_grid(professionals, "client_view_prof", anonymous)


def client_requests(user):
    """Historias 010 a 013: solicitudes del cliente (GET /api/requests/)."""
    section("📋 Mis solicitudes")

    try:
        requests = requests_api.list_requests()
        claims = {c["visit"]: c for c in requests_api.list_claims()}
        tickets = api_client.list_tickets()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar tus solicitudes. {error}")
        return

    if not requests:
        empty_state(
            "📋",
            "Todavía no tienes solicitudes",
            "Busca un profesional y envía tu primera solicitud de visita.",
        )
        return

    status_filter = st.selectbox(
        "Filtrar por estado",
        ["Todas"] + list(dict.fromkeys(requests_api.ESTADOS.values())),
        key="client_requests_filter",
    )

    shown = [r for r in requests if status_filter == "Todas" or r["status"] == status_filter]

    if not shown:
        st.info("No hay solicitudes con ese estado.")

    for request in shown:
        _client_request_card(user, request, claims, [t for t in tickets if t.get("visit") == request["id"]])


def _client_request_card(user, request, claims, tickets):
    rid = request["id"]
    raw = request["raw_status"]

    with st.container(border=True):
        top = st.columns([4, 1])

        with top[0]:
            st.markdown(f"### Solicitud #{rid} · {request['professional_name']}")

        with top[1]:
            status_badge(request["status"])

        d1, d2 = st.columns(2)

        with d1:
            st.write(f"**Oficio:** {request['trade']} · {request['specialty']}")
            st.write(f"**Comuna:** {request['commune']}")

        with d2:
            st.write(f"**Fecha tentativa:** {request['date']} · {request['time']}")
            st.write(f"**Dirección:** {request['visit_address']}")

        st.write(f"**Descripción:** {request['description']}")

        if raw == "REJECTED":
            st.warning(
                "El profesional rechazó la solicitud. "
                f"**Motivo:** {request['rejection_reason'] or 'Sin motivo informado'}"
            )

        # Contacto: el backend solo lo entrega con la solicitud aceptada o finalizada
        if request["contact"]:
            contact_box(
                {"name": request["professional_name"], **request["contact"]},
                "Datos de contacto del profesional",
            )

        if raw == "PENDING":
            st.caption(
                "⏳ Esperando la respuesta del profesional"
                + (f" · vence el {request['expires_at']}" if request["expires_at"] else "")
            )

        if raw == "EXPIRED":
            st.info(
                "Esta solicitud venció porque el profesional no respondió a tiempo. "
                "Puedes volver a solicitar desde «Buscar profesionales»."
            )

        if raw == "CANCELLED":
            if request["cancelled_by"] == "PROFESSIONAL":
                st.warning(
                    "El profesional canceló esta solicitud. "
                    f"**Motivo:** {request['cancel_reason'] or 'Sin motivo informado'}"
                )
            else:
                st.caption("Cancelaste esta solicitud.")

        if raw == "FORCED_CLOSED":
            st.info("El equipo de Overol cerró esta solicitud.")

        # ---------- Confirmar finalización (ambas partes) ----------
        if raw in ("ACCEPTED", "PROFESSIONAL_FINISHED"):
            if request["client_confirmed"]:
                st.info("✓ Ya confirmaste la finalización. Falta la confirmación del profesional.")
            else:
                if request["professional_confirmed"]:
                    st.info("El profesional informó que terminó el servicio. Falta tu confirmación.")
                if st.button("Confirmar finalización del servicio", type="primary", key=f"complete_{rid}"):
                    _client_action(rid, "confirm", "Confirmación registrada.")

        # ---------- Cancelar (pendiente o aceptada) con confirmación ----------
        if raw in ("PENDING", "ACCEPTED"):
            _cancel_flow(request)

        # ---------- Aceptada: el servicio se paga directo al profesional ----------
        if raw == "ACCEPTED":
            st.caption(f"💰 {FEE_NOTE}")

        # ---------- Finalizada: evaluar y posventa ----------
        if raw == "COMPLETED":
            _rating_block(request)
            _claim_block(request, claims.get(rid))

        # ---------- Tickets de soporte sobre esta solicitud ----------
        support_box(user, rid, "cliente", tickets, after_create=_ticket_created)


def _client_action(rid, name, success, kind="success"):
    """Envía la acción al backend y recarga. Si la solicitud ya cambió (409), lo informa."""
    try:
        updated = requests_api.action(rid, name)
    except api_client.ApiError as error:
        flash(str(error), "warning")
    else:
        if updated["raw_status"] == "COMPLETED":
            success = "Servicio finalizado por ambas partes."
        flash(success, kind)
    st.rerun()


def _cancel_flow(request):
    """Cancelación en dos pasos: advertencia + botón que hay que mantener presionado."""
    rid = request["id"]
    flag = f"cancel_confirm_{rid}"

    if not st.session_state.get(flag):
        if st.button("Cancelar solicitud", key=f"cancel_{rid}"):
            st.session_state[flag] = True
            st.rerun()
        return

    st.warning(
        "⚠️ **¿Estás seguro de que quieres cancelar la hora?** "
        "El profesional será informado y la solicitud quedará cancelada. "
        "Esta acción no se puede deshacer."
    )

    if hold_to_confirm(
        key=f"hold_cancel_{rid}",
        label="Mantén presionado para confirmar la cancelación",
    ):
        st.session_state.pop(flag, None)
        _client_action(rid, "cancel", "Solicitud cancelada.")

    if st.button("No, mantener mi solicitud", key=f"cancel_no_{rid}"):
        st.session_state.pop(flag, None)
        st.rerun()


def _rating_block(request):
    """Historia 006: el cliente evalúa al profesional (POST /api/ratings/). El backend no
    permite consultar si ya se evaluó: se recuerda en la sesión y se confirma con su 400."""
    rid = request["id"]
    rated = st.session_state.setdefault("_rated_visits", set())

    if rid in rated:
        st.success("✓ Ya evaluaste este servicio. ¡Gracias!")
        return

    with st.expander("⭐ Evaluar el servicio"):
        c1, c2, c3 = st.columns(3)
        quality = c1.slider("Calidad", 1, 5, 5, key=f"rate_quality_{rid}")
        punctuality = c2.slider("Puntualidad", 1, 5, 5, key=f"rate_punctuality_{rid}")
        treatment = c3.slider("Trato", 1, 5, 5, key=f"rate_treatment_{rid}")
        comment = st.text_area("Comentario (opcional)", max_chars=MAX_TEXTO, key=f"rate_comment_{rid}")

        if st.button("Enviar evaluación", type="primary", key=f"send_rating_{rid}"):
            try:
                requests_api.rate(rid, quality, punctuality, treatment, comment)
            except api_client.ApiError as error:
                if requests_api.already_rated(error):
                    rated.add(rid)
                    flash("Ya habías evaluado este servicio.", "info")
                    st.rerun()
                st.error(f"No se pudo enviar la evaluación. {error}")
                return
            rated.add(rid)
            flash("Evaluación enviada. ¡Gracias por ayudar a otros clientes!")
            st.rerun()


def _claim_block(request, claim):
    """Historia 009: reclamo de posventa de un servicio finalizado (POST /api/claims/)."""
    rid = request["id"]

    if claim:
        st.info(f"Abriste el reclamo #{claim['id']} ({claim['status']}). Síguelo en «🛠️ Mis reclamos».")
        return

    with st.expander("🛠️ Abrir un reclamo de posventa"):
        description = st.text_area(
            "¿Qué problema tuviste con el servicio?",
            max_chars=MAX_TEXTO,
            key=f"claim_reason_{rid}",
        )
        if st.button("Enviar reclamo", key=f"send_claim_{rid}"):
            if not description.strip():
                st.warning("Debes describir el problema.")
                return
            try:
                created = requests_api.create_claim(rid, description)
            except api_client.ApiError as error:
                st.error(f"No se pudo abrir el reclamo. {error}")
                return
            flash(f"Reclamo #{created['id']} enviado. El profesional y Overol lo revisarán.")
            st.rerun()


NEW_TICKET_KEY = "_client_new_ticket"


def _ticket_created(ticket):
    """Tras abrir un ticket desde una solicitud: lleva al cliente a «Mis reclamos», donde lo ve."""
    st.session_state["client_navigation"] = "🛠️ Mis reclamos"
    st.session_state[NEW_TICKET_KEY] = ticket.get("id")
    return f"Ticket #{ticket.get('id')} enviado a soporte (solicitud #{ticket.get('visit')})."


def _go_to_requests():
    # Callback: vuelve a «Mis solicitudes» desde un ticket o un reclamo
    st.session_state["client_navigation"] = "📋 Mis solicitudes"


def _client_tickets():
    """Tickets de soporte del cliente (GET /api/tickets/), con su solicitud de origen."""
    try:
        tickets = api_client.list_tickets()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar tus tickets de soporte. {error}")
        return

    if not tickets:
        return

    new_id = st.session_state.pop(NEW_TICKET_KEY, None)
    st.markdown("#### 💬 Tickets de soporte")
    for ticket in tickets:
        tid = ticket.get("id")
        with st.container(border=True, key=f"client_ticket_{tid}"):
            top = st.columns([4, 1])
            with top[0]:
                st.markdown(f"**Ticket #{tid} · {ticket.get('subject') or ''}**"
                            + ("  ·  🆕 recién enviado" if tid == new_id else ""))
                st.caption(f"Solicitud #{ticket.get('visit')} · {_when(ticket.get('created_at'))}")
            with top[1]:
                status_badge(api_client.ESTADOS_TICKET.get(ticket.get("status"), ticket.get("status")))
            st.write(ticket.get("description") or "")
            if ticket.get("response"):
                st.write(f"**Respuesta de soporte:** {ticket['response']}")
            st.button(f"Ver solicitud #{ticket.get('visit')} en «Mis solicitudes»", key=f"ticket_to_request_{tid}",
                      on_click=_go_to_requests)


def client_claims(user):
    """Historia 009: reclamos del cliente (GET /api/claims/) y escalar a Overol. También muestra
    sus tickets de soporte (GET /api/tickets/): se abren desde cualquier solicitud, mientras que
    un reclamo solo se puede abrir sobre un servicio finalizado."""
    section("🛠️ Mis reclamos")

    _client_tickets()

    try:
        claims = requests_api.list_claims()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar tus reclamos. {error}")
        return

    st.markdown("#### 🛠️ Reclamos de posventa")
    if not claims:
        empty_state("🛠️", "No tienes reclamos registrados", "Si un servicio no salió bien, puedes abrir un reclamo desde «Mis solicitudes».")
        return

    for claim in claims:
        with st.container(border=True):
            status_badge(claim["status"])
            st.markdown(f"### Reclamo #{claim['id']}")
            st.caption(f"Solicitud #{claim['visit']} · abierto el {claim['created_at']}")
            st.write(f"**Motivo:** {claim['description']}")

            if claim["professional_response"]:
                st.write(f"**Respuesta del profesional:** {claim['professional_response']}")
            if claim["admin_resolution"]:
                st.write(f"**Resolución de Overol:** {claim['admin_resolution']}")

            if claim["raw_status"] in ("OPEN", "PROFESSIONAL_RESPONDED"):
                if st.button("Pedir mediación de Overol", key=f"escalate_claim_{claim['id']}"):
                    try:
                        requests_api.claim_action(claim["id"], "escalate")
                    except api_client.ApiError as error:
                        st.error(f"No se pudo escalar el reclamo. {error}")
                    else:
                        flash("Reclamo enviado a mediación de Overol.")
                        st.rerun()
