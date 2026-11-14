"""Asistente Overil (POST /api/assistant/chat/) para clientes y profesionales.

El backend no guarda la conversación: el historial vive solo en esta sesión de Streamlit.
Límites del backend: 5 consultas por hora, 10 al día por usuario y 50 al día en total.
"""

import streamlit as st

from core import api_client
from ui.components import section

HISTORY_KEY = "assistant_history"
MAX_MENSAJE = 1500


def _clear_history():
    st.session_state[HISTORY_KEY] = []


def assistant_page(user):
    section("🤖 Asistente Overil")

    st.info(
        "Cuéntale a Overil qué falla en tu hogar y te orienta sobre qué oficio necesitas. "
        "Sus respuestas son preliminares: ante gas, chispas o humo, aléjate y llama a emergencias."
    )
    st.warning(
        "🔒 **No escribas datos personales** (RUT, dirección, teléfono, claves): el texto se procesa "
        "con un servicio de Google para generar la respuesta."
    )

    history = st.session_state.setdefault(HISTORY_KEY, [])

    if not history:
        with st.chat_message("assistant"):
            st.write("¡Hola! Soy Overil. ¿Qué necesitas arreglar en tu hogar?")

    for role, text in history:
        with st.chat_message("user" if role == "user" else "assistant"):
            if role == "error":
                st.error(text)
            else:
                st.write(text)

    message = st.chat_input("Escribe tu consulta", max_chars=MAX_MENSAJE, key="assistant_input")

    if history:
        st.button("Borrar conversación", key="assistant_clear", on_click=_clear_history)

    if not message or not message.strip():
        return

    history.append(("user", message.strip()))
    try:
        history.append(("assistant", api_client.assistant_chat(message)))
    except api_client.ApiError as error:
        history.append(("error", _error_text(error)))
    st.rerun()


def _error_text(error):
    if error.status == 429:
        return (
            "Llegaste al límite de consultas del asistente (5 por hora y 10 por día). "
            f"Inténtalo más tarde. {error}"
        )
    if error.status == 503:
        return "El asistente no está disponible en este momento. Inténtalo más tarde."
    return f"No se pudo enviar tu consulta. {error}"
