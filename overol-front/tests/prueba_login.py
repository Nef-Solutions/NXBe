"""Login contra el backend (401, bloqueo 429 con retry_after, sin contador local) y sesión
persistente: la cookie lleva solo un identificador aleatorio, el token de renovación vive en
la memoria del servidor, se restaura al recargar, rota, se borra al cerrar sesión y se pierde
si el servidor se reinicia. Modo demo vs producción (OVEROL_MODO_DEMO) y cookie Secure
(OVEROL_COOKIE_SECURE)."""

import os

import streamlit

from comun import backend, calls, check, errors, md, new_app, preparar, terminar, texts, toasts

front = preparar()

from streamlit.testing.v1 import AppTest  # noqa: E402

import core.session as session  # noqa: E402

CLIENTE = "cliente1@demo.overol.cl"
PASSWORD = "OverolDemo123!"
cookie_html = []  # lo que escribe render_cookie_script en el navegador
streamlit.iframe = lambda html, **_: cookie_html.append(html)


def login_page(cookie=None):
    session.read_session_cookie = lambda: cookie
    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    at.session_state["show_login"] = True
    return at.run()


def login(at, email, password, remember=True):
    at.text_input(key="login_email").input(email)
    at.text_input(key="login_password").input(password)
    if not remember:
        at.checkbox(key="login_remember").uncheck()
    next(b for b in at.button if b.label == "Ingresar").click().run()
    return at


def reload_page(cookie):
    """Simula recargar la página: sesión de Streamlit nueva con la cookie del navegador."""
    session.read_session_cookie = lambda: cookie
    streamlit.cache_data.clear()
    return AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60).run()


def stored():
    return dict(session._store()["sessions"])


# ---------- Producción (por defecto): sin cuentas de demostración ----------
os.environ.pop("OVEROL_MODO_DEMO", None)
at = login_page()
page = md(at) + " " + texts(at) + " " + " ".join(c.value for c in at.code)
check(not at.exception and not any((b.key or "").startswith("demo_") for b in at.button),
      "producción: el login no tiene botones de usuarios de demostración")
check(PASSWORD not in page and "@demo.overol.cl" not in page and "usuarios de demostración" not in page.lower()
      and "seed_demo" not in page and not at.code,
      "producción: no aparece la clave, ningún correo de demo ni el texto de cuentas demo")
os.environ["OVEROL_MODO_DEMO"] = "0"
at = login_page()
check(not any((b.key or "").startswith("demo_") for b in at.button), "OVEROL_MODO_DEMO=0: tampoco aparecen")

# ---------- Modo demo (OVEROL_MODO_DEMO=1): usuarios de demostración ----------
os.environ["OVEROL_MODO_DEMO"] = "1"
at = login_page()
at.button(key="demo_cliente").click().run()
check(at.text_input(key="login_email").value == CLIENTE and at.text_input(key="login_password").value == PASSWORD,
      "los botones de demostración completan un usuario de seed_demo")
check("OverolDemo123!" in md(at) or any("OverolDemo123!" in c.value for c in at.code),
      "la pantalla muestra la contraseña de los usuarios de seed_demo")
check(any("Olvidaste" in (e.label or "") for e in at.expander), "«¿Olvidaste tu contraseña?» está disponible")
os.environ.pop("OVEROL_MODO_DEMO", None)

# ---------- 401 y bloqueo 429 (lo cuenta el backend, no el front) ----------
victim = "cliente2@demo.overol.cl"
at = login_page()
login(at, victim, "clave-incorrecta")
check("Correo o contraseña incorrectos" in errors(at) and "5 minutos" in errors(at) and "6 horas" not in texts(at),
      "clave incorrecta: mensaje con el aviso de 5 minutos")
for _ in range(2):
    login(at, victim, "clave-incorrecta")
login(at, victim, PASSWORD)
check("Cuenta bloqueada por intentos fallidos. Intenta de nuevo en 5 minutos." in errors(at),
      "tras 3 fallos el backend responde 429: «Intenta de nuevo en 5 minutos» (aunque la clave sea correcta)")
check("retry_after" not in texts(at) and "temporalmente bloqueada" not in texts(at), "429 sin el texto crudo")
check(not at.session_state["authenticated"] and not calls("GET", "/auth/me/"), "bloqueado: no entra")
backend.by_email(victim)["locked_until"] = 0
backend.by_email(victim)["failed"] = 0

# ---------- Login con «Mantener sesión»: cookie solo con un identificador ----------
cookie_html.clear()
before = stored()
at = login(login_page(), CLIENTE, PASSWORD)
token = at.session_state["session_token"] if "session_token" in at.session_state else None
refresh = at.session_state["api_refresh"]
new_entries = {k: v for k, v in stored().items() if k not in before}
check(not at.exception and at.session_state["authenticated"] and at.session_state["me"]["email"] == CLIENTE,
      "login correcto: el usuario sale de GET /auth/me/")
