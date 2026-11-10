"""Notificaciones: contador en la barra (cliente y profesional), marcar una o todas como
leídas, cada usuario ve solo las suyas y el texto se muestra escapado."""

from comun import check, keys, md, new_app, plain, preparar, terminar, usuarios

front = preparar()
U = usuarios(front)

from core import database as db  # noqa: E402

CLIENT, PRO_USER = U["cliente"], U["carlos"]
NAV = {CLIENT: ("client_navigation", 4), PRO_USER: ("professional_navigation", 1)}


def bar_label(at, user_id):
    nav, i = NAV[user_id]
    return at.button(key=f"{nav}_btn_{i}").label.replace(" ", " ")


def send(user_id, title, message):
    conn = db.get_connection()
    db.notify(conn, user_id, title, message)
    conn.commit()
    conn.close()


for uid, who in ((CLIENT, "cliente"), (PRO_USER, "profesional")):
    db.mark_all_notifications_read(uid)
    at = new_app(front, uid)
    check(bar_label(at, uid) == "🔔 Notificaciones", f"[{who}] sin no leídas la barra no muestra contador")

    send(uid, "Aviso <b>uno</b>", "Mensaje con <script>alert(1)</script>")
    send(uid, "Aviso dos", "Segundo mensaje")
    at = new_app(front, uid)
    check(bar_label(at, uid) == "🔔 Notificaciones (2)", f"[{who}] la barra muestra 2 no leídas")

    nav, i = NAV[uid]
    at.button(key=f"{nav}_btn_{i}").click().run()
    page = md(at)
    check(not at.exception and "Aviso dos" in page and "&lt;script&gt;" in page and "<script>" not in page,
          f"[{who}] lista las notificaciones con el texto escapado")
    check(any(b.key == "notif_read_all" and "(2)" in b.label for b in at.button),
          f"[{who}] «Marcar todas como leídas (2)»")

    first = db.get_notifications(uid)[0]["id"]
    at.button(key=f"notif_read_{first}").click().run()
    check(db.count_unread_notifications(uid) == 1 and bar_label(at, uid) == "🔔 Notificaciones (1)",
          f"[{who}] marcar una como leída actualiza el contador al tiro")

    at.button(key="notif_read_all").click().run()
    check(db.count_unread_notifications(uid) == 0 and bar_label(at, uid) == "🔔 Notificaciones"
          and not keys(at, "notif_read_"), f"[{who}] «Marcar todas» deja el contador en cero")

# ---------- Cada usuario ve solo las suyas ----------
send(CLIENT, "Solo para el cliente", "x")
mine = db.get_notifications(CLIENT)[0]["id"]
db.mark_notification_read(mine, PRO_USER)
check(db.count_unread_notifications(CLIENT) == 1, "un usuario no puede marcar como leída una notificación ajena")
at = new_app(front, PRO_USER)
at.button(key="professional_navigation_btn_1").click().run()
check("Solo para el cliente" not in md(at), "[profesional] no ve notificaciones del cliente")

# ---------- Admin y visitante no tienen sección de notificaciones ----------
for uid, nav in ((U["admin"], "admin_navigation"), (None, "visitor_navigation")):
    at = new_app(front, uid)
    check(not any("Notificaciones" in plain(b.label or "") for b in at.button if b.key and b.key.startswith(nav)),
          f"[{nav}] sin sección de notificaciones")

terminar()
