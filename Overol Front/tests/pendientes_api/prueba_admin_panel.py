"""Panel del admin: bitácora con filtros (usuario, acción, fechas) y paginación;
suspender y reactivar cuentas con motivo (máx. 500), bitácora y notificación."""

from datetime import date, datetime, timedelta

from comun import check, new_app as _new_app, preparar, terminar, usuarios

front = preparar()
U = usuarios(front)
ADMIN, CLIENT, PRO_USER = U["admin"], U["cliente"], U["carlos"]


def new_app(user_id):
    return _new_app(front, user_id)


NAV_USERS, NAV_AUDIT = "admin_navigation_btn_2", "admin_navigation_btn_6"

at = new_app(ADMIN)
from core import database as db  # noqa: E402

# 45 registros de prueba del cliente con acción TEST_FILTRO, repartidos en 3 días antiguos
base = datetime(2026, 9, 1, 10, 0, 0)
conn = db.get_connection()
for i in range(45):
    when = base + timedelta(days=i % 3, minutes=i)
    conn.execute("INSERT INTO audit_log (user_id, action, entity, entity_id, details, created_at) VALUES (?,?,?,?,?,?)",
                 (CLIENT, "TEST_FILTRO", "pruebas", i, "<script>x</script> detalle" if i == 44 else f"registro {i}",
                  when.strftime("%Y-%m-%d %H:%M:%S")))
conn.execute("INSERT INTO audit_log (user_id, action, entity, entity_id, details, created_at) "
             "VALUES (NULL, 'EXPIRE', 'requests', 999, 'Vencida de prueba', '2026-09-02 08:00:00')")
conn.commit()
total_all = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
conn.close()


def caption(at):
    return " ".join(c.value for c in at.caption)


def entries(at):
    return [m.value for m in at.markdown if 'class="audit-entry"' in m.value]


# ---------- Bitácora ----------
at = new_app(ADMIN)
at.button(key=NAV_AUDIT).click().run()
check(not at.exception and all(any(w.key == k for w in ws) for k, ws in
      (("audit_user", at.selectbox), ("audit_action", at.selectbox), ("audit_dates", at.date_input))),
      "[admin] la bitácora tiene filtros de usuario, acción y rango de fechas")
