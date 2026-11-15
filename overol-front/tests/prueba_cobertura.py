"""Cobertura del profesional (etapa C): GET/PATCH /api/professionals/me/availability/ con los
días en nombre completo, horario, disponibilidad y comunas, y la tarifa por PATCH /auth/me/."""

from comun import backend, calls, check, errors, md, new_app, preparar, terminar, texts, toasts

front = preparar()

PRO = "profesional1@demo.overol.cl"
CLIENTE = "cliente1@demo.overol.cl"


def coverage(email=PRO):
    return new_app(front, email, professional_navigation="📍 Cobertura")


def last_body(method, path):
    found = calls(method, path)
    return found[-1][2] if found else None


# ---------- Carga lo que tiene el backend ----------
at = coverage()
check(not at.exception and calls("GET", "/professionals/me/availability/"), "pide GET /professionals/me/availability/")
check(at.multiselect(key="cov_days").value == ["Lun", "Mar", "Mié", "Jue", "Vie"]
      and at.selectbox(key="cov_start").value == "09:00" and at.selectbox(key="cov_end").value == "18:00",
      "muestra los días (de «Lunes» a «Lun») y el horario del backend")
check(at.multiselect(key="cov_communes").value == ["Santiago", "Ñuñoa", "Providencia"] and at.toggle(key="cov_available").value,
      "muestra comunas y disponibilidad")
check(at.number_input(key="cov_fee").value == 15000, "muestra la tarifa de /auth/me/ (15000)")

# ---------- Validaciones del front ----------
backend.calls.clear()
at.multiselect(key="cov_days").set_value([])
at.button(key="save_coverage").click().run()
check("al menos un día" in errors(at) and not calls("PATCH"), "sin días: no envía")
at.multiselect(key="cov_days").set_value(["Lun"])
at.selectbox(key="cov_start").select("18:00")
at.selectbox(key="cov_end").select("09:00")
at.button(key="save_coverage").click().run()
check("posterior a la de inicio" in errors(at) and not calls("PATCH"), "término antes del inicio: no envía")

# ---------- Guardar ----------
at = coverage()
backend.calls.clear()
at.multiselect(key="cov_days").set_value(["Lun", "Mar", "Mié", "Jue"])
at.selectbox(key="cov_start").select("10:00")
at.multiselect(key="cov_communes").set_value(["Santiago", "Maipú"])
at.number_input(key="cov_fee").set_value(20000)
at.button(key="save_coverage").click().run()
body = last_body("PATCH", "/professionals/me/availability/") or {}
check(body == {"work_days": ["Lunes", "Martes", "Miércoles", "Jueves"], "work_start": "10:00", "work_end": "18:00",
               "is_available": True, "coverage_communes": ["Santiago", "Maipú"]},
      "PATCH con días en nombre completo, horario, disponibilidad y comunas")
check(last_body("PATCH", "/auth/me/") == {"visit_fee": 20000}, "la tarifa va por PATCH /auth/me/")
pro = backend.professional(PRO)
check(pro["work_start"] == "10:00:00" and pro["visit_fee"] == 20000 and "Cobertura, días, horario y tarifa actualizados" in toasts(at),
      "el backend guardó los cambios")

at = coverage()
backend.calls.clear()
at.button(key="save_coverage").click().run()
check(calls("PATCH", "/professionals/me/availability/") and not calls("PATCH", "/auth/me/"),
      "si la tarifa no cambió, no la vuelve a enviar")

# ---------- El cliente ve el horario nuevo ----------
pid = pro["id"]
at = new_app(front, CLIENTE, client_navigation="🔎 Buscar profesionales", _client_prev_menu="🔎 Buscar profesionales",
             selected_professional=pid)
check("10:00–18:00" in texts(at) and "Lun, Mar, Mié, Jue" in texts(at), "el perfil público muestra los días y el horario nuevos")
check(all(s.split(" - ")[0] >= "10:00" for s in at.selectbox(key=f"request_time_{pid}").options),
      "las franjas para solicitar respetan el horario nuevo")

# ---------- Sin horario configurado ----------
backend.professional(PRO).update(work_start=None, work_end=None, work_days=[])
at = coverage()
check("Todavía no configuras tus días y horario" in texts(at), "sin horario: avisa que no recibirá solicitudes")

# ---------- Backend caído ----------
at = coverage()
backend.caido = True  # el backend se cae con la sesión abierta
at.run()
check(not at.exception and "No se pudo cargar tu disponibilidad" in errors(at), "backend caído: error claro")
backend.caido = False

terminar()
