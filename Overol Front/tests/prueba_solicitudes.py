"""Solicitudes: creación y reglas (días y horas del profesional, duplicadas), contacto solo
con la solicitud aceptada, rechazo con motivo, finalización de ambas partes, cancelaciones
y vencimiento a las 72 horas."""

from datetime import datetime, timedelta

from comun import check, md, new_app, next_valid_slot, preparar, reset_pending, terminar, texts, usuarios

front = preparar()
U = usuarios(front)

from core import database as db  # noqa: E402

CLIENT, PRO_USER = U["cliente"], U["carlos"]
PID = db.get_professional_by_user(PRO_USER)["id"]
TRADE = db.get_trades(PID)[0]["trade"]
CLIENT_EMAIL, PRO_EMAIL = "cliente@overol.cl", "carlos@overol.cl"


def sql(query, params=()):
    conn = db.get_connection()
    conn.execute(query, params)
    conn.commit()
    conn.close()


def status(rid):
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM requests WHERE id = ?", (rid,)).fetchone()
    conn.close()
    return row


def new_request(description="Prueba de solicitudes"):
    reset_pending(db, CLIENT, PID)
    date, slot = next_valid_slot(db, PID)
    ok, rid = db.create_request(CLIENT, PID, TRADE, "", "Santiago", date, slot, description)
    assert ok, rid
    return rid


def client_page():
    at = new_app(front, CLIENT)
    at.button(key="client_navigation_btn_2").click().run()
    return at


def last_title(user_id):
    items = db.get_notifications(user_id)
    return items[0]["title"] if items else None


# Horario conocido para Carlos: lunes a viernes, 09:00 a 18:00
sql("UPDATE professionals SET work_days = 'Lun,Mar,Mié,Jue,Vie', work_start = '09:00', work_end = '18:00', "
    "verified = 1, verification_status = 'Aprobado', availability = 1 WHERE id = ?", (PID,))
reset_pending(db, CLIENT, PID)

# ---------- Crear desde el perfil (pantalla del cliente) ----------
at = new_app(front, CLIENT)
at.button(key="client_navigation_btn_1").click().run()
at.button(key=f"client_view_prof_{PID}").click().run()
check(not any(s.key == f"request_zone_{PID}" for s in at.selectbox), "[cliente] el formulario no pide zona")
check("Lun, Mar, Mié, Jue, Vie" in texts(at), "[cliente] el formulario muestra los días en que trabaja")
check(all(s.split(" - ")[1] <= "18:00" for s in at.selectbox(key=f"request_time_{PID}").options),
      "[cliente] solo ofrece franjas dentro de su horario")
before = {r["id"] for r in db.get_requests_for_client(CLIENT)}
at.text_area(key=f"request_description_{PID}").input("Gotea la llave del baño").run()
at.button(key=f"send_request_{PID}").click().run()
new = [r for r in db.get_requests_for_client(CLIENT) if r["id"] not in before]
rid = new[0]["id"] if new else None
check(not at.exception and rid and status(rid)["status"] == "Pendiente", "[cliente] crea la solicitud Pendiente")
check(last_title(PRO_USER) == "Nueva solicitud", "[profesional] recibe la notificación «Nueva solicitud»")

# ---------- Duplicada ----------
at.button(key="client_navigation_btn_1").click().run()
at.button(key=f"client_view_prof_{PID}").click().run()
at.text_area(key=f"request_description_{PID}").input("Otra vez").run()
at.button(key=f"send_request_{PID}").click().run()
check(any("pendiente con este profesional" in w.value for w in at.warning),
      "[cliente] no puede tener dos pendientes con el mismo profesional")

