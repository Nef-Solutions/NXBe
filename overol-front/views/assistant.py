"""Asistente Overil (POST /api/assistant/chat/) para clientes y profesionales.

Se abre con un círculo fijo al borde derecho de la pantalla, en todas las secciones, y el chat
aparece en un panel lateral derecho. Streamlit no tiene un panel derecho nativo: el círculo y el
panel son contenedores con key («st-key-overil_fab» y «st-key-overil_panel») que style.css fija
a la pantalla. El panel abierto o cerrado se guarda en la sesión.

El backend no guarda la conversación: el historial vive solo en esta sesión de Streamlit (se
mantiene al cambiar de sección). Límites del backend: 5 consultas por hora, 10 al día por usuario
y 50 al día en total.
"""

import streamlit as st

from core import api_client

HISTORY_KEY = "assistant_history"
OPEN_KEY = "_overil_open"
MAX_MENSAJE = 1500
ROLES_CON_ASISTENTE = ("cliente", "profesional")


def _clear_history():
    st.session_state[HISTORY_KEY] = []


def _toggle_panel():
    st.session_state[OPEN_KEY] = not st.session_state.get(OPEN_KEY, False)


def _close_panel():
    st.session_state[OPEN_KEY] = False


def _go_login():
    # Sin sesión: el panel lleva a la pantalla de ingreso
    st.session_state[OPEN_KEY] = False
    st.session_state["show_login"] = True


def assistant_launcher(user):
    """Círculo del asistente y, si está abierto, su panel. `user` es None sin sesión (el panel pide
    iniciar sesión, porque el backend lo exige). El administrador no usa el asistente."""
    if user is not None and user["role"] not in ROLES_CON_ASISTENTE:
        return

    is_open = st.session_state.get(OPEN_KEY, False)

    with st.container(key="overil_fab_open" if is_open else "overil_fab"):
        st.button(
            "🤖",
            key="overil_toggle",
            help="Cerrar el asistente Overil" if is_open else "Abrir el asistente Overil",
            on_click=_toggle_panel,
        )

    if not is_open:
        return

    with st.container(key="overil_panel"):
        head = st.columns([6, 1], vertical_alignment="center")
        with head[0]:
            st.markdown("#### 🤖 Asistente Overil")
        with head[1]:
            st.button("✕", key="overil_close", help="Cerrar el asistente", on_click=_close_panel)

        if user is None:
            st.info(
                "Overil te orienta sobre qué oficio necesitas para arreglar algo en tu hogar. "
                "Para usarlo, inicia sesión: el asistente atiende solo a cuentas registradas."
            )
            st.button("🔑 Iniciar sesión o registrarme", key="overil_login", type="primary",
                      use_container_width=True, on_click=_go_login)
            return

        assistant_chat(user)


def assistant_chat(user):
    """El chat de Overil (mismo contenido y lógica que tenía la sección «Asistente»)."""
    st.info(
        "Cuéntale a Overil qué falla en tu hogar y te orienta sobre qué oficio necesitas. "
        "Sus respuestas son preliminares: ante gas, chispas o humo, aléjate y llama a emergencias."
    )
    st.warning(
        "🔒 **No escribas datos personales** (RUT, dirección, teléfono, claves): el texto se procesa "
        "con un servicio de Google para generar la respuesta."
    )

    history = st.session_state.setdefault(HISTORY_KEY, [])

    with st.container(key="overil_history"):
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
