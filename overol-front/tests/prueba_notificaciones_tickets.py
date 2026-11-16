"""Etapa E: notificaciones (GET /notifications/, marcar una o todas, contador, escape, cada uno
las suyas) y tickets de soporte por solicitud (GET/POST /tickets/ y la respuesta del admin). Al abrir
un ticket, el cliente pasa a «Mis reclamos», donde ve sus tickets con la solicitud de origen, sea la
solicitud aceptada, rechazada o vencida."""

from comun import backend, calls, check, errors, md, new_app, preparar, terminar, texts, toasts

front = preparar()

CLIENTE, PRO = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl"
CID = backend.by_email(CLIENTE)["id"]


def label(at, nav, name):
    return next((b.label.replace(" ", " ") for b in at.button
                 if (b.key or "").startswith(f"side_{nav}_btn_") and name in b.label), "")


def notifications(email, nav):
    return new_app(front, email, **{nav: "🔔 Notificaciones"})


# ---------- Una acción del profesional notifica al cliente ----------
VID = backend.add_visit(CLIENTE, PRO)
at = new_app(front, PRO, professional_navigation="📋 Solicitudes")
at.button(key=f"pro_accept_{VID}").click().run()
at = notifications(CLIENTE, "client_navigation")
check(label(at, "client_navigation", "Notificaciones") == "🔔 Notificaciones (1)", "el menú lateral del cliente muestra 1 no leída")
check(not at.exception and "Solicitud aceptada" in md(at) and "Nueva" in md(at) and f"Solicitud #{VID}" in md(at),
      "la notificación aparece como nueva, con la solicitud")
nid = backend.notifications[-1]["id"]
at.button(key=f"notif_read_{nid}").click().run()
check(calls("POST", f"/notifications/{nid}/read/") and backend.notifications[-1]["is_read"]
      and label(at, "client_navigation", "Notificaciones") == "🔔 Notificaciones", "marcar una (POST .../read/) y el contador baja")

# ---------- Marcar todas ----------
backend.notifications_add(CID, "Aviso uno", "Primero")
backend.notifications_add(CID, "<script>alert(1)</script>", "Segundo <b>texto</b>")
at = notifications(CLIENTE, "client_navigation")
check("&lt;script&gt;" in md(at) and "<script>alert" not in md(at), "el contenido de la notificación se escapa")
at.button(key="notif_read_all").click().run()
check(all(n["is_read"] for n in backend.notifications if n["recipient"] == CID)
      and not any(b.key == "notif_read_all" for b in at.button), "«Marcar todas» las marca una por una")

# ---------- Cada uno ve las suyas ----------
at = notifications(PRO, "professional_navigation")
check("Aviso uno" not in md(at), "el profesional no ve las notificaciones del cliente")

# ---------- Tickets de soporte ----------
at = new_app(front, CLIENTE, client_navigation="📋 Mis solicitudes")
send = next(b for b in at.button if b.key == f"support_send_cliente_{VID}")
send.click().run()
check("Escribe un asunto" in errors(at) and not calls("POST", "/tickets/"), "el ticket exige asunto")
at.text_input(key=f"support_subject_cliente_{VID}").input("El profesional no llegó")
at.text_area(key=f"support_text_cliente_{VID}").input("Lo esperé toda la mañana")
next(b for b in at.button if b.key == f"support_send_cliente_{VID}").click().run()
ticket = backend.tickets[max(backend.tickets)]
check(ticket["visit"] == VID and ticket["user"] == CID and ticket["status"] == "OPEN"
      and f"Ticket #{ticket['id']} enviado a soporte" in toasts(at), "abre el ticket (POST /tickets/)")
at = new_app(front, CLIENTE, client_navigation="📋 Mis solicitudes")
check("El profesional no llegó" in md(at) and "Lo esperé toda la mañana" in md(at) and "Abierto" in md(at),
      "el ticket aparece en la solicitud")

at = new_app(front, PRO, professional_navigation="📋 Solicitudes")
check("El profesional no llegó" not in md(at), "el profesional no ve el ticket del cliente")
at.text_input(key=f"support_subject_profesional_{VID}").input("Dirección incorrecta")
at.text_area(key=f"support_text_profesional_{VID}").input("La dirección no existe")
next(b for b in at.button if b.key == f"support_send_profesional_{VID}").click().run()
check(backend.tickets[max(backend.tickets)]["user"] == backend.by_email(PRO)["id"], "el profesional abre su propio ticket")

