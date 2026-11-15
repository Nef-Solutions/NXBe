"""Vistas del rol Administrador (RF 001, 008, 009) contra el backend.

Lo que tiene endpoint: indicadores de reclamos y tickets, verificación (aprobar o rechazar y
ver la cédula), estado de una cuenta, reclamos (resolver) y la bandeja de soporte (resolver).
Sin endpoint (ocultas, PANTALLAS_PENDIENTES_API y PEDIDO): moderación de reseñas, contenidos,
bitácora, listado de usuarios y de verificaciones pendientes.
"""

from collections import Counter

import altair as alt
import streamlit as st

from core import api_client, requests_api
from core.config import ADMIN_URL
from core.constants import MAX_TEXTO, pantallas_visibles
from ui.components import empty_state, flash, hero, metric_card, nav_bar, section, security_note, status_badge
from views.about import about_page
from views.shared import PROFILE_FOCUS_KEY, user_profile_page


def _state_chart(counts):
    """Barras horizontales por estado. Con Altair (labelLimit=0) las etiquetas largas, como
    «Respondido por el profesional», se leen completas; st.bar_chart las cortaba en celular."""
    data = alt.Data(values=[{"Estado": state, "Cantidad": n} for state, n in counts.items()])
    chart = (
        alt.Chart(data)
        .mark_bar(color="#1B4F8A", cornerRadiusEnd=4)
        .encode(
            x=alt.X("Cantidad:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
            y=alt.Y("Estado:N", title=None, sort="-x",
                    axis=alt.Axis(labelLimit=0, labelPadding=8, labelFontSize=12)),
            tooltip=[alt.Tooltip("Estado:N"), alt.Tooltip("Cantidad:Q")],
        )
        .properties(height=alt.Step(38), padding={"left": 8, "right": 12, "top": 4, "bottom": 4})
    )
    st.altair_chart(chart, use_container_width=True)


def admin_dashboard(user):
    options = pantallas_visibles("admin", [
        "📊 Indicadores",
        "🪪 Verificación",
        "👥 Usuarios",
        "⭐ Moderación",
        "🛠️ Reclamos",
        "🎓 Contenidos",
        "📜 Trazabilidad",
        "💬 Soporte",
        "ℹ️ Quiénes somos",
    ])
    badges = {}
    try:
        badges["💬 Soporte"] = sum(1 for t in api_client.list_tickets() if t.get("status") != "RESOLVED")
        badges["🛠️ Reclamos"] = sum(1 for c in requests_api.list_claims() if c["raw_status"] == "ESCALATED")
    except api_client.ApiError:
        pass

    menu = nav_bar("admin_navigation", options, badges=badges)

    hero(
        "Panel de administración",
        "Gestiona verificaciones, cuentas, reclamos y la bandeja de soporte.",
    )

    # Al cambiar de sección se olvida la opción elegida en el menú lateral
    if st.session_state.get("_admin_prev_menu") != menu:
        st.session_state.pop(PROFILE_FOCUS_KEY, None)
        st.session_state["_admin_prev_menu"] = menu

    # «Mi perfil», «Editar datos» y «Cambiar contraseña» del menú lateral (misma pantalla del resto)
    if st.session_state.get(PROFILE_FOCUS_KEY):
        st.button("← Volver al panel", key="admin_account_back", on_click=st.session_state.pop,
                  args=(PROFILE_FOCUS_KEY, None))
        user_profile_page(user)
        return

    if menu == "📊 Indicadores":
        admin_summary()

    elif menu == "🪪 Verificación":
        admin_verification(user)

    elif menu == "👥 Usuarios":
        admin_users(user)

    elif menu == "🛠️ Reclamos":
        admin_claims(user)

    elif menu == "💬 Soporte":
        admin_support(user)

    elif menu == "ℹ️ Quiénes somos":
        about_page()


def _django_admin_note(what):
    st.caption(
        f"{what} todavía no tiene endpoint en el backend: mientras tanto se hace en el administrador "
        f"de Django (**/admin/** del backend: {ADMIN_URL})."
    )


def admin_summary():
    """Indicadores con lo que el backend entrega al admin: reclamos y tickets (todos)."""
    section("📊 Indicadores de la plataforma")

    try:
        claims = requests_api.list_claims()
        tickets = api_client.list_tickets()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar los indicadores. {error}")
        return

    claim_states = Counter(c["status"] for c in claims)
    ticket_states = Counter(api_client.ESTADOS_TICKET.get(t.get("status"), t.get("status")) for t in tickets)

    cols = st.columns(4)
    for col, (icon, label, value) in zip(cols, [
        ("🛠️", "Reclamos", len(claims)),
        ("⚖️", "En mediación", claim_states.get("En mediación", 0)),
        ("💬", "Tickets", len(tickets)),
        ("📭", "Tickets abiertos", sum(v for k, v in ticket_states.items() if k != "Resuelto")),
    ]):
        with col:
            metric_card(value, label, icon)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Estado de reclamos")
        if claim_states:
            _state_chart(claim_states)
        else:
            st.caption("Sin reclamos.")
    with c2:
        st.markdown("#### Estado de tickets")
        if ticket_states:
            _state_chart(ticket_states)
        else:
            st.caption("Sin tickets.")

    _django_admin_note("El conteo de usuarios, profesionales verificados y solicitudes")


def admin_verification(user):
    """Verificación de identidad: ver la cédula y aprobar o rechazar con motivo."""
    section("🪪 Verificación de profesionales")
    st.info(
        "El backend todavía no entrega la lista de verificaciones pendientes. Escribe el **id del perfil "
        "profesional** (lo ves en `/admin/` → Professional profiles) para revisar sus documentos."
    )

    pid = st.number_input("Id del perfil profesional", min_value=1, step=1, value=None, key="verif_profile_id")
    if not pid:
        return
    pid = int(pid)

    c1, c2 = st.columns(2)
    for col, side, label in ((c1, "front", "Frente"), (c2, "back", "Reverso")):
        with col:
            st.markdown(f"**{label} de la cédula**")
            if st.button(f"Ver {label.lower()}", key=f"view_doc_{side}_{pid}"):
                try:
                    data, kind, name = api_client.download_verification_document(pid, side)
                except api_client.ApiError as error:
                    st.error(str(error))
                else:
                    st.session_state[f"_doc_{side}_{pid}"] = (data, kind, name)
            doc = st.session_state.get(f"_doc_{side}_{pid}")
            if doc:
                data, kind, name = doc
                if kind.startswith("image/"):
                    try:
                        st.image(data)
                    except Exception:
                        st.caption("No se pudo mostrar la imagen: descárgala para revisarla.")
                else:
                    st.caption(f"Archivo {name}: descárgalo para revisarlo.")
                st.download_button("Descargar", data, file_name=name, mime=kind, key=f"download_doc_{side}_{pid}")

    reason = st.text_area(
        "Motivo de la decisión",
        max_chars=MAX_TEXTO,
        placeholder="Obligatorio al rechazar. Se le informa al profesional.",
        key=f"verif_reason_{pid}",
    )
    a1, a2 = st.columns(2)
    if a1.button("✓ Aprobar verificación", type="primary", key=f"admin_approve_{pid}"):
        _decide(pid, "approve", reason)
    if a2.button("✕ Rechazar verificación", key=f"admin_reject_{pid}"):
        if not reason.strip():
            st.warning("Escribe el motivo del rechazo.")
        else:
            _decide(pid, "reject", reason)

    security_note("Los documentos son privados: se descargan solo con una cuenta de administrador.")


def _decide(pid, decision, reason):
    try:
        api_client.decide_verification(pid, decision, reason)
    except api_client.ApiError as error:
        st.error(f"No se pudo registrar la decisión. {error}")
        return
    for side in ("front", "back"):
        st.session_state.pop(f"_doc_{side}_{pid}", None)
    flash("Profesional aprobado." if decision == "approve" else "Profesional rechazado.",
          "success" if decision == "approve" else "warning")
    st.rerun()


def admin_users(user):
    """Cambiar el estado de una cuenta (POST /auth/admin/accounts/{id}/status/) con motivo."""
    section("👥 Estado de cuentas")
    st.info(
        "El backend todavía no entrega el listado de usuarios. Escribe el **id del usuario** "
        "(lo ves en `/admin/` → Users) para cambiar el estado de su cuenta."
    )

    with st.form("account_status_form", clear_on_submit=True):
        uid = st.number_input("Id del usuario", min_value=1, step=1, value=None, key="account_user_id")
        status = st.selectbox(
            "Nuevo estado",
            list(api_client.ESTADOS_CUENTA),
            format_func=lambda s: api_client.ESTADOS_CUENTA[s],
            key="account_status",
        )
        reason = st.text_area(
            "Motivo",
            max_chars=MAX_TEXTO,
            placeholder="Se registra en la bitácora del backend y se le notifica al usuario.",
            key="account_reason",
        )
        sent = st.form_submit_button("Cambiar estado", type="primary")

    if not sent:
        return
    if not uid:
        st.warning("Escribe el id del usuario.")
    elif not reason.strip():
        st.warning("Escribe el motivo.")
    elif int(uid) == user["id"]:
        st.warning("No puedes cambiar el estado de tu propia cuenta.")
    else:
        try:
            result = api_client.set_account_status(int(uid), status, reason)
        except api_client.ApiError as error:
            st.error(f"No se pudo cambiar el estado. {error}")
            return
        flash(f"Cuenta #{result.get('id', uid)}: {api_client.ESTADOS_CUENTA.get(result.get('account_status'), status)}.")
        st.rerun()

    st.caption(
        "Ojo: hoy una cuenta **suspendida** puede seguir usando una sesión ya abierta hasta que venza; "
        "**desactivada** corta la sesión de inmediato (pedido al backend)."
    )


def admin_claims(user):
    """Reclamos de posventa (GET /api/claims/: todos) y resolución con mediación."""
    section("🛠️ Reclamos y mediación")

    try:
        claims = requests_api.list_claims()
    except api_client.ApiError as error:
        st.error(f"No se pudieron cargar los reclamos. {error}")
        return

    if not claims:
        empty_state("🛠️", "No existen reclamos", "Aquí aparecerán los reclamos de posventa de los clientes.")
        return

    for claim in claims:
        cid = claim["id"]
        with st.container(border=True):
            st.markdown(f"### Reclamo #{cid}")
            status_badge(claim["status"])
            st.caption(f"Solicitud #{claim['visit']} · abierto el {claim['created_at']}")
            st.write(f"**Motivo:** {claim['description']}")
            if claim["professional_response"]:
                st.write(f"**Respuesta del profesional:** {claim['professional_response']}")
            if claim["admin_resolution"]:
                st.write(f"**Resolución:** {claim['admin_resolution']}")

            if claim["raw_status"] != "RESOLVED":
                resolution = st.text_area(
                    "Resolución / mediación",
                    max_chars=MAX_TEXTO,
                    key=f"claim_resolution_{cid}",
                )
                if st.button("Resolver reclamo", key=f"save_claim_{cid}"):
                    if not resolution.strip():
                        st.warning("Escribe la resolución.")
                        continue
                    try:
                        requests_api.claim_action(cid, "resolve", resolution=resolution.strip())
                    except api_client.ApiError as error:
                        st.error(f"No se pudo resolver el reclamo. {error}")
                        continue
                    flash(f"Reclamo #{cid} resuelto.")
                    st.rerun()


def admin_support(user):
    """Bandeja de soporte (GET /api/tickets/?status=) y respuesta (POST .../resolve/)."""
    section("💬 Bandeja de soporte")

    labels = {"Abiertos": "OPEN", "En revisión": "IN_REVIEW", "Resueltos": "RESOLVED", "Todos": None}
    chosen = st.radio("Mostrar", list(labels), horizontal=True, key="support_filter")

    try:
        tickets = api_client.list_tickets(labels[chosen])
    except api_client.ApiError as error:
        st.error(f"No se pudo cargar la bandeja. {error}")
        return

    if not tickets:
        empty_state("💬", "No hay tickets", "Cuando un usuario abra un ticket desde una solicitud, aparecerá aquí.")
        return

    for ticket in tickets:
        tid = ticket["id"]
        with st.container(border=True):
            st.markdown(f"### Ticket #{tid} · {ticket.get('subject', '')}")
            status_badge(api_client.ESTADOS_TICKET.get(ticket.get("status"), ticket.get("status")))
            st.caption(f"Solicitud #{ticket.get('visit')}")
            st.write(ticket.get("description", ""))
            if ticket.get("response"):
                st.write(f"**Respuesta de soporte:** {ticket['response']}")
            if ticket.get("status") != "RESOLVED":
                response = st.text_area("Respuesta al usuario", max_chars=MAX_TEXTO, key=f"support_reply_{tid}")
                if st.button("Responder y resolver", type="primary", key=f"support_resolve_{tid}"):
                    if not response.strip():
                        st.warning("Escribe la respuesta.")
                        continue
                    try:
                        api_client.resolve_ticket(tid, response)
                    except api_client.ApiError as error:
                        st.error(f"No se pudo responder el ticket. {error}")
                        continue
                    flash(f"Ticket #{tid} respondido y resuelto. El usuario recibe una notificación.")
                    st.rerun()
