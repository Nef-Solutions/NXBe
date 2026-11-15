"""Pago de la suscripción mensual del profesional con Webpay Plus (sandbox), a través del backend.
Overol no intermedia el pago de las visitas: el cliente le paga directo al profesional.

Flujo: el backend inicia el pago y entrega `url` y `token`; el front envía un formulario
POST con `token_ws` a esa url (la página completa pasa a Webpay). Transbank vuelve al
backend, que confirma y redirige al front (PAYMENT_RESULT_URL) con `?status=...`.
Ese parámetro NO prueba el pago: el front siempre consulta el estado real a la API.

La vuelta abre una sesión nueva de Streamlit: si el usuario marcó «Mantener mi sesión»
se restaura sola; si no, se le pide ingresar y después se muestra el resultado.
"""

from html import escape

import streamlit as st

RETURN_KEY = "_payment_return"
PENDING_KEY = "_webpay_pending"
STATUS_TEXT = {
    "PENDING": "pendiente",
    "AUTHORIZED": "autorizado",
    "REJECTED": "rechazado",
    "FAILED": "fallido",
}


def capture_payment_return():
    """Si la URL trae la vuelta de Webpay, la guarda en la sesión y limpia la URL.
    Debe llamarse al inicio de cada ejecución, antes de crear las barras."""
    params = st.query_params
    if "status" not in params or "professional_profile_id" not in params:
        return

    st.session_state[RETURN_KEY] = {
        "status": params.get("status", ""),
        "professional_profile_id": params.get("professional_profile_id"),
    }
    for key in ("status", "professional_profile_id"):
        if key in params:
            del params[key]


def pending_return():
    return st.session_state.get(RETURN_KEY)


def route_payment_return(user):
    """Lleva a la pantalla donde se ve el resultado del pago (antes de crear la barra)."""
    data = pending_return()
    if not data or not user:
        return
    if data.get("professional_profile_id") and user["role"] == "profesional":
        st.session_state["professional_navigation"] = "💳 Suscripción"


def pop_return(kind):
    """Devuelve y borra la vuelta de Webpay de la suscripción (kind="subscription")."""
    data = pending_return()
    if not data:
        return None
    if (kind == "subscription") != bool(data.get("professional_profile_id")):
        return None
    return st.session_state.pop(RETURN_KEY)


def webpay_form(url, token, key):
    """Botones que envían el formulario POST con token_ws a Webpay (página completa o pestaña nueva)."""
    st.session_state[PENDING_KEY] = {"url": url, "token": token, "key": key}

    def form(target, label, primary):
        style = (
            "width:100%;padding:.6rem 1rem;border-radius:.5rem;font-weight:600;cursor:pointer;"
            + ("background:#F59E0B;color:#111827;border:none;" if primary else
               "background:white;color:#111827;border:1px solid #D1D5DB;")
        )
        return (
            f'<form method="post" action="{escape(url)}" target="{target}" style="margin:0 0 .5rem 0">'
            f'<input type="hidden" name="token_ws" value="{escape(token)}">'
            f'<button type="submit" style="{style}">{escape(label)}</button></form>'
        )

    html = (
        '<div style="font-family:sans-serif">'
        + form("_top", "Ir a Webpay para pagar", True)
        + form("_blank", "Abrir Webpay en otra pestaña", False)
        + "</div>"
    )
    try:
        if hasattr(st, "iframe"):
            st.iframe(html, height=110)
        else:
            import streamlit.components.v1 as components

            components.html(html, height=110)
    except Exception:
        st.markdown(f"[Abrir Webpay]({url})")

    st.caption(
        "Webpay está en modo de pruebas (sandbox): no se hace ningún cobro real. "
        "Al terminar volverás a Overol y verás el resultado."
    )


def payment_status_text(status):
    return STATUS_TEXT.get(status or "", status or "sin pagos")
