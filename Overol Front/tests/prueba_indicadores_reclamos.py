"""Indicadores del admin (cifras reales) y reclamos de posventa: el cliente reclama un
servicio finalizado, lo ve en «Mis reclamos» y el admin registra la mediación."""

import re

from comun import check, md, new_app, next_valid_slot, plain, preparar, reset_pending, terminar, texts, usuarios

front = preparar()
U = usuarios(front)

from core import database as db  # noqa: E402

CLIENT, PRO_USER, ADMIN = U["cliente"], U["carlos"], U["admin"]
PID = db.get_professional_by_user(PRO_USER)["id"]


def count(sql):
    conn = db.get_connection()
    n = conn.execute(sql).fetchone()[0]
    conn.close()
    return n


def metric(at, label):
    """Número de la tarjeta de indicador con esa etiqueta (None si no está)."""
    for m in at.markdown:
        found = re.search(r'metric-number">(\d+)<.*metric-label">' + label + "<", m.value)
        if found:
            return int(found.group(1))
    return None


# ---------- Indicadores ----------
at = new_app(front, ADMIN)
check(not at.exception and "Indicadores de la plataforma" in md(at), "[admin] Indicadores abre al entrar")
for label, sql in (("Usuarios", "SELECT COUNT(*) FROM users"),
                   ("Profesionales", "SELECT COUNT(*) FROM professionals"),
                   ("Verificados", "SELECT COUNT(*) FROM professionals WHERE verified = 1"),
                   ("Solicitudes", "SELECT COUNT(*) FROM requests"),
                   ("Reclamos", "SELECT COUNT(*) FROM claims")):
    check(metric(at, label) == count(sql), f"[admin] indicador «{label}» = {count(sql)}")
check("Estado de solicitudes" in md(at) and "Estado de reclamos" in md(at), "[admin] gráficos de estado")

# ---------- Servicio finalizado para reclamar ----------
reset_pending(db, CLIENT, PID)
ok, rid = db.create_request(CLIENT, PID, db.get_trades(PID)[0]["trade"], "", "Santiago",
                            *next_valid_slot(db, PID), "Prueba de reclamos")
db.change_request_status(rid, "Aceptada", ["Pendiente"], professional_id=PID)
db.confirm_request_completion(rid, "client", client_id=CLIENT)
db.confirm_request_completion(rid, "professional", professional_id=PID)

at = new_app(front, CLIENT)
at.button(key="client_navigation_btn_2").click().run()
at.button(key=f"send_claim_{rid}").click().run()
check(any("describir el problema" in w.value for w in at.warning), "[cliente] el reclamo exige describir el problema")
before = count("SELECT COUNT(*) FROM claims")
at.text_area(key=f"claim_reason_{rid}").input("Volvió a gotear al día siguiente")
at.button(key=f"send_claim_{rid}").click().run()
conn = db.get_connection()
claim = conn.execute("SELECT * FROM claims WHERE request_id = ?", (rid,)).fetchone()
conn.close()
check(not at.exception and claim and claim["status"] == "Abierto" and count("SELECT COUNT(*) FROM claims") == before + 1,
      "[cliente] abre el reclamo de un servicio finalizado")
check(not any(b.key == f"send_claim_{rid}" for b in at.button) and f"reclamo #{claim['id']}" in texts(at),
      "[cliente] no puede reclamar dos veces el mismo servicio")

at.button(key="client_navigation_btn_3").click().run()
check(f"Reclamo #{claim['id']}" in md(at) and "Volvió a gotear" in texts(at), "[cliente] lo ve en «Mis reclamos»")

# ---------- Profesional: responde el reclamo ----------
at = new_app(front, PRO_USER)
nav = next(b for b in at.button if (b.key or "").startswith("professional_navigation_btn_") and "Reclamos" in b.label)
check(plain(nav.label) == "🛠️ Reclamos" and nav.label != plain(nav.label),
      "[profesional] «Reclamos» está en su barra, con contador de reclamos por responder")
nav.click().run()
check(not at.exception and "Reclamos de posventa" in md(at) and f"Reclamo #{claim['id']}" in md(at)
      and "Volvió a gotear" in texts(at), "[profesional] ve el reclamo de su cliente")
at.button(key=f"respond_claim_{claim['id']}").click().run()
check(any("Escribe una respuesta" in w.value for w in at.warning), "[profesional] la respuesta no puede ir vacía")
check(at.text_area(key=f"claim_response_{claim['id']}").max_chars == 500, "[profesional] respuesta de máx. 500 caracteres")
unread_before = db.count_unread_notifications(CLIENT)
at.text_area(key=f"claim_response_{claim['id']}").input("Voy el lunes a revisar la unión sin costo")
at.button(key=f"respond_claim_{claim['id']}").click().run()
conn = db.get_connection()
claim = conn.execute("SELECT * FROM claims WHERE id = ?", (claim["id"],)).fetchone()
conn.close()
check(not at.exception and claim["professional_response"] == "Voy el lunes a revisar la unión sin costo"
      and claim["status"] == "En mediación" and claim["response"] == "",
      "[profesional] responde: queda En mediación sin pisar la mediación del admin")
check(db.count_unread_notifications(CLIENT) == unread_before + 1, "[profesional] el cliente recibe una notificación")
check(not any(b.key == f"respond_claim_{claim['id']}" for b in at.button)
      and "Voy el lunes" in texts(at), "[profesional] ya no puede responder dos veces y ve su respuesta")

# ---------- Admin: Reclamos y mediación ----------
at = new_app(front, ADMIN)
at.button(key="admin_navigation_btn_4").click().run()
check(not at.exception and "Reclamos y mediación" in md(at) and f"Reclamo #{claim['id']}" in md(at),
      "[admin] el reclamo aparece en «Reclamos»")
at.selectbox(key=f"claim_status_{claim['id']}").select("En mediación")
at.text_area(key=f"claim_resolution_{claim['id']}").input("Se coordina una segunda visita sin costo")
at.button(key=f"save_claim_{claim['id']}").click().run()
conn = db.get_connection()
claim = conn.execute("SELECT * FROM claims WHERE id = ?", (claim["id"],)).fetchone()
conn.close()
check(claim["status"] == "En mediación" and claim["response"] == "Se coordina una segunda visita sin costo",
      "[admin] registra el estado y la mediación")
log, _ = db.get_audit_log(action="UPDATE")
check(any(r["entity"] == "claims" and r["entity_id"] == claim["id"] and r["user_id"] == ADMIN for r in log),
      "[admin] el cambio queda en la bitácora")

at.selectbox(key=f"claim_status_{claim['id']}").select("Cerrado")
at.button(key=f"save_claim_{claim['id']}").click().run()
check(not any(b.key == f"save_claim_{claim['id']}" for b in at.button), "[admin] un reclamo cerrado ya no se edita")

at = new_app(front, CLIENT)
at.button(key="client_navigation_btn_3").click().run()
check("Se coordina una segunda visita" in texts(at), "[cliente] ve la respuesta en «Mis reclamos»")
check("Respuesta del profesional:** Voy el lunes" in texts(at) or
      any("Respuesta del profesional" in m.value and "Voy el lunes" in m.value for m in at.markdown),
      "[cliente] ve por separado la respuesta del profesional y la mediación")

at = new_app(front, ADMIN)
check(metric(at, "Reclamos") == count("SELECT COUNT(*) FROM claims"), "[admin] el indicador de reclamos se actualiza")

terminar()
