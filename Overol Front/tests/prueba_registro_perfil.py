"""Registro de cliente y profesional sin espejo local, completar perfil y «Mi perfil» por
PATCH /auth/me/ (contact_preference, titular y presentación solo para profesionales),
cambio y recuperación de contraseña."""

import os

from comun import backend, calls, check, errors, new_app, preparar, terminar, texts, toasts

front = preparar()

from streamlit.testing.v1 import AppTest  # noqa: E402


def register_page():
    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    at.session_state["show_login"] = True
    return at.run()


def free_rut():
    used = {u["rut"] for u in backend.users.values()}
    for number in range(23456789, 23460000):
        total, factor = 0, 2
        for digit in reversed(str(number)):
            total += int(digit) * factor
            factor = 2 if factor == 7 else factor + 1
        dv = {11: "0", 10: "K"}.get(11 - total % 11, str(11 - total % 11))
        if f"{number}-{dv}" not in used:
            return f"{number}-{dv}"


def fill(at, email, password, role="Cliente", trade=None):
    at.radio(key="register_role").set_value(role).run()
    at.text_input(key="register_name").input("Paula")
    at.text_input(key="register_lastname").input("Rojas")
    at.text_input(key="register_rut").input(free_rut())
    at.text_input(key="register_email").input(email)
    at.text_input(key="register_phone").input("+56 9 8765 4321")
    at.text_input(key="register_address").input("Av. Siempre Viva 742")
    if role == "Profesional":
        at.selectbox(key="register_trade").select(trade)
        at.number_input(key="register_years").set_value(4)
        at.multiselect(key="register_coverage").select("Santiago").select("Ñuñoa")
    at.text_input(key="register_password").input(password)
    at.text_input(key="register_confirm").input(password)
    at.checkbox(key="register_privacy").check()
    at.button(key="register_button").click().run()
    return at


def last_body(method, path):
    found = calls(method, path)
    return found[-1][2] if found else None


def submit(at, label):
    next(b for b in at.button if b.label == label).click().run()


# ---------- Registro de cliente ----------
backend.calls.clear()
at = fill(register_page(), "nueva.cliente@prueba.cl", "Clave1234")
body = last_body("POST", "/auth/register/")
check(not at.exception and body and body["role"] == "CLIENT" and "professional_profile" not in body,
      "cliente: POST /auth/register/ sin perfil profesional")
check(body and body["phone"] and body["address"] and body["commune"] and body["privacy_policy_accepted"],
      "cliente: envía teléfono, dirección, comuna y la aceptación de la política")
check("Cuenta creada correctamente" in toasts(at) and backend.by_email("nueva.cliente@prueba.cl"),
      "cliente: la cuenta se crea en el backend")
check("register_certifications" not in [w.key for w in at.text_input], "el formulario ya no pide certificaciones como texto")

# ---------- Registro de profesional ----------
backend.calls.clear()
at = fill(register_page(), "paula.multi@prueba.cl", "Clave1234", "Profesional", "Maestro multipropósito")
check(not calls("POST", "/auth/register/") and "«Maestro multipropósito» todavía no está disponible" in errors(at)
      and "Gasfitería" in errors(at), "oficio que el backend no tiene: avisa y no envía el registro")

at = fill(register_page(), "paula.gasfiter@prueba.cl", "Clave1234", "Profesional", "Gasfitería")
body = last_body("POST", "/auth/register/") or {}
profile = body.get("professional_profile", {})
check(profile.get("coverage_communes") == ["Santiago", "Ñuñoa"]
      and profile.get("categories") == [{"category": 1, "years_experience": 4}],
      "profesional: envía coverage_communes y categories con el id del backend")
check("latitude" not in str(body) and "certifications" not in profile, "profesional: sin coordenadas ni certificaciones")
new_pro = backend.by_email("paula.gasfiter@prueba.cl")
check(new_pro and new_pro["professional"]["verification_status"] == "PENDING", "profesional: queda pendiente de verificación")

# ---------- Errores del backend legibles ----------
at = fill(register_page(), "otra@prueba.cl", "Password123")
check("La contraseña no cumple las reglas de seguridad del servidor" in errors(at)
      and "- Esta contraseña es demasiado común." in errors(at), "contraseña débil: reglas del backend como lista")
at = fill(register_page(), "cliente1@demo.overol.cl", "Clave1234")
check("Correo: Ya existe" in errors(at), "correo repetido: el backend lo informa por campo")

# ---------- Completar perfil (cuenta sin teléfono ni dirección) ----------
INCOMPLETO = "cliente2@demo.overol.cl"
at = new_app(front, INCOMPLETO)
check(not at.exception and "Completa tu perfil" in texts(at) and "client_navigation_btn_0" not in [b.key for b in at.button],
      "cuenta sin teléfono ni dirección: pide completar el perfil antes de entrar")