check(calls("GET", "/auth/me/"), "pidió /auth/me/ al backend")
check(token and len(token) >= 40 and "acc-" not in token and "ref-" not in token and token != refresh,
      "el identificador de la cookie es aleatorio y no es un token del backend")
check(len(new_entries) == 1 and list(new_entries.values())[0]["refresh"] == refresh and token not in stored(),
      "el token de renovación vive en la memoria del servidor (indexado por el hash del identificador)")
script = " ".join(cookie_html)
check(f"overol_session={token}" in script and "SameSite=Lax" in script and refresh not in script
      and CLIENTE not in script and "acc-" not in script,
      "la cookie lleva solo el identificador, con SameSite y sin tokens ni datos personales")
check("location.protocol === 'https:'" in script and "const s = '; Secure';" not in script,
      "sin OVEROL_COOKIE_SECURE: Secure solo si la página carga por https (en local funciona por http)")

# ---------- OVEROL_COOKIE_SECURE=1: la cookie siempre lleva Secure ----------
os.environ["OVEROL_COOKIE_SECURE"] = "1"
cookie_html.clear()
at_secure = login(login_page(), CLIENTE, PASSWORD)
script_secure = " ".join(cookie_html)
check(at_secure.session_state["authenticated"] and "const s = '; Secure';" in script_secure
      and "SameSite=Lax" in script_secure and CLIENTE not in script_secure,
      "OVEROL_COOKIE_SECURE=1: la cookie lleva Secure y SameSite=Lax, sin datos personales")
os.environ.pop("OVEROL_COOKIE_SECURE", None)

# ---------- Recargar la página: la sesión se restaura ----------
at = reload_page(token)
rotated = stored()[session._hash(token)]["refresh"]
check(not at.exception and at.session_state["authenticated"] and at.session_state["me"]["email"] == CLIENTE
      and "client_navigation_btn_0" in [b.key for b in at.button],
      "al recargar con la cookie, entra sin pedir la contraseña")
check(rotated != refresh and refresh in backend.blacklist,
      "el backend rotó el token de renovación y el nuevo quedó guardado en memoria")

# ---------- Identificador desconocido o servidor reiniciado ----------
cookie_html.clear()
at = reload_page("x" * 43)
check(not at.exception and not at.session_state["authenticated"] and "max-age=0" in " ".join(cookie_html),
      "un identificador desconocido no abre sesión y borra la cookie")
session._store.clear()  # el servidor de Streamlit se reinicia: la memoria se pierde
at = reload_page(token)
check(not at.exception and not at.session_state["authenticated"],
      "si el servidor se reinicia, la cookie ya no sirve: hay que ingresar de nuevo")

# ---------- Sin «Mantener sesión» ----------
cookie_html.clear()
before = stored()
at = login(login_page(), CLIENTE, PASSWORD, remember=False)
check(at.session_state["authenticated"] and "session_token" not in at.session_state and stored() == before
      and "max-age=0" in " ".join(cookie_html), "sin «Mantener sesión»: no guarda nada en el servidor y borra la cookie")

# ---------- Cerrar sesión ----------
at = login(login_page(), CLIENTE, PASSWORD)
token = at.session_state["session_token"]
refresh = at.session_state["api_refresh"]
cookie_html.clear()
at.button(key="logout_button").click().run()
check(session._hash(token) not in stored() and refresh in backend.blacklist and "max-age=0" in " ".join(cookie_html),
      "cerrar sesión borra la memoria del servidor, anula el token en el backend y la cookie")
at = reload_page(token)
check(not at.session_state["authenticated"], "después de cerrar sesión, la cookie vieja no abre sesión")

# ---------- El acceso vence durante la sesión: se renueva solo ----------
at = login(login_page(), CLIENTE, PASSWORD)
backend.expire_access()
at.session_state["_me_loaded_at"] = 0
at.run()
check(not at.exception and at.session_state["authenticated"], "acceso vencido: se renueva y sigue la sesión")

# ---------- Cuenta desactivada con la sesión abierta ----------
# (una cuenta SUSPENDED sigue con is_active=True en el backend y su token sirve: PEDIDO 0.4)
backend.by_email(CLIENTE)["account_status"] = "DEACTIVATED"
at.session_state["_me_loaded_at"] = 0
at.run()
check(not at.exception and not at.session_state["authenticated"] and "Tu sesión terminó" in toasts(at),
      "cuenta desactivada: la sesión se cierra con un aviso")
backend.by_email(CLIENTE)["account_status"] = "SUSPENDED"
at = login(login_page(), CLIENTE, PASSWORD)
check("Correo o contraseña incorrectos" in errors(at), "cuenta suspendida: no puede volver a entrar")
backend.by_email(CLIENTE)["account_status"] = "ACTIVE"

terminar()