# ---------- Tras abrir el ticket, el cliente va a «Mis reclamos» (aceptada, rechazada y vencida) ----------
NAV = "client_navigation"


def marked(at):
    """Sección destacada (primary) en el menú lateral (no hay barra superior)."""
    return [b.label for b in at.sidebar.button if (b.key or "").startswith(f"side_{NAV}_btn_") and b.proto.type == "primary"]


for state, name in [("ACCEPTED", "aceptada"), ("REJECTED", "rechazada"), ("EXPIRED", "vencida")]:
    vid = backend.add_visit(CLIENTE, PRO, status=state)
    at = new_app(front, CLIENTE, client_navigation="📋 Mis solicitudes")
    subject = f"Consulta por la solicitud {name}"
    at.text_input(key=f"support_subject_cliente_{vid}").input(subject)
    at.text_area(key=f"support_text_cliente_{vid}").input(f"Necesito ayuda con la solicitud {name}")
    next(b for b in at.button if b.key == f"support_send_cliente_{vid}").click().run()
    created = backend.tickets[max(backend.tickets)]
    check(not at.exception and created["visit"] == vid and created["subject"] == subject,
          f"[{name}] crea el ticket asociado a la solicitud #{vid} (POST /tickets/)")
    check(at.session_state[NAV] == "🛠️ Mis reclamos" and marked(at) == ["🛠️ Mis reclamos"],
          f"[{name}] pasa a «Mis reclamos», marcada en el menú lateral")
    check(at.session_state[f"_nav_shown_{NAV}"][0] == "🛠️ Mis reclamos",
          f"[{name}] cuenta como cambio de sección (la página vuelve arriba)")
    check(f"Ticket #{created['id']} enviado a soporte (solicitud #{vid})" in toasts(at),
          f"[{name}] aviso corto de éxito con el ticket y la solicitud")
    check(subject in md(at) and "recién enviado" in md(at) and f"Solicitud #{vid}" in texts(at),
          f"[{name}] el ticket aparece en «Mis reclamos», destacado y con su solicitud de origen")
    at.button(key=f"ticket_to_request_{created['id']}").click().run()
    check(at.session_state[NAV] == "📋 Mis solicitudes" and marked(at) == ["📋 Mis solicitudes"],
          f"[{name}] «Ver solicitud» vuelve a «Mis solicitudes»")

at = new_app(front, CLIENTE, client_navigation="🛠️ Mis reclamos")
check(not at.exception and "recién enviado" not in md(at) and "Tickets de soporte" in md(at),
      "al volver a «Mis reclamos», los tickets siguen ahí sin la marca de recién enviado")
pro_vid = backend.add_visit(CLIENTE, PRO, status="ACCEPTED")
at = new_app(front, PRO, professional_navigation="📋 Solicitudes")
at.text_input(key=f"support_subject_profesional_{pro_vid}").input("Consulta del profesional")
at.text_area(key=f"support_text_profesional_{pro_vid}").input("Detalle")
next(b for b in at.button if b.key == f"support_send_profesional_{pro_vid}").click().run()
check(at.session_state["professional_navigation"] == "📋 Solicitudes" and "abierto. Soporte te responderá" in toasts(at),
      "el profesional se queda en «Solicitudes» con su aviso de siempre (su flujo no cambia)")

# ---------- El admin responde (en esta etapa, desde la API) ----------
admin = backend.by_email("admin@demo.overol.cl")
backend._resolve_ticket(admin, ticket["id"], {"response": "Hablamos con el profesional, reagendamos"})
at = new_app(front, CLIENTE, client_navigation="📋 Mis solicitudes")
check("Soporte Overol" in md(at) and "reagendamos" in md(at) and "Resuelto" in md(at), "el cliente ve la respuesta de soporte")
check(label(at, "client_navigation", "Notificaciones") == "🔔 Notificaciones (1)", "y le llega la notificación «Ticket resuelto»")

terminar()