check("profile_contact_preference" not in [w.key for w in at.selectbox],
      "cliente: no pide preferencia de contacto (el backend no la guarda para clientes)")
at.text_input(key="profile_phone").input("123")
submit(at, "Guardar mis datos y entrar a Overol")
check("teléfono válido" in errors(at) and not calls("PATCH", "/auth/me/"), "teléfono inválido: no envía nada")
at.text_input(key="profile_phone").input("+56 9 5555 5555")
at.text_input(key="profile_address").input("Pasaje Uno 12")
at.selectbox(key="profile_commune").select("Ñuñoa")
submit(at, "Guardar mis datos y entrar a Overol")
body = last_body("PATCH", "/auth/me/") or {}
check(body == {"phone": "+56 9 5555 5555", "address": "Pasaje Uno 12", "commune": "Ñuñoa"},
      "completa el perfil con PATCH /auth/me/ (teléfono, dirección y comuna)")
check(not at.exception and "client_navigation_btn_0" in [b.key for b in at.button], "después entra a la plataforma")

# ---------- Mi perfil del cliente ----------
CLIENTE = "cliente1@demo.overol.cl"
at = new_app(front, CLIENTE, client_navigation="👤 Mi perfil")
check(not at.exception and at.text_input(key="ro_name").value == "Clara Pérez" and at.text_input(key="ro_rut").disabled,
      "Mi perfil: nombre, RUT y correo de /auth/me/, bloqueados")
check("edit_contact_preference" not in [w.key for w in at.selectbox], "cliente: sin preferencia de contacto")
at.text_input(key="edit_address").input("Av. Nueva 99")
submit(at, "Guardar cambios")
check(backend.by_email(CLIENTE)["address"] == "Av. Nueva 99" and "Tus datos fueron actualizados" in toasts(at),
      "cliente: guarda los cambios en el backend")
check(at.session_state["me"]["address"] == "Av. Nueva 99", "la sesión se recarga con los datos nuevos")

# ---------- Mi perfil del profesional: preferencia, titular y presentación ----------
PRO = "profesional1@demo.overol.cl"
at = new_app(front, PRO, professional_navigation="👤 Mi perfil")
at.selectbox(key="edit_contact_preference").select("Correo electrónico")
at.text_input(key="edit_headline").input("Gasfiter certificado")
at.text_area(key="edit_bio").input("Presentación nueva")
submit(at, "Guardar cambios")
body = last_body("PATCH", "/auth/me/") or {}
pro = backend.professional(PRO)
check(body.get("contact_preference") == "Correo electrónico" and body.get("headline") == "Gasfiter certificado"
      and pro["contact_preference"] == "Correo electrónico" and pro["bio"] == "Presentación nueva",
      "profesional: envía y guarda contact_preference, headline y bio")
check(at.text_input(key="edit_headline").max_chars == 160 and at.text_area(key="edit_bio").max_chars == 500,
      "profesional: titular máx. 160 y presentación máx. 500, como el backend")

# ---------- Cambiar contraseña ----------
at = new_app(front, CLIENTE, client_navigation="👤 Mi perfil")
at.text_input(key="pwd_current").input("equivocada")
at.text_input(key="pwd_new").input("NuevaClave99")
at.text_input(key="pwd_confirm").input("NuevaClave99")
submit(at, "Cambiar contraseña")
check("La contraseña actual no es correcta" in errors(at), "contraseña actual incorrecta: mensaje del backend")
at.text_input(key="pwd_current").input("OverolDemo123!")
at.text_input(key="pwd_new").input("NuevaClave99")
at.text_input(key="pwd_confirm").input("Otra")
submit(at, "Cambiar contraseña")
check("no coinciden" in errors(at), "confirmación distinta: no envía")
at.text_input(key="pwd_current").input("OverolDemo123!")
at.text_input(key="pwd_new").input("NuevaClave99")
at.text_input(key="pwd_confirm").input("NuevaClave99")
submit(at, "Cambiar contraseña")
check(backend.by_email(CLIENTE)["password"] == "NuevaClave99" and any("Contraseña actualizada" in s.value for s in at.success),
      "cambia la contraseña con POST /auth/password/change/")
backend.by_email(CLIENTE)["password"] = "OverolDemo123!"

# ---------- Recuperar contraseña ----------
at = register_page()
at.text_input(key="recovery_email").input("no-es-correo")
submit(at, "Enviar instrucciones")
check("correo válido" in errors(at) and not backend.reset_emails, "recuperación: valida el correo antes de enviar")
at.text_input(key="recovery_email").input("Cliente1@Demo.Overol.cl")
submit(at, "Enviar instrucciones")
check(backend.reset_emails == ["cliente1@demo.overol.cl"] and any("recibirás instrucciones" in s.value for s in at.success),
      "recuperación: POST /auth/password/reset/ y muestra el mensaje del backend")

terminar()
