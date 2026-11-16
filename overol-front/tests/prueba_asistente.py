"""Asistente Overil (POST /api/assistant/chat/): se abre con el círculo fijo y el chat va en un
panel lateral derecho. Cliente y profesional, historial solo en la sesión (se mantiene al cambiar
de sección), advertencia de datos personales, límites (429), backend no disponible (503), cierre
con la X o con el círculo, y sin sesión el panel pide iniciar sesión."""

from comun import backend, calls, check, keys, new_app, preparar, terminar, texts

front = preparar()

CLIENTE, PRO, ADMIN = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl", "admin@demo.overol.cl"


def chat_texts(at):
    return " ".join(str(m.value) for m in at.markdown) + " " + texts(at)


def send(at, text):
    at.chat_input(key="assistant_input").set_value(text).run()
    return at


def panel_open(at):
    return bool(at.session_state["_overil_open"]) if "_overil_open" in at.session_state else False


def open_panel(at):
    at.button(key="overil_toggle").click().run()
    return at


# ---------- Círculo y panel ----------
at = new_app(front, CLIENTE)
check(not at.exception and "overil_toggle" in keys(at, "overil") and not panel_open(at)
      and not [c for c in at.chat_input if c.key == "assistant_input"], "con sesión: el círculo está y el panel parte cerrado")
check(not any("Asistente" in (b.label or "") for b in at.sidebar.button), "«Asistente» no está en el menú lateral")
open_panel(at)
check(panel_open(at) and "overil_close" in keys(at, "overil") and [c for c in at.chat_input if c.key == "assistant_input"],
      "al pulsar el círculo se abre el panel con el chat")
check(not at.exception and "No escribas datos personales" in texts(at) and "Google" in texts(at),
      "advierte no escribir datos personales (el texto se procesa con Google)")

send(at, "Gotea la llave del lavaplatos")
body = (calls("POST", "/assistant/chat/") or [(None, None, {})])[-1][2]
check(body == {"message": "Gotea la llave del lavaplatos"}, "envía POST /assistant/chat/ con el mensaje")
check("Gotea la llave del lavaplatos" in chat_texts(at) and "te recomiendo contactar" in chat_texts(at),
      "muestra la pregunta y la respuesta")
check(panel_open(at), "el panel sigue abierto después de enviar")
send(at, "¿Y si además huele a humedad?")
check(len(at.session_state["assistant_history"]) == 4, "el historial se guarda en la sesión")

at.sidebar.button(key="side_client_navigation_btn_2").click().run()
check(not at.exception and panel_open(at) and len(at.session_state["assistant_history"]) == 4
      and "Gotea la llave del lavaplatos" in chat_texts(at), "al cambiar de sección se mantiene la conversación")

at.button(key="overil_close").click().run()
check(not panel_open(at) and not [c for c in at.chat_input if c.key == "assistant_input"]
      and len(at.session_state["assistant_history"]) == 4, "la X cierra el panel y la conversación se conserva")
open_panel(at)
check(panel_open(at) and "Gotea la llave del lavaplatos" in chat_texts(at), "al reabrir, la conversación sigue ahí")
open_panel(at)
check(not panel_open(at), "pulsar de nuevo el círculo también cierra el panel")

open_panel(at)
at.button(key="assistant_clear").click().run()
check(at.session_state["assistant_history"] == [] and "assistant_clear" not in keys(at, "assistant"),
      "«Borrar conversación» la vacía")

at = new_app(front, CLIENTE)
check("assistant_history" not in at.session_state or at.session_state["assistant_history"] == [],
      "una sesión nueva empieza sin historial (el backend no lo guarda)")

# ---------- Límite (429) ----------
open_panel(at)
for i in range(3):
    send(at, f"Consulta {i}")
send(at, "Una más")
check("límite de consultas del asistente" in chat_texts(at), "429: avisa el límite y no reintenta")
check(backend.assistant_use[backend.by_email(CLIENTE)["id"]] == 5, "no hizo más peticiones que las del usuario")

# ---------- No disponible (503) ----------
backend.assistant_down = True
at = open_panel(new_app(front, PRO))
send(at, "Se cortó la luz en la cocina")
check(not at.exception and "El asistente no está disponible en este momento" in chat_texts(at),
      "503: mensaje claro (profesional)")
backend.assistant_down = False

# ---------- Sin sesión: el panel pide iniciar sesión ----------
calls_before = len(calls("POST", "/assistant/chat/"))
at = new_app(front)
check(not at.exception and "overil_toggle" in keys(at, "overil"), "sin sesión: el círculo también se muestra")
open_panel(at)
check(panel_open(at) and "inicia sesión" in texts(at) and not [c for c in at.chat_input if c.key == "assistant_input"]
      and len(calls("POST", "/assistant/chat/")) == calls_before, "sin sesión: el panel pide iniciar sesión y no hay chat")
at.button(key="overil_login").click().run()
check(not at.exception and at.session_state["show_login"] and not panel_open(at)
      and "login_email" in [w.key for w in at.text_input], "«Iniciar sesión» del panel lleva a la pantalla de ingreso")

# ---------- Administrador ----------
at = new_app(front, ADMIN)
check(not at.exception and "overil_toggle" not in keys(at, "overil"), "el administrador no tiene el círculo del asistente")

terminar()
