"""Navegación de los 4 roles, solo desde el menú lateral izquierdo (no hay barra superior), con
las pantallas pendientes de la API ocultas (PANTALLAS_PENDIENTES_API), perfil abierto que se
cierra al cambiar de sección, cerrar sesión, «Mi cuenta» y el círculo del asistente."""

from comun import backend, calls, check, keys, md, nav_labels, new_app, preparar, terminar, texts

front = preparar()

from core.constants import PANTALLAS_PENDIENTES_API  # noqa: E402

CLIENTE, PRO, ADMIN = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl", "admin@demo.overol.cl"
ROLES = {
    "visitante": (None, "visitor_navigation", ["🏠 Inicio", "🔎 Profesionales", "ℹ️ Quiénes somos"]),
    "cliente": (CLIENTE, "client_navigation",
                ["🏠 Inicio", "🔎 Buscar profesionales", "📋 Mis solicitudes", "🛠️ Mis reclamos",
                 "🔔 Notificaciones", "👤 Mi perfil", "ℹ️ Quiénes somos"]),
    "profesional": (PRO, "professional_navigation",
                    ["📋 Solicitudes", "🔔 Notificaciones", "👤 Mi perfil", "📍 Cobertura", "💳 Suscripción",
                     "🪪 Verificación", "🛠️ Reclamos", "🎓 Desarrollo profesional", "ℹ️ Quiénes somos"]),
    "admin": (ADMIN, "admin_navigation",
              ["📊 Indicadores", "🪪 Verificación", "👥 Usuarios", "🛠️ Reclamos", "💬 Soporte", "ℹ️ Quiénes somos"]),
}


def main_keys(at):
    return [b.key or "" for b in at.main.button]


for role, (email, nav, options) in ROLES.items():
    at = new_app(front, email)
    check(not at.exception and nav_labels(at, nav) == options, f"[{role}] menú lateral: {', '.join(options)}")
    hidden = PANTALLAS_PENDIENTES_API.get(role, {})
    check(not any(h in nav_labels(at, nav) for h in hidden), f"[{role}] oculta las {len(hidden)} pantallas pendientes")
    check(not keys(at, f"{nav}_btn_") and not any(k.startswith(f"side_{nav}_btn_") for k in main_keys(at)),
          f"[{role}] sin barra superior: las secciones están solo en el menú lateral")
    check(all(b.key.startswith(f"side_{nav}_btn_") for b in at.sidebar.button if nav in (b.key or "")),
          f"[{role}] los botones de sección están en el menú lateral izquierdo")

    others = [n for r, (_, n, _) in ROLES.items() if r != role]
    check(not any(keys(at, f"side_{n}_btn_") for n in others), f"[{role}] no aparecen las secciones de otro rol")

    ok = True
    for i, option in enumerate(options):
        at.sidebar.button(key=f"side_{nav}_btn_{i}").click().run()
        ok = ok and not at.exception and at.session_state[nav] == option
    check(ok, f"[{role}] todas las secciones abren sin excepción desde el menú lateral")
    check(not any("Asistente" in (b.label or "") for b in at.sidebar.button),
          f"[{role}] «Asistente» ya no está en la navegación")
    check(("overil_toggle" in keys(at, "overil")) == (role != "admin"),
          f"[{role}] círculo del asistente {'visible' if role != 'admin' else 'oculto (el admin no usa el asistente)'}")

# ---------- Visitante ----------
at = new_app(front)
check("go_login_top" in [b.key for b in at.sidebar.button], "[visitante] «Ingresar o registrarme» en el menú lateral")
check(not any(b.key == "logout_button" for b in at.button), "[visitante] sin «Cerrar sesión»")

# Pantalla de ingreso: el menú lateral sigue ofreciendo las secciones del visitante
at.sidebar.button(key="go_login_top").click().run()
check(not at.exception and "login_email" in [w.key for w in at.text_input]
      and keys(at, "side_visitor_navigation_btn_"), "[visitante] la pantalla de ingreso conserva el menú lateral")
at.sidebar.button(key="side_visitor_navigation_btn_1").click().run()
check(not at.exception and "show_login" not in at.session_state and at.session_state["visitor_navigation"] == "🔎 Profesionales"
      and "login_email" not in [w.key for w in at.text_input], "[visitante] desde el ingreso, el menú lateral vuelve a explorar")

