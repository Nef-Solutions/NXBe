"""Tickets de soporte: el cliente y el profesional abren un ticket con asunto sobre su
solicitud, el admin responde, resuelve y reabre; escribir en un ticket resuelto lo reabre;
límites de 100 y 500 caracteres y solo participantes."""

from comun import check, md, new_app, next_valid_slot, preparar, reset_pending, terminar, usuarios

front = preparar()
U = usuarios(front)

from core import database as db  # noqa: E402

CLIENT, PRO_USER, ADMIN = U["cliente"], U["carlos"], U["admin"]
PID = db.get_professional_by_user(PRO_USER)["id"]
reset_pending(db, CLIENT, PID)
ok, rid = db.create_request(CLIENT, PID, db.get_trades(PID)[0]["trade"], "", "Santiago",
                            *next_valid_slot(db, PID), "Prueba de tickets")
assert ok, rid


def ticket(user_id):
    return db.get_support_ticket(rid, user_id)


def last_title(user_id):
    return db.get_notifications(user_id)[0]["title"]


def client_requests():
    at = new_app(front, CLIENT)
    at.button(key="client_navigation_btn_2").click().run()
    return at


# ---------- Validaciones ----------
check(db.add_support_message(rid, CLIENT, "Hola", subject="")[1] == "Escribe el asunto del ticket.",
      "el primer mensaje exige asunto")
check("100" in db.add_support_message(rid, CLIENT, "Hola", subject="x" * 101)[1], "asunto máx. 100 caracteres")
check("500" in db.add_support_message(rid, CLIENT, "x" * 501, subject="Asunto")[1], "mensaje máx. 500 caracteres")
check(db.add_support_message(rid, U["daniel"], "Hola", subject="Ajeno")[1] == "No participas en esta solicitud.",
      "solo los participantes de la solicitud pueden abrir un ticket")
check(db.add_support_message(rid, CLIENT, "Hola", from_admin=True)[1] == "Ese ticket no existe.",
      "el admin no puede crear tickets, solo responder")
check(ticket(CLIENT) is None, "ninguna validación fallida crea el ticket")

# ---------- El cliente abre el ticket desde «Mis solicitudes» ----------
at = client_requests()
at.text_input(key=f"support_subject_cliente_{rid}").input("El profesional no llegó")
at.text_area(key=f"support_text_cliente_{rid}").input("Lo esperé toda la mañana <b>")
at.button(key=f"support_send_cliente_{rid}").click().run()
check(not at.exception and ticket(CLIENT)["status"] == "Abierto" and ticket(CLIENT)["subject"] == "El profesional no llegó",
      "[cliente] abre el ticket con asunto")
check(not any(t.key == f"support_subject_cliente_{rid}" for t in at.text_input),
      "[cliente] con el ticket abierto ya no se pide asunto")

# ---------- El profesional abre su propio ticket sobre la misma solicitud ----------
at = new_app(front, PRO_USER)
at.text_input(key=f"support_subject_profesional_{rid}").input("Dirección incompleta")
at.text_area(key=f"support_text_profesional_{rid}").input("Falta el número de depto.")
at.button(key=f"support_send_profesional_{rid}").click().run()
check(not at.exception and ticket(PRO_USER)["status"] == "Abierto" and ticket(CLIENT)["id"] != ticket(PRO_USER)["id"],
      "[profesional] abre un ticket separado del cliente")

# ---------- Admin: bandeja, responder, resolver ----------
at = new_app(front, ADMIN)
at.button(key="admin_navigation_btn_7").click().run()
page = md(at)
check(not at.exception and "&lt;b&gt;" in page and "<b>\n" not in page, "[admin] ve los tickets con el texto escapado")
check(any(f"support_read_{rid}_{CLIENT}" == b.key for b in at.button), "[admin] el ticket aparece con mensajes sin leer")
at.text_area(key=f"support_reply_text_{rid}_{CLIENT}").input("Lo llamaremos hoy.")
at.button(key=f"support_reply_send_{rid}_{CLIENT}").click().run()
check(last_title(CLIENT) == "Respuesta de soporte" and not any(f"support_read_{rid}_{CLIENT}" == b.key for b in at.button),
      "[admin] responde, notifica al cliente y el hilo queda leído")
at.button(key=f"support_resolve_{rid}_{CLIENT}").click().run()
check(ticket(CLIENT)["status"] == "Resuelto" and last_title(CLIENT) == "Ticket resuelto",
      "[admin] resuelve el ticket y notifica")
at.radio(key="support_filter").set_value("Resueltos").run()
check(any(b.key == f"support_reopen_{rid}_{CLIENT}" for b in at.button)
      and not any(b.key == f"support_resolve_{rid}_{PRO_USER}" for b in at.button),
      "[admin] filtro «Resueltos» muestra solo los resueltos")
at.button(key=f"support_reopen_{rid}_{CLIENT}").click().run()
check(ticket(CLIENT)["status"] == "Abierto", "[admin] reabre el ticket")
db.set_support_ticket_status(rid, CLIENT, "Resuelto")

# ---------- El cliente escribe en un ticket resuelto: se reabre ----------
at = client_requests()
check("Lo llamaremos hoy." in md(at), "[cliente] ve la respuesta de soporte en su solicitud")
at.text_area(key=f"support_text_cliente_{rid}").input("No me han llamado")
at.button(key=f"support_send_cliente_{rid}").click().run()
check(ticket(CLIENT)["status"] == "Abierto" and len(db.get_support_thread(rid, CLIENT)) == 3,
      "[cliente] escribir en un ticket resuelto lo reabre")

terminar()