# ---------- Reglas de negocio de create_request ----------
date, slot = next_valid_slot(db, PID)
saturday = date + timedelta(days=(5 - date.weekday()) % 7)
cases = [
    ((CLIENT, PID, TRADE, "", "Santiago", saturday, slot, "x"), "no trabaja los Sáb", "día no laboral"),
    ((CLIENT, PID, TRADE, "", "Santiago", date, "17:00 - 19:00", "x"), "atiende entre 09:00 y 18:00", "franja fuera de horario"),
    ((CLIENT, PID, TRADE, "", "Santiago", datetime.today().date() - timedelta(days=1), slot, "x"), "anterior a hoy", "fecha pasada"),
    ((CLIENT, PID, TRADE, "", "Santiago", date, slot, "   "), "descripción", "descripción vacía"),
    ((CLIENT, PID, "Electricidad", "", "Santiago", date, slot, "x"), "no ofrece ese oficio", "oficio que no tiene"),
    ((U["daniel"], PID, TRADE, "", "Santiago", date, slot, "x"), "Solo los clientes", "un profesional no agenda"),
]
reset_pending(db, CLIENT, PID)
for args, expected, name in cases:
    ok, message = db.create_request(*args)
    check(not ok and expected in message, f"[reglas] rechaza {name}")
sql("UPDATE professionals SET verified = 0 WHERE id = ?", (PID,))
ok, message = db.create_request(CLIENT, PID, TRADE, "", "Santiago", date, slot, "x")
check(not ok and "no está disponible" in message, "[reglas] no se agenda con un profesional sin verificar")
sql("UPDATE professionals SET verified = 1 WHERE id = ?", (PID,))

# ---------- Contacto oculto mientras está Pendiente ----------
rid = new_request()
at = client_page()
at.selectbox(key="client_requests_filter").select("Pendiente").run()  # solo las pendientes en pantalla
check("vence el" in texts(at) and PRO_EMAIL not in md(at), "[cliente] pendiente: plazo visible y contacto oculto")
at = new_app(front, PRO_USER)
pending_tab = " ".join(m.value for m in at.tabs[0].markdown)  # pestaña «Pendientes»
check(any(b.key == f"pro_accept_{rid}" for b in at.button) and f"#{rid}" in pending_tab
      and CLIENT_EMAIL not in pending_tab, "[profesional] pendiente: puede aceptar y no ve el contacto del cliente")

# ---------- Rechazo con motivo ----------
at.selectbox(key=f"reject_reason_{rid}").select("Otro").run()
at.button(key=f"pro_reject_{rid}").click().run()
check(status(rid)["status"] == "Pendiente" and any("debes explicar" in w.value for w in at.warning),
      "[profesional] «Otro» sin explicación no rechaza")
at.text_input(key=f"reject_detail_{rid}").input("Estoy de vacaciones")
at.button(key=f"pro_reject_{rid}").click().run()
check(status(rid)["status"] == "Rechazada" and last_title(CLIENT) == "Solicitud rechazada",
      "[profesional] rechaza con motivo y el cliente es notificado")
check("Estoy de vacaciones" in texts(client_page()), "[cliente] ve el motivo del rechazo")

# ---------- Aceptar → contacto visible para ambos ----------
rid = new_request()
at = new_app(front, PRO_USER)
at.button(key=f"pro_accept_{rid}").click().run()
check(status(rid)["status"] == "Aceptada" and last_title(CLIENT) == "Solicitud aceptada",
      "[profesional] acepta y el cliente es notificado")
check(CLIENT_EMAIL in md(at), "[profesional] con la solicitud aceptada ve el contacto del cliente")
check(PRO_EMAIL in md(client_page()), "[cliente] con la solicitud aceptada ve el contacto del profesional")

# ---------- Finalizar: requiere a ambas partes ----------
at = client_page()
at.button(key=f"complete_{rid}").click().run()
check(status(rid)["status"] == "Aceptada" and status(rid)["client_confirmed"] == 1
      and last_title(PRO_USER) == "Confirma el término del servicio",
      "[cliente] su confirmación sola no finaliza y avisa al profesional")
