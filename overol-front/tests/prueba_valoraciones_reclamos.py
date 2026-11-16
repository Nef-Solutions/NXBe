"""Etapa D: el cliente evalúa al profesional, el profesional califica al cliente (POST /ratings/),
reclamos de posventa (crear, responder, mediación, resolución) y la tarifa como dato informativo
(Overol no cobra las visitas: el cliente le paga directo al profesional)."""

import streamlit

from comun import backend, calls, check, md, nav_labels, new_app, preparar, terminar, texts, toasts

front = preparar()
from core.constants import FEE_NOTE  # noqa: E402  (la copia del front queda en sys.path tras preparar)

CLIENTE, PRO = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl"
iframes = []
streamlit.iframe = lambda html, **_: iframes.append(html)


def client_requests():
    return new_app(front, CLIENTE, client_navigation="📋 Mis solicitudes")


def last_body(method, path):
    found = calls(method, path)
    return found[-1][2] if found else None


# ---------- El cliente evalúa un servicio finalizado ----------
VID = backend.add_visit(CLIENTE, PRO, status="COMPLETED")
at = client_requests()
check(not at.exception and any(b.key == f"send_rating_{VID}" for b in at.button), "finalizada: ofrece evaluar")
at.slider(key=f"rate_punctuality_{VID}").set_value(4)
at.text_area(key=f"rate_comment_{VID}").input("Llegó a la hora y dejó todo limpio")
at.button(key=f"send_rating_{VID}").click().run()
check(last_body("POST", "/ratings/") == {"visit": VID, "quality": 5, "punctuality": 4, "treatment": 5,
                                         "comment": "Llegó a la hora y dejó todo limpio"},
      "POST /ratings/ con las tres notas y el comentario")
check("Evaluación enviada" in toasts(at) and "Ya evaluaste este servicio" in texts(at), "ya no ofrece evaluar otra vez")
at = client_requests()
at.button(key=f"send_rating_{VID}").click().run()
check("Ya habías evaluado este servicio" in toasts(at) and "Ya evaluaste" in texts(at),
      "en una sesión nueva: el 400 del backend («ya fue calificado») se muestra como aviso")
pid = backend.professional(PRO)["id"]
at = new_app(front, CLIENTE, client_navigation="🔎 Buscar profesionales", _client_prev_menu="🔎 Buscar profesionales",
             selected_professional=pid)
check("Llegó a la hora y dejó todo limpio" in md(at), "la opinión aparece en el perfil público")
check(FEE_NOTE in md(at), "el perfil aclara que la tarifa se paga directo al profesional")

# ---------- El profesional califica al cliente ----------
at = new_app(front, PRO, professional_navigation="📋 Solicitudes")
at.button(key=f"save_client_rating_{VID}").click().run()
rating = backend.ratings[-1]
check(rating["author"] == backend.by_email(PRO)["id"] and rating["target"] == backend.by_email(CLIENTE)["id"]
      and "Calificación al cliente registrada" in toasts(at), "el profesional califica al cliente con el mismo endpoint")

# ---------- Reclamo de posventa ----------
at = client_requests()
at.button(key=f"send_claim_{VID}").click().run()
check("Debes describir el problema" in texts(at) and not calls("POST", "/claims/"), "el reclamo exige describir el problema")
at.text_area(key=f"claim_reason_{VID}").input("Volvió a gotear al día siguiente")
at.button(key=f"send_claim_{VID}").click().run()
claim = backend.claims[max(backend.claims)]
check(claim["visit"] == VID and claim["status"] == "OPEN" and f"Reclamo #{claim['id']} enviado" in toasts(at),
      "abre el reclamo (POST /claims/)")
at = client_requests()
check(f"Abriste el reclamo #{claim['id']}" in texts(at) and not any(b.key == f"send_claim_{VID}" for b in at.button),
      "no permite reclamar dos veces el mismo servicio")

# ---------- El profesional responde ----------
at = new_app(front, PRO, professional_navigation="🛠️ Reclamos")
check("🛠️ Reclamos (1)" in [b.label.replace(" ", " ") for b in at.button],
      "su menú lateral muestra el contador de reclamos abiertos")
at.button(key=f"respond_claim_{claim['id']}").click().run()
check("Escribe una respuesta" in texts(at), "la respuesta no puede ir vacía")
at.text_area(key=f"claim_response_{claim['id']}").input("Voy el lunes sin costo")
at.button(key=f"respond_claim_{claim['id']}").click().run()
check(claim["status"] == "PROFESSIONAL_RESPONDED" and claim["professional_response"] == "Voy el lunes sin costo",
      "responde (POST /claims/{id}/respond/)")
check(backend.notifications[-1]["title"] == "Respuesta de posventa", "el backend notifica al cliente")

# ---------- El cliente lo ve y pide mediación ----------
at = new_app(front, CLIENTE, client_navigation="🛠️ Mis reclamos")
check("Respondido por el profesional" in md(at) and "Voy el lunes sin costo" in texts(at), "«Mis reclamos» muestra la respuesta")
at.button(key=f"escalate_claim_{claim['id']}").click().run()
check(claim["status"] == "ESCALATED", "pide mediación (POST /claims/{id}/escalate/)")
claim.update(status="RESOLVED", admin_resolution="Se coordinó una segunda visita")
at = new_app(front, CLIENTE, client_navigation="🛠️ Mis reclamos")
check("Resuelto" in md(at) and "Se coordinó una segunda visita" in texts(at)
      and not any(b.key == f"escalate_claim_{claim['id']}" for b in at.button), "resuelto: muestra la resolución de Overol")

# ---------- Sin pago de visitas: la tarifa es informativa ----------
VID = backend.add_visit(CLIENTE, PRO, status="ACCEPTED")
at = client_requests()
check(not at.exception and FEE_NOTE in texts(at), "aceptada: aclara que la tarifa se paga directo al profesional")
check(not any(b.key.startswith("visit_pay_") for b in at.button if b.key)
      and not any("Pagar" in (b.label or "") for b in at.button), "no hay botón para pagar la visita")
check(not calls(prefix="/payments/visits/"), "el front no llama a /payments/visits/")

at = new_app(front, CLIENTE, run=False)
at.query_params["status"] = "authorized"
at.query_params["visit_id"] = str(VID)
at.run()
check(not at.exception and "_payment_return" not in at.session_state
      and not any("Pago confirmado" in s.value for s in at.success), "una vuelta de Webpay de visita se ignora")

check("🛠️ Mis reclamos" in nav_labels(client_requests(), "client_navigation"), "«Mis reclamos» está en el menú lateral del cliente")

terminar()
