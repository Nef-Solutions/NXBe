"""Verificación: hilo de mensajes profesional ↔ admin (máx. 500) y decisión
con motivo, que queda en el hilo, en la bitácora y en la notificación."""

from comun import check, md, new_app as _new_app, preparar, terminar, usuarios

front = preparar()
U = usuarios(front)
ADMIN, CLIENT, PRO_USER = U["admin"], U["cliente"], U["carlos"]


def new_app(user_id):
    return _new_app(front, user_id)


at = new_app(ADMIN)
from core import database as db  # noqa: E402

PID = db.get_professional_by_user(PRO_USER)["id"]


def set_pending():
    conn = db.get_connection()
    conn.execute("UPDATE professionals SET verified = 0, verification_status = 'Pendiente' WHERE id = ?", (PID,))
    conn.commit()
    conn.close()


def pro():
    return db.get_professional_by_user(PRO_USER)


set_pending()
conn = db.get_connection()
check("verification_reason" in [r["name"] for r in conn.execute("PRAGMA table_info(professionals)")]
      and conn.execute("SELECT name FROM sqlite_master WHERE name = 'verification_messages'").fetchone(),
      "migración: tabla verification_messages y columna verification_reason")
conn.close()


def open_pro_verification():
    at = new_app(PRO_USER)
    at.button(key="professional_navigation_btn_2").click().run()
    return at


def open_admin_verification():
    at = new_app(ADMIN)
    at.button(key="admin_navigation_btn_1").click().run()
    return at


# ---------- El profesional escribe ----------
at = open_pro_verification()
check(not at.exception and at.text_area(key=f"verif_msg_text_{PID}").proto.max_chars == 500,
      "[profesional] la pestaña Verificación tiene el hilo (máx. 500)")
at.button(key=f"verif_msg_send_{PID}").click().run()
check(any("Escribe un mensaje" in e.value for e in at.error) and not db.get_verification_messages(PID),
      "[profesional] mensaje vacío → error")
at.text_area(key=f"verif_msg_text_{PID}").input("Subí mi <b>cédula</b>, ¿falta algo?")
at.button(key=f"verif_msg_send_{PID}").click().run()
msgs = db.get_verification_messages(PID)
check(not at.exception and len(msgs) == 1 and not msgs[0]["from_admin"] and msgs[0]["read_by_admin"] == 0,
      "[profesional] envía el mensaje al admin")
check("Subí mi &lt;b&gt;cédula&lt;/b&gt;" in md(at), "[profesional] su mensaje se ve escapado")

# ---------- El admin ve el aviso, lee y responde ----------
at = new_app(ADMIN)
check(at.button(key="admin_navigation_btn_1").label == "🪪 Verificación (1)",
      "[admin] la barra avisa 1 mensaje de verificación sin leer")
at.button(key="admin_navigation_btn_1").click().run()
labels = [e.label for e in at.expander]
check(not at.exception and "💬 Mensajes de verificación (1) · 🔴 1 sin leer" in labels, "[admin] el hilo muestra el no leído")
check("&lt;b&gt;cédula&lt;/b&gt;" in md(at), "[admin] el mensaje del profesional va escapado")
at.text_area(key=f"verif_reply_text_{PID}").input("Falta el reverso de la cédula.")
at.button(key=f"verif_reply_send_{PID}").click().run()
n = db.get_notifications(PRO_USER)[0]
check(not at.exception and db.count_unread_verification_messages() == 0 and n["title"] == "Mensaje sobre tu verificación",
      "[admin] responder marca como leído y notifica al profesional")
check(at.button(key="admin_navigation_btn_1").label == "🪪 Verificación", "[admin] la barra ya no muestra contador")

# ---------- Decisión: sin motivo, rechazo con motivo ----------
at = open_admin_verification()
check(at.text_area(key=f"verif_reason_{PID}").proto.max_chars == 500, "[admin] motivo de la decisión con máx. 500")
at.button(key=f"admin_reject_{PID}").click().run()
check(any("motivo" in e.value for e in at.error) and pro()["verification_status"] == "Pendiente",
      "[admin] rechazar sin motivo → error, sigue Pendiente")
at.text_area(key=f"verif_reason_{PID}").input("La foto de la cédula está borrosa")
at.button(key=f"admin_reject_{PID}").click().run()
p = pro()
check(not at.exception and p["verification_status"] == "Rechazado" and p["verified"] == 0
      and p["verification_reason"] == "La foto de la cédula está borrosa", "[admin] rechazar con motivo guarda estado y motivo")
n = db.get_notifications(PRO_USER)[0]
check(n["title"] == "Verificación rechazada" and "Motivo: La foto de la cédula está borrosa" in n["message"],
      "[admin] el profesional recibe la notificación con el motivo")
check(db.get_verification_messages(PID)[-1]["body"] == "✕ Verificación rechazada. Motivo: La foto de la cédula está borrosa",
      "[admin] la decisión queda en el hilo")
log, _ = db.get_audit_log(action="VERIFY_REJECT", limit=1)
check(log and log[0]["user_id"] == ADMIN and log[0]["entity_id"] == PID and "borrosa" in log[0]["details"],
      "[admin] la decisión queda en la bitácora")
at = open_admin_verification()
check(any("Decisión: Rechazado · Motivo: La foto de la cédula está borrosa" in c.value for c in at.caption)
      and not any(b.key == f"admin_approve_{PID}" for b in at.button),
      "[admin] el rechazado sigue visible por su hilo, sin botones de decisión")

# ---------- El profesional ve el motivo y vuelve a escribir ----------
at = open_pro_verification()
check(any("Motivo: La foto de la cédula está borrosa" in e.value for e in at.error), "[profesional] ve el motivo del rechazo")
at.text_area(key=f"verif_msg_text_{PID}").input("Ya subí una foto nítida")
at.button(key=f"verif_msg_send_{PID}").click().run()
check(db.count_unread_verification_messages() == 1, "[profesional] puede seguir escribiendo tras el rechazo")

# ---------- Vuelve a revisión y el admin aprueba con motivo ----------
set_pending()
at = open_admin_verification()
at.text_area(key=f"verif_reason_{PID}").input("Documentos completos y legibles")
at.button(key=f"admin_approve_{PID}").click().run()
p = pro()
n = db.get_notifications(PRO_USER)[0]
check(not at.exception and p["verification_status"] == "Aprobado" and p["verified"] == 1
      and n["title"] == "Verificación aprobada" and "Documentos completos" in n["message"],
      "[admin] aprobar con motivo verifica al profesional y lo notifica")
check(db.count_unread_verification_messages() == 0, "[admin] decidir marca como leídos los mensajes del profesional")

# ---------- Reglas en la base ----------
ok, err = db.decide_verification(ADMIN, PID, False, "otra vez")
check(not ok and "ya fue resuelta" in err and pro()["verification_status"] == "Aprobado", "no se puede decidir dos veces")
ok, err = db.add_verification_message(PID, CLIENT, "intruso")
check(not ok, "otro usuario no puede escribir en el hilo de un profesional")
ok, err = db.add_verification_message(PID, PRO_USER, "x" * 501)
check(not ok and "500" in err, "mensaje de 501 caracteres → error")
ok, err = db.decide_verification(ADMIN, PID, True, "x" * 501)
check(not ok and "500" in err, "motivo de 501 caracteres → error")

terminar()