at = new_app(front, PRO_USER)
at.button(key=f"pro_complete_{rid}").click().run()
check(status(rid)["status"] == "Finalizada" and last_title(CLIENT) == "Servicio finalizado",
      "[profesional] con las dos confirmaciones queda Finalizada")
at = client_page()
check(any(s.key == f"quality_{rid}" for s in at.slider) and PRO_EMAIL in md(at),
      "[cliente] finalizada: puede evaluar y sigue viendo el contacto")
at.button(key=f"save_rating_{rid}").click().run()
check(db.get_rating_for_request(rid) is not None, "[cliente] publica la evaluación")

# ---------- El profesional cancela una aceptada con motivo (máx. 500) ----------
rid = new_request()
db.change_request_status(rid, "Aceptada", ["Pendiente"], professional_id=PID)
at = new_app(front, PRO_USER)
at.button(key=f"pro_cancel_{rid}").click().run()
check(status(rid)["status"] == "Aceptada", "[profesional] sin motivo no cancela")
ok, message = db.cancel_request_by_professional(rid, PID, "x" * 501)
check(not ok and "500" in message, "[profesional] el motivo no puede pasar de 500 caracteres")
at.text_area(key=f"pro_cancel_reason_{rid}").input("Se me enfermó un hijo")
at.button(key=f"pro_cancel_{rid}").click().run()
check(status(rid)["status"] == "Cancelada" and status(rid)["cancelled_by"] == "profesional"
      and last_title(CLIENT) == "Solicitud cancelada", "[profesional] cancela con motivo y notifica")
check("Se me enfermó un hijo" in texts(client_page()), "[cliente] ve el motivo de la cancelación")

# ---------- El cliente cancela con advertencia ----------
rid = new_request()
at = client_page()
at.button(key=f"cancel_{rid}").click().run()
check(any("¿Estás seguro" in w.value for w in at.warning) and any(b.key == f"cancel_no_{rid}" for b in at.button),
      "[cliente] «Cancelar» muestra la advertencia y «mantener presionado»")
at.button(key=f"cancel_no_{rid}").click().run()
check(status(rid)["status"] == "Pendiente" and any(b.key == f"cancel_{rid}" for b in at.button),
      "[cliente] «No, mantener mi solicitud» no cancela")
# El botón de mantener presionado es un componente propio que AppTest no puede pulsar
check(db.cancel_request_by_client(rid, CLIENT) and status(rid)["status"] == "Cancelada"
      and last_title(PRO_USER) == "Solicitud cancelada", "[cliente] la cancelación confirmada avisa al profesional")
check(not db.cancel_request_by_client(rid, CLIENT), "[cliente] no se cancela dos veces")

# ---------- Vencimiento a las 72 horas ----------
old = new_request("Vieja")
sql("UPDATE requests SET created_at = ? WHERE id = ?",
    ((datetime.now() - timedelta(hours=73)).strftime("%Y-%m-%d %H:%M:%S"), old))
young = db.create_request(U["cliente"], db.get_professional_by_user(U["daniel"])["id"], "Electricidad", "",
                          "Maipú", *next_valid_slot(db, db.get_professional_by_user(U["daniel"])["id"]), "Nueva")[1]
sql("UPDATE requests SET created_at = ? WHERE id = ?",
    ((datetime.now() - timedelta(hours=71)).strftime("%Y-%m-%d %H:%M:%S"), young))
at = client_page()
check(status(old)["status"] == "Vencida" and status(young)["status"] == "Pendiente",
      "[vencimiento] a las 73 h vence y a las 71 h sigue pendiente")
check(last_title(PRO_USER) == "Solicitud vencida"
      and any(n["title"] == "Solicitud vencida" for n in db.get_notifications(CLIENT)),
      "[vencimiento] avisa al cliente y al profesional")
log, _ = db.get_audit_log(action="EXPIRE")
check(any(r["entity_id"] == old and r["user_id"] is None for r in log), "[vencimiento] queda en la bitácora como acción del sistema")
check("venció" in texts(at), "[cliente] ve por qué venció")

terminar()
