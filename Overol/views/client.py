"""Vistas del rol Cliente (RF 002, 003, 004, 006, 009) y clasificador del chatbot."""

import sqlite3

import streamlit as st

from core.constants import CATEGORIAS, COMUNAS, ESTADOS_SOLICITUD
from core.database import (
    audit,
    change_request_status,
    get_all_professionals,
    get_claims_for_client,
    get_connection,
    get_professional_rating,
    get_rating_for_request,
    get_requests_for_client,
    now_str,
)
from ui.components import (
    empty_state,
    flash,
    format_professional_card,
    hero,
    section,
    security_note,
    stars,
    status_badge,
)
from views.shared import professional_profile_client, user_profile_page


def sugerir_especialidad(texto):
    texto = texto.lower().strip()

    grupos = {
        "Gasfitería": [
            "agua",
            "fuga",
            "filtración",
            "filtracion",
            "cañería",
            "caneria",
            "tubería",
            "tuberia",
            "llave",
            "lavaplatos",
            "baño",
            "wc",
            "inodoro",
            "desagüe",
            "desague",
        ],
        "Electricidad": [
            "luz",
            "enchufe",
            "corriente",
            "cable",
            "eléctrico",
            "electrico",
            "electricidad",
            "interruptor",
            "automático",
            "automatico",
        ],
        "Carpintería": [
            "mueble",
            "madera",
            "puerta",
            "mesa",
            "silla",
            "closet",
            "clóset",
            "estante",
        ],
        "Pintura": [
            "pintar",
            "pintura",
            "pared",
            "techo",
            "color",
            "mancha",
            "pintado",
        ],
    }

    for specialty, words in grupos.items():
        if any(word in texto for word in words):
            return specialty

    return "Maestro multipropósito"


def client_dashboard(user):
    hero(
        "Encuentra al profesional que necesitas para tu hogar",
        "Busca por especialidad y ubicación, revisa perfiles verificados, "
        "solicita una visita y evalúa el servicio.",
    )

    menu = st.radio(
        "Navegación",
        [
            "🏠 Inicio",
            "🔎 Buscar profesionales",
            "🤖 Asistente",
            "📋 Mis solicitudes",
            "⭐ Mis evaluaciones",
            "🛠️ Mis reclamos",
            "👤 Mi perfil",
        ],
        horizontal=True,
        key="client_navigation",
    )

    # Al cambiar de sección se descarta el perfil abierto, para que no
    # "aparezca" solo en otra pantalla.
    if st.session_state.get("_client_prev_menu") != menu:
        st.session_state.pop("selected_professional", None)
        st.session_state["_client_prev_menu"] = menu

    if menu == "🏠 Inicio":
        client_home()

    elif menu == "🔎 Buscar profesionales":
        client_search(user)

    elif menu == "🤖 Asistente":
        client_chatbot(user)

    elif menu == "📋 Mis solicitudes":
        client_requests(user)

    elif menu == "⭐ Mis evaluaciones":
        client_ratings(user)

    elif menu == "🛠️ Mis reclamos":
        client_claims(user)

    elif menu == "👤 Mi perfil":
        user_profile_page(user)


def client_home():
    section("¿Cómo funciona Overol?")

    cols = st.columns(4)

    steps = [
        ("1", "Describe tu necesidad", "Busca por especialidad o utiliza el asistente."),
        ("2", "Compara profesionales", "Revisa experiencia, certificaciones y reputación."),
        ("3", "Solicita el servicio", "Envía una solicitud de visita al profesional."),
        ("4", "Evalúa", "Luego del servicio puedes evaluar la experiencia."),
    ]

    for col, (number, title, description) in zip(cols, steps):
        with col:
            st.markdown(
                f"""<div class="card"><div class="step-number">{number}</div><h3>{title}</h3><div class="muted">{description}</div></div>""",
                unsafe_allow_html=True,
            )

    section("🧰 Especialidades")

    cols = st.columns(4)

    for col, (icon, title, description) in zip(cols, CATEGORIAS):
        with col:
            st.markdown(
                f"""<div class="card"><div style="font-size:32px;">{icon}</div><h3>{title}</h3><div class="muted">{description}</div></div>""",
                unsafe_allow_html=True,
            )

    section("🔐 Privacidad")

    security_note(
        "La plataforma debe separar la información pública de la información privada. "
        "Datos sensibles como RUT, documentos de identidad y dirección exacta "
        "no deben exponerse innecesariamente."
    )


