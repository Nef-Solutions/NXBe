"""Arreglos del modo api con un backend simulado (se reemplaza requests.request):
registro de profesional con comunas y oficio del backend, oficio inexistente, reglas de
contraseña legibles, bloqueo 429 con retry_after, aviso de 5 minutos y días con nombre completo.
En modo local revisa que nada de esto salga a la red."""

import json
import os

import requests

from comun import check, new_app, preparar, terminar, texts, usuarios

front = preparar()
U = usuarios(front)

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import database as db  # noqa: E402
from core.constants import API_BASE_URL, DIAS_COMPLETOS, use_api  # noqa: E402

CATEGORIES = [{"id": 1, "name": "Electricidad"}, {"id": 2, "name": "Gasfitería"}, {"id": 3, "name": "Cerrajería"}]
calls = []      # (método, ruta, cuerpo) de cada petición
token_reply = {}  # respuesta que dará POST auth/token/
fail_availability = []


class FakeResponse:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data
        self.content = json.dumps(data).encode() if data is not None else b""

    def json(self):
        return self._data


def fake_request(method, url, json=None, headers=None, timeout=None):
    path = url.replace(API_BASE_URL, "")
    calls.append((method, path, json))
    if path == "auth/token/":
        return FakeResponse(*token_reply["value"])
    if path == "catalog/categories/":
        return FakeResponse(200, CATEGORIES)
    if path == "auth/register/":
        if json["password"].lower() == "password123":
            return FakeResponse(400, {"password": ["Esta contraseña es demasiado común.",
                                                   "La contraseña es demasiado similar a la de correo electrónico."]})
        return FakeResponse(201, {"email": json["email"]})
    if path == "professionals/me/availability/":
        if fail_availability:
            return FakeResponse(400, {"work_start": ["Formato de hora inválido."]})
        return FakeResponse(200, json)
    return FakeResponse(404, {"detail": "No encontrado."})


requests.request = fake_request


def login_app():
    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    at.session_state["show_login"] = True
    return at.run()


def login(at, email, password):
    at.text_input(key="login_email").input(email)
    at.text_input(key="login_password").input(password)
    next(b for b in at.button if b.label == "Ingresar").click().run()


def fill_register(at, email, rut, trade, password):
    at.radio(key="register_role").set_value("Profesional").run()
    at.text_input(key="register_name").input("Paula")
    at.text_input(key="register_lastname").input("Rojas")
    at.text_input(key="register_rut").input(rut)
    at.text_input(key="register_email").input(email)
    at.text_input(key="register_phone").input("+56 9 8765 4321")
    at.text_input(key="register_address").input("Av. Siempre Viva 742")
    at.selectbox(key="register_trade").select(trade)
    at.multiselect(key="register_coverage").select("Santiago").select("Ñuñoa")
    at.text_input(key="register_password").input(password)
    at.text_input(key="register_confirm").input(password)
    at.checkbox(key="register_privacy").check()
    at.button(key="register_button").click().run()


def free_rut():
    """Un RUT válido que no esté en la base local."""
    conn = db.get_connection()
    used = {r["rut"] for r in conn.execute("SELECT rut FROM users WHERE rut IS NOT NULL")}
    conn.close()
    for number in range(23456789, 23460000):
        total, factor = 0, 2
        for digit in reversed(str(number)):
            total += int(digit) * factor
            factor = 2 if factor == 7 else factor + 1
        dv = {11: "0", 10: "K"}.get(11 - total % 11, str(11 - total % 11))
        rut = f"{number}-{dv}"
        if db_rut(rut) not in used:
            return rut


def db_rut(rut):
    from core.security import normalize_rut
    return normalize_rut(rut)


RUT = free_rut()


def errors(at):
    return " ".join(str(e.value) for e in at.error)


PRO_USER = U["carlos"]
PID = db.get_professional_by_user(PRO_USER)["id"]


def open_coverage():
    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    at.session_state["authenticated"] = True
    at.session_state["user_id"] = PRO_USER
    at.session_state["api_access"] = "token-de-prueba"
    at.session_state["professional_navigation"] = "📍 Cobertura"
    return at.run()