pages = -(-total_all // 20)
check(f"{total_all} registros · página 1 de {pages}" in caption(at) and len(entries(at)) == 20,
      f"[admin] sin filtros: {total_all} registros, 20 por página")
check(at.button(key="audit_prev").proto.disabled and not at.button(key="audit_next").proto.disabled,
      "[admin] en la página 1 «Más recientes» está deshabilitado")
at.button(key="audit_next").click().run()
check(f"página 2 de {pages}" in caption(at) and not at.button(key="audit_prev").proto.disabled,
      "[admin] «Más antiguos →» pasa a la página 2")

at.selectbox(key="audit_action").select("TEST_FILTRO").run()
check("45 registros · página 1 de 3" in caption(at), "[admin] filtrar por acción vuelve a la página 1 (45 → 3 páginas)")
at.button(key="audit_next").click().run()
at.button(key="audit_next").click().run()
check("página 3 de 3" in caption(at) and len(entries(at)) == 5 and at.button(key="audit_next").proto.disabled,
      "[admin] última página con 5 registros y «Más antiguos» deshabilitado")
page1 = new_app(ADMIN)
page1.button(key=NAV_AUDIT).click().run()
page1.selectbox(key="audit_action").select("TEST_FILTRO").run()
md = " ".join(entries(page1))
check("&lt;script&gt;x&lt;/script&gt;" in md and "<script>" not in md, "[admin] el detalle va escapado")

at.date_input(key="audit_dates").set_value((date(2026, 9, 2), date(2026, 9, 2))).run()
check("15 registros · página 1 de 1" in caption(at), "[admin] rango de un día: 15 registros de ese día, página 1")
at.date_input(key="audit_dates").set_value((date(2026, 9, 1), date(2026, 9, 3))).run()
check("45 registros" in caption(at), "[admin] rango de 3 días: los 45")

user_label = next(o for o in at.selectbox(key="audit_user").options if o.endswith(f"#{CLIENT}"))
at.selectbox(key="audit_user").select(user_label).run()
check("45 registros" in caption(at), "[admin] usuario + acción + fechas combinados")
at.selectbox(key="audit_action").select("Todas").run()
at.selectbox(key="audit_user").select("Sistema (acciones automáticas)").run()
md = " ".join(entries(at))
check("1 registros" in caption(at) and "Vencida de prueba" in md and "Usuario: Sistema" in md,
      "[admin] filtro «Sistema» muestra las acciones automáticas")
at.date_input(key="audit_dates").set_value((date(2026, 9, 3), date(2026, 9, 3))).run()
check(any("No hay registros con esos filtros" in i.value for i in at.info), "[admin] sin resultados: mensaje claro")

# ---------- Suspender / reactivar con motivo ----------
at = new_app(ADMIN)
at.button(key=NAV_USERS).click().run()
check(not any(b.key == f"toggle_user_{ADMIN}" for b in at.button), "[admin] no puede suspender su propia cuenta")
check(at.text_area(key=f"user_reason_{CLIENT}").proto.max_chars == 500, "[admin] el motivo tiene máximo 500 caracteres")
at.button(key=f"toggle_user_{CLIENT}").click().run()
check(not at.exception and any("Escribe el motivo" in e.value for e in at.error) and db.get_user(CLIENT)["active"] == 1,
      "[admin] suspender sin motivo → error y la cuenta sigue activa")
at.text_area(key=f"user_reason_{CLIENT}").input("Reclamos reiterados <b>graves</b>")
at.button(key=f"toggle_user_{CLIENT}").click().run()
check(not at.exception and db.get_user(CLIENT)["active"] == 0, "[admin] suspender con motivo desactiva la cuenta")
log, _ = db.get_audit_log(action="USER_SUSPEND", limit=1)
check(log and log[0]["user_id"] == ADMIN and log[0]["entity_id"] == CLIENT
      and log[0]["details"] == "Motivo: Reclamos reiterados <b>graves</b>", "[admin] la bitácora guarda quién, a quién y el motivo")
n = db.get_notifications(CLIENT)[0]
check(n["title"] == "Cuenta suspendida" and "Motivo: Reclamos reiterados <b>graves</b>" in n["message"],
      "[admin] el usuario recibe la notificación con el motivo")

at = new_app(ADMIN)
at.button(key=NAV_USERS).click().run()
check(at.button(key=f"toggle_user_{CLIENT}").label == "Reactivar", "[admin] la cuenta suspendida ofrece «Reactivar»")
at.text_area(key=f"user_reason_{CLIENT}").input("Revisado, era un malentendido")
at.button(key=f"toggle_user_{CLIENT}").click().run()
n = db.get_notifications(CLIENT)[0]
check(db.get_user(CLIENT)["active"] == 1 and n["title"] == "Cuenta reactivada" and "malentendido" in n["message"],
      "[admin] reactivar con motivo activa la cuenta y notifica")
check(db.get_audit_log(action="USER_REACTIVATE", limit=1)[0][0]["details"] == "Motivo: Revisado, era un malentendido",
      "[admin] la reactivación queda en la bitácora con su motivo")

ok, err = db.set_user_active(ADMIN, CLIENT, True, "otra vez")
check(not ok and "ya tenía" in err, "reactivar una cuenta activa no aplica ni duplica")
ok, err = db.set_user_active(ADMIN, CLIENT, False, "x" * 501)
check(not ok and "500" in err and db.get_user(CLIENT)["active"] == 1, "motivo de 501 caracteres → error")
ok, err = db.set_user_active(ADMIN, ADMIN, False, "prueba")
check(not ok and db.get_user(ADMIN)["active"] == 1, "el admin no puede suspenderse a sí mismo (también en la base)")

# El cliente reactivado ve la notificación al entrar
at = new_app(CLIENT)
check(not at.exception and any("Notificaciones" in b.label and "(" in b.label for b in at.button),
      "[cliente] tras reactivarse ve el contador de notificaciones")

terminar()