def _show_selected_profile(user):
    """Si hay un profesional seleccionado, muestra su perfil con botón de volver.
    Devuelve True cuando mostró el perfil (el llamador debe terminar su render)."""
    selected = st.session_state.get("selected_professional")

    if not selected:
        return False

    if st.button("← Volver", key="back_from_profile"):
        st.session_state.pop("selected_professional", None)
        st.rerun()

    professional_profile_client(user["id"], selected)
    return True


def _professional_grid(professionals, key_prefix):
    """Muestra tarjetas en 3 columnas con botón «Ver perfil»."""
    cols = st.columns(3)

    for i, professional in enumerate(professionals):
        with cols[i % 3]:
            format_professional_card(professional)

            if st.button(
                "Ver perfil y solicitar visita",
                key=f"{key_prefix}_{professional['id']}",
                use_container_width=True,
            ):
                st.session_state.selected_professional = professional["id"]
                st.rerun()


def client_search(user):
    if _show_selected_profile(user):
        return

    section("🔎 Buscar profesionales")

    c1, c2, c3 = st.columns(3)

    with c1:
        specialty = st.selectbox(
            "Especialidad",
            ["Todas"] + [x[1] for x in CATEGORIAS] + ["Maestro multipropósito"],
            key="search_specialty",
        )

    with c2:
        commune = st.selectbox(
            "Comuna",
            ["Todas"] + COMUNAS,
            key="search_commune",
        )

    with c3:
        order = st.selectbox(
            "Ordenar por",
            ["Mejor evaluados", "Nombre"],
            key="search_order",
        )

    professionals = get_all_professionals(
        specialty=specialty,
        commune=commune,
    )

    if order == "Mejor evaluados":
        professionals = sorted(
            professionals,
            key=lambda p: get_professional_rating(p["id"])[1],
            reverse=True,
        )

    # Se registra la búsqueda solo cuando cambian los filtros (no en cada rerun).
    signature = (specialty, commune)
    if st.session_state.get("_last_search_signature") != signature:
        st.session_state["_last_search_signature"] = signature
        audit(
            user["id"],
            "SEARCH",
            "professionals",
            None,
            f"Especialidad={specialty}; Comuna={commune}",
        )

    st.write(f"**{len(professionals)} profesionales disponibles**")

    if not professionals:
        empty_state(
            "🔍",
            "No encontramos profesionales con esos filtros",
            "Prueba ampliando la comuna o cambiando la especialidad.",
        )
        return

    _professional_grid(professionals, "client_view_prof")


def client_chatbot(user):
    if _show_selected_profile(user):
        return

    section("🤖 Asistente de Overol")

    st.markdown(
        """<div class="warning-box"><b>Diagnóstico inicial</b><br>Describe el problema de tu hogar. El asistente identificará una especialidad sugerida y te permitirá revisar profesionales relacionados.</div>""",
        unsafe_allow_html=True,
    )

    problem = st.text_area(
        "¿Qué problema tienes?",
        placeholder=(
            "Ej: Tengo una fuga de agua debajo del lavaplatos "
            "y necesito repararla."
        ),
        key="chat_problem",
    )

    if st.button(
        "Analizar problema",
        use_container_width=True,
        type="primary",
        key="chat_analyze",
    ):
        if not problem.strip():
            st.warning("Describe el problema primero.")
        else:
            suggestion = sugerir_especialidad(problem)
            # Se guarda el resultado para que sobreviva al pulsar «Ver perfil».
            st.session_state.chat_suggestion = suggestion

            audit(
                user["id"],
                "CHATBOT_DIAGNOSIS",
                "chatbot",
                None,
                f"Sugerencia={suggestion}",
            )

    suggestion = st.session_state.get("chat_suggestion")

    if suggestion:
        st.success(f"Especialidad sugerida: **{suggestion}**")

        professionals = get_all_professionals(
            specialty=suggestion,
            commune="Todas",
        )

        if professionals:
            st.markdown("### Profesionales relacionados")
            _professional_grid(professionals, "chat_prof")
        else:
            empty_state(
                "🛠️",
                "Sin profesionales disponibles",
                "No hay profesionales para esa especialidad en este momento.",
            )

    st.caption(
        "Nota: el chatbot actual es una simulación basada en palabras clave. "
        "La documentación contempla reemplazarlo posteriormente por una IA real."
    )


