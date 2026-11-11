"""Solicitudes contra el backend (etapa C): formulario con especialidad y dirección de /me,
errores 400 legibles, «Mis solicitudes» y «Solicitudes» con pestañas, aceptar, rechazar con
motivo, cancelar (cliente con mantener presionado, profesional con motivo), finalizar y
confirmar en ambos órdenes, contacto solo con la solicitud aceptada, 409 y estados del backend."""

from datetime import date, timedelta

from comun import backend, calls, check, errors, md, new_app, preparar, terminar, texts, toasts

front = preparar()

CLIENTE, PRO = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl"
PRO2, PRO3 = "profesional2@demo.overol.cl", "profesional3@demo.overol.cl"
PID = backend.professional(PRO)["id"]
ADDRESS = backend.by_email(CLIENTE)["address"]


def profile(pro_email):
    pid = backend.professional(pro_email)["id"]
    return new_app(front, CLIENTE, client_navigation="🔎 Buscar profesionales", _client_prev_menu="🔎 Buscar profesionales",
                   selected_professional=pid), pid


def client_requests():
    return new_app(front, CLIENTE, client_navigation="📋 Mis solicitudes")


def pro_requests(email=PRO):
    return new_app(front, email, professional_navigation="📋 Solicitudes")


def status(vid):
    return backend.visits[vid]["status"]


def last_visit():
    return max(backend.visits)


def keys(at):
    return [b.key for b in at.button]


# ---------- Formulario «Solicitar visita» ----------
at, pid = profile(PRO)
spec = at.selectbox(key=f"request_specialty_Gasfitería_{pid}")
check(not at.exception and set(spec.options) == {"Fugas de agua", "Calefont y termo"},
      "el formulario ofrece las especialidades del profesional en ese oficio")
check(at.text_input(key=f"request_address_{pid}").value == ADDRESS and at.text_input(key=f"request_address_{pid}").disabled,
      "la dirección de la visita sale de /auth/me/ y no se edita aquí")
check(all("09:00" <= s.split(" - ")[0] and s.split(" - ")[1] <= "18:00" for s in at.selectbox(key=f"request_time_{pid}").options),
      "solo ofrece franjas dentro del horario del profesional")
check(at.date_input(key=f"request_date_{pid}").value.weekday() < 5, "la fecha propuesta es un día en que trabaja")

backend.calls.clear()
at.button(key=f"send_request_{pid}").click().run()
check("Describe el trabajo" in texts(at) and not calls("POST", "/requests/"), "sin descripción: avisa y no envía")

at.selectbox(key=f"request_specialty_Gasfitería_{pid}").select("Calefont y termo")
at.text_area(key=f"request_description_{pid}").input("El calefont no enciende")
slots = at.selectbox(key=f"request_time_{pid}").options
at.button(key=f"send_request_{pid}").click().run()
body = (calls("POST", "/requests/") or [(None, None, {})])[-1][2]
sid = next(s for s, (n, _) in backend.specialties.items() if n == "Calefont y termo")
check(body.get("professional") == pid and body.get("specialty") == sid and body.get("visit_address") == ADDRESS
      and body.get("visit_time") in slots
      and date.fromisoformat(body.get("visit_date")).weekday() < 5,
      "POST /requests/ con profesional, especialidad, fecha, franja, comuna y dirección")
VID = last_visit()
check(status(VID) == "PENDING" and "Solicitud enviada" in toasts(at), "la solicitud queda Pendiente en el backend")

at, pid = profile(PRO)
at.text_area(key=f"request_description_{pid}").input("Otra vez")
at.button(key=f"send_request_{pid}").click().run()
check("Ya tienes una solicitud pendiente para este profesional" in errors(at) and "non_field_errors" not in errors(at),
      "duplicada: el error del backend se muestra legible")

at, pid = profile(PRO2)
saturday = date.today() + timedelta(days=(5 - date.today().weekday()) % 7 or 7)
at.date_input(key=f"request_date_{pid}").set_value(saturday)
at.text_area(key=f"request_description_{pid}").input("Enchufe quemado")
at.button(key=f"send_request_{pid}").click().run()
check("Fecha: La solicitud está fuera de los días de atención del profesional." in errors(at),
      "día en que no trabaja: «Fecha: …» del backend (400 por campo)")