if use_api():
    # ---------- Registro de profesional ----------
    calls.clear()
    at = login_app()
    fill_register(at, "paula.pintora@prueba.cl", RUT, "Pintura", "Clave1234")
    check(not any(p == "auth/register/" for _, p, _ in calls),
          "[api] oficio que el backend no tiene: no se envía el registro")
    check("«Pintura» todavía no está disponible en el servidor" in errors(at)
          and "Electricidad" in errors(at) and "Gasfitería" in errors(at),
          "[api] avisa con un mensaje claro y lista los oficios disponibles")
    check(db.get_user_by_email("paula.pintora@prueba.cl") is None, "[api] no se crea el espejo local")

    calls.clear()
    at = login_app()
    fill_register(at, "paula.gasfiter@prueba.cl", RUT, "Gasfitería", "Password123")
    msg = errors(at)
    check("La contraseña no cumple las reglas de seguridad del servidor" in msg
          and "- Esta contraseña es demasiado común." in msg
          and "- La contraseña es demasiado similar" in msg and "Contraseña:" not in msg,
          "[api] contraseña débil: las reglas del backend se muestran como lista legible")

    calls.clear()
    at = login_app()
    fill_register(at, "paula.gasfiter@prueba.cl", RUT, "Gasfitería", "Clave1234")
    sent = next((body for m, p, body in calls if p == "auth/register/"), None)
    profile = (sent or {}).get("professional_profile", {})
    check(not at.exception and sent is not None, "[api] oficio que sí existe: se envía el registro")
    check(profile.get("coverage_communes") == ["Santiago", "Ñuñoa"], "[api] envía coverage_communes")
    check(profile.get("categories") == [{"category": 2, "years_experience": 0}],
          "[api] envía categories con el id del backend (Gasfitería = 2)")
    check("latitude" not in json.dumps(sent) and "service_latitude" not in json.dumps(sent),
          "[api] no envía coordenadas")
    mirror = db.get_user_by_email("paula.gasfiter@prueba.cl")
    check(mirror is not None and db.get_professional_by_user(mirror["id"]) is not None,
          "[api] crea el espejo local con su perfil profesional")

    # ---------- Login: 401 y 429 ----------
    token_reply["value"] = (401, {"detail": "Credenciales inválidas."})
    at = login_app()
    login(at, "nadie@prueba.cl", "Clave1234")
    check("5 minutos" in errors(at) and "6 horas" not in texts(at), "[api] el aviso de bloqueo dice 5 minutos, no 6 horas")

    failures_before = db.count_login_failures("bloqueada@prueba.cl")
    token_reply["value"] = (429, {"detail": "La cuenta está temporalmente bloqueada.", "retry_after": 241})
    at = login_app()
    login(at, "bloqueada@prueba.cl", "Clave1234")
    check("Cuenta bloqueada por intentos fallidos. Intenta de nuevo en 5 minutos." in errors(at),
          "[api] 429: «Cuenta bloqueada… en 5 minutos» (241 s redondeado hacia arriba)")
    check("retry_after" not in texts(at) and "temporalmente bloqueada" not in texts(at),
          "[api] 429: sin el texto crudo del backend")
    check(db.count_login_failures("bloqueada@prueba.cl") == failures_before,
          "[api] 429: no cuenta como otro intento fallido local")

    token_reply["value"] = (429, {"detail": "La cuenta está temporalmente bloqueada.", "retry_after": 45})
    at = login_app()
    login(at, "bloqueada2@prueba.cl", "Clave1234")
    check("Intenta de nuevo en 1 minuto." in errors(at), "[api] 429 con menos de un minuto: «1 minuto»")

    # ---------- Disponibilidad con días completos ----------
    calls.clear()
    at = open_coverage()
    at.button(key="save_coverage").click().run()
    sent = next((body for m, p, body in calls if m == "PATCH" and p == "professionals/me/availability/"), None)
    local_days = db.get_professional_by_id(PID)["work_days"].split(",")
    check(not at.exception and sent is not None, "[api] guardar cobertura envía la disponibilidad al backend")
    check(sent and sent["work_days"] == [DIAS_COMPLETOS[d] for d in local_days]
          and all(d in DIAS_COMPLETOS.values() for d in sent["work_days"]),
          f"[api] días con nombre completo: {sent and sent['work_days']}")
    check(sent and sent["work_start"] and sent["coverage_communes"] and "latitude" not in sent,
          "[api] envía horario y comunas, sin coordenadas")

    fail_availability.append(True)
    before = dict(db.get_professional_by_id(PID))
    at = open_coverage()
    at.button(key="save_coverage").click().run()
    check("No se pudo guardar tu disponibilidad en el servidor" in errors(at)
          and dict(db.get_professional_by_id(PID)) == before,
          "[api] si el backend rechaza la disponibilidad, no se guarda en local")
    fail_availability.clear()

else:
    # ---------- Modo local: igual que antes y sin red ----------
    calls.clear()
    at = login_app()
    fill_register(at, "paula.pintora@prueba.cl", RUT, "Pintura", "Clave1234")
    mirror = db.get_user_by_email("paula.pintora@prueba.cl")
    check(not at.exception and mirror is not None and db.get_professional_by_user(mirror["id"]) is not None,
          "[local] registra un profesional de Pintura en la base local")

    at = login_app()
    login(at, "cliente@overol.cl", "clave-incorrecta")
    check("Te quedan" in errors(at) and "6 horas" not in texts(at), "[local] login fallido muestra los intentos restantes")

    at = open_coverage()
    at.button(key="save_coverage").click().run()
    check(not at.exception and any("Cobertura, días, horario y tarifa actualizados" in t.value for t in at.toast),
          "[local] guardar cobertura funciona")
    check(calls == [], f"[local] ninguna petición a la red ({len(calls)})")

terminar()
