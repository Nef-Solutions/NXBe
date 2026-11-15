"""Asistente Overil (POST /api/assistant/chat/): cliente y profesional, historial solo en la
sesión, advertencia de datos personales, límites (429) y backend no disponible (503)."""

from comun import backend, calls, check, keys, new_app, preparar, terminar, texts

front = preparar()

CLIENTE, PRO = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl"


def chat_texts(at):
    return " ".join(str(m.value) for m in at.markdown) + " " + texts(at)


def send(at, text):
    at.chat_input(key="assistant_input").set_value(text).run()
    return at


at = new_app(front, CLIENTE, client_navigation="🤖 Asistente")
check(not at.exception and "No escribas datos personales" in texts(at) and "Google" in texts(at),
      "advierte no escribir datos personales (el texto se procesa con Google)")

send(at, "Gotea la llave del lavaplatos")
body = (calls("POST", "/assistant/chat/") or [(None, None, {})])[-1][2]
check(body == {"message": "Gotea la llave del lavaplatos"}, "envía POST /assistant/chat/ con el mensaje")
check("Gotea la llave del lavaplatos" in chat_texts(at) and "te recomiendo contactar" in chat_texts(at),
      "muestra la pregunta y la respuesta")
send(at, "¿Y si además huele a humedad?")
check(len(at.session_state["assistant_history"]) == 4, "el historial se guarda en la sesión")
at.button(key="assistant_clear").click().run()
check(at.session_state["assistant_history"] == [] and "assistant_clear" not in keys(at, "assistant"),
      "«Borrar conversación» la vacía")

at = new_app(front, CLIENTE, client_navigation="🤖 Asistente")
check(at.session_state["assistant_history"] == [], "una sesión nueva empieza sin historial (el backend no lo guarda)")

# ---------- Límite (429) ----------
for i in range(3):
    send(at, f"Consulta {i}")
send(at, "Una más")
check("límite de consultas del asistente" in chat_texts(at), "429: avisa el límite y no reintenta")
check(backend.assistant_use[backend.by_email(CLIENTE)["id"]] == 5, "no hizo más peticiones que las del usuario")

# ---------- No disponible (503) ----------
backend.assistant_down = True
at = new_app(front, PRO, professional_navigation="🤖 Asistente")
send(at, "Se cortó la luz en la cocina")
check(not at.exception and "El asistente no está disponible en este momento" in chat_texts(at),
      "503: mensaje claro (profesional)")
backend.assistant_down = False

terminar()