backend.professional(PRO2)["work_start"] = None
at, pid = profile(PRO2)
check("todavía no configuró su horario" in texts(at) and f"send_request_{pid}" not in keys(at),
      "profesional sin horario: no ofrece enviar")
backend.professional(PRO2)["work_start"] = "09:00:00"

saved = backend.professional(PRO3)["trades"][1]["specialties"]
backend.professional(PRO3)["trades"][1]["specialties"] = []
at, pid = profile(PRO3)
at.selectbox(key=f"request_trade_{pid}").select("Pintura").run()
check("aún no registra especialidades de Pintura" in texts(at) and f"send_request_{pid}" not in keys(at),
      "oficio sin especialidades: no se puede solicitar")
backend.professional(PRO3)["trades"][1]["specialties"] = saved

# ---------- Mis solicitudes (cliente) ----------
at = client_requests()
expires = backend.visits[VID]["expires_at"].astimezone().strftime("%d-%m-%Y %H:%M")
check(not at.exception and f"Solicitud #{VID}" in md(at) and "Pendiente" in md(at), "el cliente ve su solicitud Pendiente")
check(f"vence el {expires}" in texts(at), f"muestra expires_at tal como lo entrega el backend ({expires})")
check("Datos de contacto" not in md(at), "pendiente: sin datos de contacto")
check("Esperando confirmación" in at.selectbox(key="client_requests_filter").options, "el filtro usa los estados traducidos")

# ---------- Rechazo con motivo ----------
at = pro_requests()
check(not at.exception and at.tabs[0].label.startswith("Pendientes (1)"), "el profesional ve la pendiente en su pestaña")
at.selectbox(key=f"reject_reason_{VID}").select("Otro")
at.button(key=f"pro_reject_{VID}").click().run()
check("debes explicar el motivo" in texts(at) and status(VID) == "PENDING", "«Otro» sin explicación: no rechaza")
at.text_input(key=f"reject_detail_{VID}").input("Estoy de vacaciones esa semana")
at.button(key=f"pro_reject_{VID}").click().run()
check(status(VID) == "REJECTED" and backend.visits[VID]["rejection_reason"] == "Otro — Estoy de vacaciones esa semana",
      "rechaza con el motivo y el detalle (POST reject)")
at = client_requests()
check("Rechazada" in md(at) and "Estoy de vacaciones" in texts(at), "el cliente ve el rechazo y su motivo")

# ---------- Aceptar → contacto visible para ambos ----------
VID = backend.add_visit(CLIENTE, PRO)
at = pro_requests()
at.button(key=f"pro_accept_{VID}").click().run()
check(status(VID) == "ACCEPTED", "acepta la solicitud (POST accept)")
check("Datos de contacto del cliente" in md(at) and backend.by_email(CLIENTE)["phone"] in md(at),
      "aceptada: el profesional ve el contacto del cliente")
at = client_requests()
check("Datos de contacto del profesional" in md(at) and backend.by_email(PRO)["phone"] in md(at),
      "aceptada: el cliente ve el contacto del profesional")

# ---------- Finalizar: el profesional primero ----------
at = pro_requests()
at.button(key=f"pro_complete_{VID}").click().run()
check(status(VID) == "PROFESSIONAL_FINISHED" and "Falta la del cliente" in toasts(at), "el profesional finaliza (POST finish)")
at = client_requests()
check("Esperando confirmación" in md(at) and "Falta tu confirmación" in texts(at), "el cliente ve «Esperando confirmación»")
at.button(key=f"complete_{VID}").click().run()
check(status(VID) == "COMPLETED" and "finalizado por ambas partes" in toasts(at), "el cliente confirma (POST confirm): Finalizada")
at = client_requests()
check("Finalizada" in md(at) and "Datos de contacto del profesional" in md(at), "finalizada: sigue el contacto")