def client_requests(user):
    section("📋 Mis solicitudes")

    requests = get_requests_for_client(user["id"])

    if not requests:
        empty_state(
            "📋",
            "Todavía no tienes solicitudes",
            "Busca un profesional y envía tu primera solicitud de visita.",
        )
        return

    claimed_requests = {
        claim["request_id"]: claim["id"]
        for claim in get_claims_for_client(user["id"])
    }

    status_filter = st.selectbox(
        "Filtrar por estado",
        ["Todas"] + ESTADOS_SOLICITUD,
        key="client_requests_filter",
    )

    shown = [
        r for r in requests
        if status_filter == "Todas" or r["status"] == status_filter
    ]

    if not shown:
        st.info("No hay solicitudes con ese estado.")

    for request in shown:
        rid = request["id"]

        with st.container(border=True):
            top = st.columns([4, 1])

            with top[0]:
                st.markdown(f"### Solicitud #{rid} · {request['professional_name']}")

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

            # ---------- Pendiente: se puede cancelar ----------
            if request["status"] == "Pendiente":
                if st.button("Cancelar solicitud", key=f"cancel_{rid}"):
                    if change_request_status(
                        rid, "Cancelada", ["Pendiente"], client_id=user["id"]
                    ):
                        audit(user["id"], "UPDATE", "requests", rid,
                              "Solicitud cancelada por cliente")
                        flash("Solicitud cancelada.")
                    else:
                        flash("La solicitud ya cambió de estado.", "warning")
                    st.rerun()

            # ---------- Aceptada: se puede completar ----------
            if request["status"] == "Aceptada":
                st.info(
                    "El profesional aceptó la solicitud. "
                    "Ambas partes pueden coordinar los detalles del servicio."
                )

                if st.button(
                    "Marcar servicio como completado",
                    type="primary",
                    key=f"complete_{rid}",
                ):
                    if change_request_status(
                        rid, "Completada", ["Aceptada"], client_id=user["id"]
                    ):
                        audit(user["id"], "UPDATE", "requests", rid,
                              "Servicio marcado como completado")
                        flash("Servicio marcado como completado. ¡Ya puedes evaluarlo!")
                    else:
                        flash("La solicitud ya cambió de estado.", "warning")
                    st.rerun()

            # ---------- Completada: evaluar y posventa ----------
            if request["status"] == "Completada":
                _rating_block(user, request)
                _claim_block(user, request, claimed_requests.get(rid))