# ---------- Cliente: perfil abierto se cierra al cambiar de sección ----------
PID = backend.professional(PRO)["id"]
at = new_app(front, CLIENTE)
at.sidebar.button(key="side_client_navigation_btn_1").click().run()
at.button(key=f"client_view_prof_{PID}").click().run()
check(any(b.key == "back_from_profile" for b in at.button), "[cliente] abre el perfil de un profesional")
at.sidebar.button(key="side_client_navigation_btn_0").click().run()
at.sidebar.button(key="side_client_navigation_btn_1").click().run()
check(not any(b.key == "back_from_profile" for b in at.button), "[cliente] al cambiar de sección el perfil se cierra")
at.button(key=f"client_view_prof_{PID}").click().run()
at.button(key="back_from_profile").click().run()
check(not at.exception and keys(at, "client_view_prof_"), "[cliente] «← Volver» regresa a la lista")

# ---------- Profesional: estado de verificación desde /auth/me/ ----------
at = new_app(front, PRO, professional_navigation="👤 Mi perfil")
check("Tu identidad está verificada" in texts(at), "[profesional] aprobado: lo dice su perfil")
at = new_app(front, "pendiente@demo.overol.cl", professional_navigation="👤 Mi perfil")
check("pendiente de verificación" in texts(at), "[profesional] pendiente: aviso de revisión")

# ---------- Admin: parte en Indicadores ----------
at = new_app(front, ADMIN)
check("Indicadores de la plataforma" in md(at), "[admin] parte en Indicadores")

# ---------- Cerrar sesión ----------
at = new_app(front, CLIENTE)
refresh = at.session_state["api_refresh"]
at.button(key="logout_button").click().run()
check(not at.exception and keys(at, "side_visitor_navigation_btn_") and not keys(at, "side_client_navigation_btn_"),
      "[cliente] «Cerrar sesión» vuelve a la vista de visitante")
check(any(b == {"refresh": refresh} for _, _, b in calls("POST", "/auth/logout/"))
      and refresh in backend.blacklist, "[cliente] cerrar sesión anula el token en el backend (POST /auth/logout/)")
check("api_access" not in at.session_state and "me" not in at.session_state, "[cliente] no quedan tokens ni datos en la sesión")
check("Clara Pérez" not in md(at), "[cliente] tras cerrar sesión no se muestran datos de la cuenta")


# ---------- Menú lateral: secciones del rol y opciones de la cuenta ----------
def side(at):
    return [b.key for b in at.sidebar.button]


def widget_keys(at):
    return {w.key for w in list(at.text_input) + list(at.selectbox)}


def section_keys(nav, n):
    return [f"side_{nav}_btn_{i}" for i in range(n)]


def side_sections(at, nav):
    return [b for b in at.sidebar.button if (b.key or "").startswith(f"side_{nav}_btn_")]


def sidebar_text(at):
    return " ".join(m.value for m in at.sidebar.markdown) + " ".join(c.value for c in at.sidebar.caption) \
        + " ".join(b.label for b in at.sidebar.button)


def current_marked(at, nav):
    """La sección actual va destacada (primary) en el menú lateral, y solo esa."""
    value = at.session_state[nav]
    marked = [b for b in side_sections(at, nav) if b.proto.type == "primary"]
    return len(marked) == 1 and marked[0].label.replace(" ", " ").startswith(value)


at = new_app(front)
check(side(at) == section_keys("visitor_navigation", 3) + ["go_login_top"],
      "[visitante] menú lateral: Inicio, Profesionales, Quiénes somos e Ingresar, sin opciones de cuenta")

# Cliente
NAV = "client_navigation"
N = len(ROLES["cliente"][2])
backend.notifications_add(backend.by_email(CLIENTE)["id"], "Aviso de prueba", "Para el contador del menú lateral.")
at = new_app(front, CLIENTE)
check(side(at) == section_keys(NAV, N) + ["side_contrasena", "logout_button"],
      "[cliente] menú lateral: las secciones, Cambiar contraseña y Cerrar sesión al final")
check("Rol:" not in sidebar_text(at), "[cliente] el menú lateral no muestra «Rol:»")
check("Editar datos" not in sidebar_text(at) and "side_editar" not in side(at), "[cliente] sin «Editar datos»")
check("Mi perfil" not in " ".join(b.label for b in at.sidebar.button if not (b.key or "").startswith("side_" + NAV)),
      "[cliente] «Mi perfil» no se repite en «Mi cuenta» (queda en las secciones)")