# ---------- Finalizar: el cliente primero ----------
VID = backend.add_visit(CLIENTE, PRO, status="ACCEPTED")
at = client_requests()
at.button(key=f"complete_{VID}").click().run()
at = client_requests()
check(status(VID) == "ACCEPTED" and "Ya confirmaste la finalización" in texts(at), "el cliente confirma primero: sigue Aceptada")
at = pro_requests()
check("El cliente ya confirmó" in texts(at), "el profesional ve que el cliente ya confirmó")
at.button(key=f"pro_complete_{VID}").click().run()
check(status(VID) == "COMPLETED", "el profesional finaliza después: Finalizada")

# ---------- El profesional cancela una aceptada con motivo ----------
VID = backend.add_visit(CLIENTE, PRO, status="ACCEPTED")
at = pro_requests()
check(at.text_area(key=f"pro_cancel_reason_{VID}").max_chars == 500, "motivo de cancelación máx. 500")
at.button(key=f"pro_cancel_{VID}").click().run()
check("Escribe el motivo" in texts(at) and status(VID) == "ACCEPTED", "sin motivo: no cancela")
at.text_area(key=f"pro_cancel_reason_{VID}").input("Se me enfermó un hijo")
at.button(key=f"pro_cancel_{VID}").click().run()
check(status(VID) == "CANCELLED" and backend.visits[VID]["cancelled_by"] == "PROFESSIONAL", "cancela (POST cancel_professional)")
at = client_requests()
check("El profesional canceló" in texts(at) and "Se me enfermó un hijo" in texts(at), "el cliente ve el motivo")

# ---------- El cliente cancela con advertencia y mantener presionado ----------
VID = backend.add_visit(CLIENTE, PRO2)
at = client_requests()
at.button(key=f"cancel_{VID}").click().run()
check("¿Estás seguro de que quieres cancelar la hora?" in texts(at), "cancelar: muestra la advertencia")
at.button(key=f"cancel_no_{VID}").click().run()
check(status(VID) == "PENDING" and f"cancel_{VID}" in keys(at), "«No, mantener mi solicitud» no cancela")
import views.client  # noqa: E402

views.client.hold_to_confirm = lambda **_: True  # AppTest no puede mantener presionado el componente
at.button(key=f"cancel_{VID}").click().run()
at.run()
check(status(VID) == "CANCELLED" and backend.visits[VID]["cancelled_by"] == "CLIENT", "al mantener presionado: POST cancel")

# ---------- 409: la solicitud cambió mientras tanto ----------
VID = backend.add_visit(CLIENTE, PRO)
at = pro_requests()
# El cliente cancela justo cuando el profesional pulsa «Aceptar»
backend.before_action = lambda visit: visit.update(status="CANCELLED")
at.button(key=f"pro_accept_{VID}").click().run()
backend.before_action = None
check(not at.exception and "Solo se pueden aceptar solicitudes pendientes." in toasts(at) and status(VID) == "CANCELLED",
      "409: avisa con el mensaje del backend")

# ---------- Estados del backend: vencida y cerrada por Overol ----------
VID_OLD = backend.add_visit(CLIENTE, PRO3)
backend.age_visit(VID_OLD, 31)
VID_FC = backend.add_visit(CLIENTE, PRO3, status="FORCED_CLOSED")
at = client_requests()
check(status(VID_OLD) == "EXPIRED" and "Vencida" in md(at), "una pendiente vieja vence en el backend y se muestra «Vencida»")
check("Cerrada por Overol" in md(at) and "El equipo de Overol cerró" in texts(at), "FORCED_CLOSED: «Cerrada por Overol»")
at = pro_requests(PRO3)
check(any(t.label.startswith("Rechazadas / Canceladas / Vencidas (2)") for t in at.tabs), "pestaña de cerradas del profesional")

# ---------- Perfil del cliente: cifras desde /requests/ ----------
at = new_app(front, CLIENTE, client_navigation="👤 Mi perfil")
total = sum(1 for v in backend.visits.values() if v["client"] == backend.by_email(CLIENTE)["id"])
check(f'pstat-n">{total}<' in md(at), f"Mi perfil: {total} solicitudes")

terminar()