def _rating_block(user, request):
    rid = request["id"]
    rating = get_rating_for_request(rid)

    if rating:
        average = round(
            (rating["quality"] + rating["punctuality"] + rating["treatment"]) / 3, 1
        )
        st.success(f"✓ Servicio evaluado · {stars(average)} {average}")
        return

    st.markdown("#### ⭐ Evaluar servicio")

    s1, s2, s3 = st.columns(3)
    quality = s1.slider("Calidad", 1, 5, 5, key=f"quality_{rid}")
    punctuality = s2.slider("Puntualidad", 1, 5, 5, key=f"punctuality_{rid}")
    treatment = s3.slider("Trato", 1, 5, 5, key=f"treatment_{rid}")

    comment = st.text_area("Comentario (opcional)", key=f"rating_comment_{rid}")

    if st.button("Publicar evaluación", type="primary", key=f"save_rating_{rid}"):
        conn = get_connection()

        try:
            cur = conn.execute(
                """
                INSERT INTO ratings
                (request_id, client_id, professional_id, quality,
                 punctuality, treatment, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    user["id"],
                    request["professional_id"],
                    quality,
                    punctuality,
                    treatment,
                    comment.strip(),
                    now_str(),
                ),
            )
            rating_id = cur.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            flash("Este servicio ya fue evaluado.", "warning")
            st.rerun()
        finally:
            conn.close()

        audit(user["id"], "CREATE", "ratings", rating_id,
              f"Evaluación de solicitud {rid}")
        flash("Evaluación registrada. ¡Gracias por tu opinión!")
        st.rerun()


def _claim_block(user, request, existing_claim_id):
    """Posventa: disponible en servicios completados, hayan sido evaluados o no."""
    rid = request["id"]

    if existing_claim_id:
        st.info(
            f"🛠️ Ya registraste el reclamo #{existing_claim_id} para este servicio. "
            "Puedes seguirlo en «Mis reclamos»."
        )
        return

    with st.expander("🛠️ ¿Hubo un problema? Abrir un reclamo de posventa"):
        reason = st.text_area("Describe el problema", key=f"claim_reason_{rid}")

        if st.button("Enviar reclamo", key=f"send_claim_{rid}"):
            if not reason.strip():
                st.warning("Debes describir el problema.")
                return

            conn = get_connection()
            cur = conn.execute(
                """
                INSERT INTO claims
                (request_id, client_id, professional_id, reason,
                 status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Abierto', ?, ?)
                """,
                (
                    rid,
                    user["id"],
                    request["professional_id"],
                    reason.strip(),
                    now_str(),
                    now_str(),
                ),
            )
            claim_id = cur.lastrowid
            conn.commit()
            conn.close()

            audit(user["id"], "CREATE", "claims", claim_id,
                  f"Reclamo de solicitud {rid}")
            flash("Reclamo enviado. El profesional será notificado.")
            st.rerun()


def client_ratings(user):
    section("⭐ Mis evaluaciones")

    conn = get_connection()
    ratings = conn.execute(
        """
        SELECT
            r.*,
            u.name AS professional_name
        FROM ratings r
        JOIN professionals p ON p.id = r.professional_id
        JOIN users u ON u.id = p.user_id
        WHERE r.client_id = ?
        ORDER BY r.id DESC
        """,
        (user["id"],),
    ).fetchall()
    conn.close()

    if not ratings:
        empty_state(
            "⭐",
            "Todavía no has publicado evaluaciones",
            "Cuando completes un servicio podrás evaluarlo desde «Mis solicitudes».",
        )
        return

    for rating in ratings:
        with st.container(border=True):
            average = round(
                (rating["quality"] + rating["punctuality"] + rating["treatment"]) / 3,
                1,
            )

            st.markdown(f"### {rating['professional_name']}")
            st.markdown(f"**{stars(average)}  {average}**")

            m1, m2, m3 = st.columns(3)
            m1.metric("Calidad", f"{rating['quality']}/5")
            m2.metric("Puntualidad", f"{rating['punctuality']}/5")
            m3.metric("Trato", f"{rating['treatment']}/5")

            st.write(rating["comment"] or "Sin comentario.")


def client_claims(user):
    section("🛠️ Mis reclamos")

    claims = get_claims_for_client(user["id"])

    if not claims:
        empty_state("🛠️", "No tienes reclamos registrados", "Si un servicio no salió bien, puedes abrir un reclamo desde «Mis solicitudes».")
        return

    for claim in claims:
        with st.container(border=True):
            status_badge(claim["status"])
            st.markdown(
                f"### Reclamo #{claim['id']}"
            )
            st.write(
                f"**Profesional:** {claim['professional_name']}"
            )
            st.write(
                f"**Motivo:** {claim['reason']}"
            )

            if claim["response"]:
                st.write(
                    f"**Respuesta del profesional:** {claim['response']}"
                )
