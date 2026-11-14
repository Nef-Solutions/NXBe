"""Etapa C2: suscripción con Webpay (formulario POST con token_ws, vuelta con ?status= sin confiar
en el parámetro, con y sin sesión), catálogo según la suscripción, cédula y mensajes de verificación."""

import os
from datetime import datetime, timedelta, timezone

import streamlit

from comun import backend, calls, card_ids, check, errors, new_app, preparar, terminar, texts, toasts

front = preparar()

from streamlit.testing.v1 import AppTest  # noqa: E402

PRO = "profesional1@demo.overol.cl"
CLIENTE = "cliente1@demo.overol.cl"
pro = backend.professional(PRO)
iframes = []
streamlit.iframe = lambda html, **_: iframes.append(html)


def subscription_page(**state):
    return new_app(front, PRO, professional_navigation="💳 Suscripción", **state)


def back_from_webpay(params, email=None):
    """La vuelta de Webpay abre una sesión nueva de Streamlit con ?status=... en la URL."""
    at = new_app(front, email, run=False)
    for key, value in params.items():
        at.query_params[key] = value
    return at.run()


# ---------- Suscripción vigente ----------
at = subscription_page()
check(not at.exception and calls("GET", "/payments/professional-subscription/"), "pide GET /payments/professional-subscription/")
check(at.metric[0].value == "Vigente" and at.metric[2].value == "$10.000", "muestra estado y monto del backend")
check(any(b.key == "sub_pay" and "Renovar" in b.label for b in at.button) and "no apareces en el catálogo" not in texts(at),
      "vigente: ofrece renovar y no muestra el aviso del catálogo")

# ---------- Vencida: aviso y fuera del catálogo ----------
pro["subscription_expires_at"] = datetime.now(timezone.utc) - timedelta(days=1)
at = subscription_page()
check(at.metric[0].value == "Vencida" and "no apareces en el catálogo" in texts(at), "vencida: avisa que no aparece en el catálogo")
cat = new_app(front, CLIENTE, client_navigation="🔎 Buscar profesionales")
check(pro["id"] not in card_ids(cat), "el catálogo del backend ya no lo muestra")

# ---------- Pagar con Webpay: formulario POST con token_ws ----------
iframes.clear()
at.button(key="sub_pay").click().run()
started = backend.payments[max(backend.payments)]
html = " ".join(iframes)
check(calls("POST", "/payments/professional-subscription/transbank/") and started["status"] == "PENDING",
      "inicia el pago en el backend (POST .../transbank/)")
check('method="post"' in html and "webpay3gint.transbank.cl" in html and 'name="token_ws"' in html
      and f'value="{started["token"]}"' in html and 'target="_top"' in html,
      "formulario POST a la url de Webpay con token_ws, en la página completa")
check(started["token"] not in str(calls("GET")), "el token no viaja en ninguna URL")

at = subscription_page(**{"_webpay_pending": None})
at.button(key="sub_pay").click().run()
check("Ya existe un pago de suscripción pendiente." in errors(at), "con un pago pendiente: muestra el 409 del backend")

# ---------- Vuelta de Webpay con sesión restaurada ----------
params = backend.webpay_return(started["token"], "authorized")
at = back_from_webpay(params, PRO)
check(not at.exception and at.session_state["professional_navigation"] == "💳 Suscripción",
      "al volver, abre «Suscripción»")
check(any("Pago confirmado" in s.value for s in at.success) and at.metric[0].value == "Vigente",
      "muestra el resultado consultando el estado real (vigente)")
check("status" not in at.query_params, "limpia ?status= de la URL")

# ---------- El parámetro no se cree: la URL dice «authorized», el backend dice rechazado ----------
pro["subscription_expires_at"] = None
started = backend.payments[max(backend.payments)]
at = subscription_page(**{"_webpay_pending": None})
at.button(key="sub_pay").click().run()
token = backend.payments[max(backend.payments)]["token"]
params = backend.webpay_return(token, "rejected")
params["status"] = "authorized"  # alguien edita la URL
at = back_from_webpay(params, PRO)
check(not any("Pago confirmado" in s.value for s in at.success) and "no se completó (estado: rechazado)" in errors(at)
      and at.metric[0].value == "Sin suscripción", "URL alterada: manda el estado real del backend (rechazado)")

