"""Etapa G: panel del admin con lo que tiene endpoint (indicadores de reclamos y tickets,
verificación con cédula, estado de cuentas, reclamos y bandeja de soporte); el resto oculto."""

from comun import backend, calls, check, errors, md, nav_labels, new_app, preparar, terminar, texts, toasts

front = preparar()

ADMIN, CLIENTE, PRO = "admin@demo.overol.cl", "cliente1@demo.overol.cl", "profesional1@demo.overol.cl"
PENDING = "pendiente@demo.overol.cl"


def admin(section_name):
    return new_app(front, ADMIN, admin_navigation=section_name)


# ---------- Barra ----------
at = admin("📊 Indicadores")
check(nav_labels(at, "admin_navigation") == ["📊 Indicadores", "🪪 Verificación", "👥 Usuarios", "🛠️ Reclamos",
                                              "💬 Soporte", "ℹ️ Quiénes somos"],
      "barra del admin sin Moderación, Contenidos ni Trazabilidad (no tienen endpoint)")

# ---------- Datos de partida: un reclamo escalado y un ticket abierto ----------
admin_user = backend.by_email(ADMIN)
VID = backend.add_visit(CLIENTE, PRO, status="COMPLETED")
backend._create_claim(backend.by_email(CLIENTE), {"visit": VID, "description": "Quedó mal sellado"})
claim = backend.claims[max(backend.claims)]
claim["status"] = "ESCALATED"
backend._create_ticket(backend.by_email(CLIENTE), {"visit": VID, "subject": "Consulta", "description": "¿Quién paga?"})
ticket = backend.tickets[max(backend.tickets)]

# ---------- Indicadores ----------
at = admin("📊 Indicadores")
check(not at.exception and f'metric-number">{len(backend.claims)}<' in md(at)
      and f'metric-number">{len(backend.tickets)}<' in md(at), "indicadores con los reclamos y tickets del backend")
check("Estado de reclamos" in md(at) and "Estado de tickets" in md(at), "gráficos de estado")

# ---------- Verificación ----------
pid = backend.professional(PENDING)["id"]
at = admin("🪪 Verificación")
at.number_input(key="verif_profile_id").set_value(pid).run()
at.button(key=f"view_doc_front_{pid}").click().run()
check("El documento solicitado no existe." in errors(at), "sin cédula: el backend responde que no existe")
at.button(key=f"admin_approve_{pid}").click().run()
check("debe cargar ambos lados de su cédula" in errors(at), "no se puede aprobar sin la cédula (400 del backend)")

backend.professional(PENDING).update(id_front="frente.png", id_back="reverso.pdf")
at.button(key=f"view_doc_front_{pid}").click().run()
check(len(at.get("imgs")) >= 1 or any(e.type == "image" for e in at.main), "muestra la imagen del frente")
check(any(b.key == f"download_doc_front_{pid}" for b in at.get("download_button")), "ofrece descargarla")
at.button(key=f"admin_reject_{pid}").click().run()
check("Escribe el motivo del rechazo" in texts(at), "rechazar exige motivo")
at.button(key=f"admin_approve_{pid}").click().run()
check(backend.professional(PENDING)["verification_status"] == "APPROVED" and "Profesional aprobado" in toasts(at)
      and backend.notifications[-1]["title"] == "Resultado de verificación", "aprueba (POST .../approve/) y se notifica")

# ---------- Estado de cuentas ----------
target = backend.by_email("cliente2@demo.overol.cl")
at = admin("👥 Usuarios")
at.number_input(key="account_user_id").set_value(target["id"])
at.selectbox(key="account_status").select("SUSPENDED")
next(b for b in at.button if b.label == "Cambiar estado").click().run()
check("Escribe el motivo" in texts(at) and target["account_status"] == "ACTIVE", "sin motivo: no cambia")
at.number_input(key="account_user_id").set_value(target["id"])
at.selectbox(key="account_status").select("SUSPENDED")
at.text_area(key="account_reason").input("Reportes de mal trato")
next(b for b in at.button if b.label == "Cambiar estado").click().run()
check(target["account_status"] == "SUSPENDED" and "Suspendida" in toasts(at), "suspende la cuenta con motivo")
at.number_input(key="account_user_id").set_value(admin_user["id"])
at.text_area(key="account_reason").input("Prueba")
next(b for b in at.button if b.label == "Cambiar estado").click().run()
check("No puedes cambiar el estado de tu propia cuenta" in texts(at), "no puede cambiarse a sí mismo")
target["account_status"] = "ACTIVE"

# ---------- Reclamos ----------
at = admin("🛠️ Reclamos")
check(f"Reclamo #{claim['id']}" in md(at) and "En mediación" in md(at), "ve todos los reclamos con su estado")
at.button(key=f"save_claim_{claim['id']}").click().run()
check("Escribe la resolución" in texts(at), "resolver exige texto")
at.text_area(key=f"claim_resolution_{claim['id']}").input("Segunda visita sin costo")
at.button(key=f"save_claim_{claim['id']}").click().run()
check(claim["status"] == "RESOLVED" and claim["admin_resolution"] == "Segunda visita sin costo"
      and ("resolve_claim", admin_user["id"], claim["id"]) in backend.audit_log, "resuelve (POST .../resolve/) con bitácora")

# ---------- Bandeja de soporte ----------
at = admin("💬 Soporte")
check(calls("GET", "/tickets/?status=OPEN") and f"Ticket #{ticket['id']}" in md(at), "bandeja de tickets abiertos (?status=OPEN)")
at.text_area(key=f"support_reply_{ticket['id']}").input("La garantía la cubre el profesional")
at.button(key=f"support_resolve_{ticket['id']}").click().run()
check(ticket["status"] == "RESOLVED" and backend.notifications[-1]["title"] == "Ticket resuelto", "responde y resuelve; el usuario recibe aviso")
at.radio(key="support_filter").set_value("Resueltos").run()
check(f"Ticket #{ticket['id']}" in md(at) and "La garantía la cubre" in texts(at), "filtro «Resueltos»")

terminar()