check("Requisitos contemplados" not in sidebar_text(at) and "RNF" not in sidebar_text(at), "[cliente] sin los bloques de requisitos")
check(any("Notificaciones" in b.label and "(" in b.label for b in side_sections(at, NAV)),
      "[cliente] el contador de notificaciones sin leer se ve en el menú lateral")
check(current_marked(at, NAV), "[cliente] la sección actual queda marcada en el menú lateral")

at.sidebar.button(key=f"side_{NAV}_btn_2").click().run()
check(not at.exception and at.session_state[NAV] == "📋 Mis solicitudes" and "Mis solicitudes" in md(at),
      "[cliente] el botón del menú lateral cambia de sección")
check(current_marked(at, NAV), "[cliente] tras cambiar desde el menú lateral, la nueva sección queda marcada")
check(at.session_state[f"_nav_shown_{NAV}"][0] == "📋 Mis solicitudes", "[cliente] el cambio de sección se registra (vuelve arriba)")

at.sidebar.button(key="side_contrasena").click().run()
check(at.session_state[NAV] == "👤 Mi perfil" and "pwd_current" in widget_keys(at)
      and "edit_phone" not in widget_keys(at) and "Cambiar contraseña" in md(at),
      "[cliente] «Cambiar contraseña» abre solo el cambio de contraseña")
at.sidebar.button(key=f"side_{NAV}_btn_0").click().run()
at.sidebar.button(key=f"side_{NAV}_btn_5").click().run()
check(at.session_state[NAV] == "👤 Mi perfil" and {"edit_phone", "pwd_current"} <= widget_keys(at)
      and "Mi perfil personal" in md(at), "[cliente] «Mi perfil» (sección) muestra los datos y la contraseña")

# Profesional
NAV = "professional_navigation"
N = len(ROLES["profesional"][2])
at = new_app(front, PRO)
check(side(at) == section_keys(NAV, N) + ["side_contrasena", "side_suscripción", "side_verificación", "logout_button"],
      "[profesional] secciones y, en «Mi cuenta», Cambiar contraseña, Suscripción y Verificación")
check("Rol:" not in sidebar_text(at) and "Editar datos" not in sidebar_text(at), "[profesional] sin «Rol:» ni «Editar datos»")
check(current_marked(at, NAV), "[profesional] la sección actual queda marcada")
at.sidebar.button(key="side_suscripción").click().run()
check(not at.exception and at.session_state[NAV] == "💳 Suscripción" and "Suscripción" in md(at) and current_marked(at, NAV),
      "[profesional] «Suscripción» abre su pantalla y queda marcada en las secciones")
at.sidebar.button(key="side_verificación").click().run()
check(not at.exception and at.session_state[NAV] == "🪪 Verificación", "[profesional] «Verificación» abre su pantalla")
at.sidebar.button(key="side_contrasena").click().run()
check(at.session_state[NAV] == "👤 Mi perfil" and "pwd_current" in widget_keys(at),
      "[profesional] «Cambiar contraseña» abre su perfil en esa sección")

# Administrador: no tiene «Mi perfil» entre sus secciones, así que lo conserva en «Mi cuenta»
NAV = "admin_navigation"
N = len(ROLES["admin"][2])
at = new_app(front, ADMIN)
check(side(at) == section_keys(NAV, N) + ["side_perfil", "side_contrasena", "logout_button"],
      "[admin] secciones y, en «Mi cuenta», Mi perfil (no está en sus secciones) y Cambiar contraseña")
check(not any("Moderación" in b.label or "Contenidos" in b.label or "Trazabilidad" in b.label for b in at.sidebar.button),
      "[admin] el menú lateral respeta las pantallas ocultas")
check("Rol:" not in sidebar_text(at) and "Editar datos" not in sidebar_text(at), "[admin] sin «Rol:» ni «Editar datos»")
at.sidebar.button(key=f"side_{NAV}_btn_4").click().run()
check(not at.exception and at.session_state[NAV] == "💬 Soporte" and current_marked(at, NAV),
      "[admin] el menú lateral cambia de sección y la marca")
at.sidebar.button(key="side_contrasena").click().run()
check(not at.exception and "pwd_current" in widget_keys(at), "[admin] «Cambiar contraseña» dentro de su panel")
at.button(key="admin_account_back").click().run()
check("pwd_current" not in widget_keys(at), "[admin] «← Volver al panel»")
at.sidebar.button(key="side_perfil").click().run()
check(not at.exception and "edit_phone" in widget_keys(at), "[admin] «Mi perfil» abre sus datos")

terminar()