# ---------- Vuelta sin sesión (no marcó «Mantener mi sesión») ----------
at = subscription_page(**{"_webpay_pending": None})
at.button(key="sub_pay").click().run()
token = backend.payments[max(backend.payments)]["token"]
params = backend.webpay_return(token, "authorized")
at = back_from_webpay(params)
check(not at.exception and "Volviste de Webpay. Inicia sesión" in texts(at) and any(w.key == "login_email" for w in at.text_input),
      "sin sesión: pide iniciar sesión con un aviso")
at.text_input(key="login_email").input(PRO)
at.text_input(key="login_password").input("OverolDemo123!")
next(b for b in at.button if b.label == "Ingresar").click().run()
check(any("Pago confirmado" in s.value for s in at.success), "después de ingresar ve el resultado del pago")

# ---------- Cédula ----------
class Upload:
    def __init__(self, name, data, kind):
        self.name, self._data, self.type = name, data, kind

    def getvalue(self):
        return self._data


uploads = {}
from streamlit.delta_generator import DeltaGenerator  # noqa: E402

# AppTest no sube archivos: el selector devuelve el archivo preparado para su key
DeltaGenerator.file_uploader = lambda self, label, key=None, **_: uploads.get(key)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
PDF = b"%PDF-1.4\n" + b"0" * 100 + b"\n%%EOF"

pending = "pendiente@demo.overol.cl"
at = new_app(front, pending, professional_navigation="🪪 Verificación")
check(not at.exception and calls("GET", "/auth/verification/documents/") and "⏳ falta" in texts(at),
      "muestra qué lados de la cédula faltan (GET /auth/verification/documents/)")

uploads.update(ver_front=Upload("frente.png", b"\xff\xd8\xff" + b"0" * 50, "image/png"))
at.button(key="ver_send").click().run()
check("no parece un PNG válido" in errors(at) and not calls("POST", "/auth/verification/documents/"),
      "un .png que no es PNG: no se envía")
uploads.update(ver_front=Upload("frente.png", b"\x89PNG" + b"0" * (5 * 1024 * 1024 + 1), "image/png"))
at.button(key="ver_send").click().run()
check("supera 5 MB" in errors(at), "imagen de más de 5 MB: no se envía")
uploads.update(ver_front=Upload("frente.png", PNG, "image/png"), ver_back=Upload("reverso.pdf", PDF, "application/pdf"))
at.button(key="ver_send").click().run()
p = backend.professional(pending)
check(p.get("id_front") == "frente.png" and p.get("id_back") == "reverso.pdf" and "Documentos enviados" in toasts(at),
      "envía ambos lados por multipart (PNG y PDF)")
uploads.clear()
at = new_app(front, pending, professional_navigation="🪪 Verificación")
check(texts(at).count("✅ cargado") == 2, "después muestra ambos lados cargados")

# ---------- Mensajes de verificación ----------
at.button(key="ver_message_send").click().run()
check("Escribe un mensaje" in texts(at), "mensaje vacío: no se envía")
at.text_area(key="ver_message").input("Subí la cédula por ambos lados")
at.button(key="ver_message_send").click().run()
check(calls("POST", "/auth/verification/messages/") and p["messages"][-1]["message"] == "Subí la cédula por ambos lados",
      "envía el mensaje (POST /auth/verification/messages/)")
p["messages"][-1].update(admin_response="Recibido, lo revisamos hoy", resolved_at=datetime.now(timezone.utc).isoformat())
at = new_app(front, pending, professional_navigation="🪪 Verificación")
check("Subí la cédula" in texts(at) and "Recibido, lo revisamos hoy" in texts(at), "muestra el hilo con la respuesta de Overol")

terminar()
