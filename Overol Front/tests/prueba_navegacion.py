"""Navegación de los 4 roles con las pantallas pendientes de la API ocultas
(PANTALLAS_PENDIENTES_API), perfil abierto que se cierra al cambiar de sección y cerrar sesión."""

from comun import backend, calls, check, keys, md, nav_labels, new_app, preparar, terminar, texts

front = preparar()

from core.constants import PANTALLAS_PENDIENTES_API  # noqa: E402

CLIENTE, PRO, ADMIN = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl", "admin@demo.overol.cl"
ROLES = {
    "visitante": (None, "visitor_navigation", ["🏠 Inicio", "🔎 Profesionales", "ℹ️ Quiénes somos"]),
    "cliente": (CLIENTE, "client_navigation",
                ["🏠 Inicio", "🔎 Buscar profesionales", "📋 Mis solicitudes", "🤖 Asistente", "🛠️ Mis reclamos",
                 "🔔 Notificaciones", "👤 Mi perfil", "ℹ️ Quiénes somos"]),
    "profesional": (PRO, "professional_navigation",
                    ["📋 Solicitudes", "🔔 Notificaciones", "👤 Mi perfil", "📍 Cobertura", "💳 Suscripción",
                     "🪪 Verificación", "🛠️ Reclamos", "🎓 Desarrollo profesional", "🤖 Asistente",
                     "ℹ️ Quiénes somos"]),
    "admin": (ADMIN, "admin_navigation",
              ["📊 Indicadores", "🪪 Verificación", "👥 Usuarios", "🛠️ Reclamos", "💬 Soporte", "ℹ️ Quiénes somos"]),
}

for role, (email, nav, options) in ROLES.items():
    at = new_app(front, email)
    check(not at.exception and nav_labels(at, nav) == options, f"[{role}] barra: {', '.join(options)}")
    hidden = PANTALLAS_PENDIENTES_API.get(role, {})
    check(not any(h in nav_labels(at, nav) for h in hidden), f"[{role}] oculta las {len(hidden)} pantallas pendientes")

    others = [n for r, (_, n, _) in ROLES.items() if r != role]
    check(not any(keys(at, n + "_btn_") for n in others), f"[{role}] no aparece la barra de otro rol")

    ok = True
    for i, option in enumerate(options):
        at.button(key=f"{nav}_btn_{i}").click().run()
        ok = ok and not at.exception and at.session_state[nav] == option
    check(ok, f"[{role}] todas las secciones abren sin excepción")
    has_assistant = any("Asistente" in (b.label or "") for b in at.button)
    check(has_assistant == (role in ("cliente", "profesional")),
          f"[{role}] «Asistente» {'disponible' if role in ('cliente', 'profesional') else 'no disponible'}")

# ---------- Visitante ----------
at = new_app(front)
check("go_login_top" in keys(at, "go_login"), "[visitante] botón «Ingresar o registrarme» en la barra")
check(not any(b.key == "logout_button" for b in at.button), "[visitante] sin «Cerrar sesión»")

# ---------- Cliente: perfil abierto se cierra al cambiar de sección ----------
PID = backend.professional(PRO)["id"]
at = new_app(front, CLIENTE)
at.button(key="client_navigation_btn_1").click().run()
at.button(key=f"client_view_prof_{PID}").click().run()
check(any(b.key == "back_from_profile" for b in at.button), "[cliente] abre el perfil de un profesional")
at.button(key="client_navigation_btn_0").click().run()
at.button(key="client_navigation_btn_1").click().run()
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
check(not at.exception and keys(at, "visitor_navigation_btn_") and not keys(at, "client_navigation_btn_"),
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


def bar_keys(at, nav):
    return [b.key for b in at.button if (b.key or "").startswith(f"{nav}_btn_")]


def side_sections(at, nav):
    return [b for b in at.sidebar.button if (b.key or "").startswith(f"side_{nav}_btn_")]


def sidebar_text(at):
    return " ".join(m.value for m in at.sidebar.markdown) + " ".join(c.value for c in at.sidebar.caption) \
        + " ".join(b.label for b in at.sidebar.button)


def current_marked(at, nav):
    """La sección actual va destacada (primary) en la barra y en el menú lateral, y solo esa."""
    value = at.session_state[nav]
    top = [b for b in at.button if (b.key or "").startswith(f"{nav}_btn_")]
    lat = side_sections(at, nav)
    return (len(top) == len(lat)
            and [b.label for b in top if b.proto.type == "primary"] == [b.label for b in lat if b.proto.type == "primary"]
            and len([b for b in lat if b.proto.type == "primary"]) == 1
            and next(b for b in lat if b.proto.type == "primary").label.replace("\u00a0", " ").startswith(value))


at = new_app(front)
check(not [k for k in side(at) if (k or "").startswith("side_")] and "logout_button" not in side(at),
      "[visitante] sin secciones ni opciones de cuenta en el menú lateral")

# Cliente
NAV = "client_navigation"
backend.notifications_add(backend.by_email(CLIENTE)["id"], "Aviso de prueba", "Para el contador del menú lateral.")
at = new_app(front, CLIENTE)
check(side(at) == ["side_" + k for k in bar_keys(at, NAV)] + ["side_contrasena", "logout_button"],
      "[cliente] menú lateral: las secciones de la barra, Cambiar contraseña y Cerrar sesión al final")
check([b.label for b in side_sections(at, NAV)] == [b.label for b in at.button if b.key in bar_keys(at, NAV)],
      "[cliente] las secciones del menú lateral tienen las mismas etiquetas (con ícono) que la barra")
check("Rol:" not in sidebar_text(at), "[cliente] el menú lateral no muestra «Rol:»")
check("Editar datos" not in sidebar_text(at) and "side_editar" not in side(at), "[cliente] sin «Editar datos»")
check("Mi perfil" not in " ".join(b.label for b in at.sidebar.button if not (b.key or "").startswith("side_" + NAV)),
      "[cliente] «Mi perfil» no se repite en «Mi cuenta» (queda en las secciones)")
check("Requisitos contemplados" not in sidebar_text(at) and "RNF" not in sidebar_text(at), "[cliente] sin los bloques de requisitos")
check(any("Notificaciones" in b.label and "(" in b.label for b in side_sections(at, NAV)),
      "[cliente] el contador de notificaciones sin leer también se ve en el menú lateral")
check(current_marked(at, NAV), "[cliente] la sección actual queda marcada en la barra y en el menú lateral")

at.sidebar.button(key=f"side_{NAV}_btn_2").click().run()
via_side = at.session_state[NAV]
at2 = new_app(front, CLIENTE)
at2.button(key=f"{NAV}_btn_2").click().run()
check(not at.exception and via_side == at2.session_state[NAV] == "📋 Mis solicitudes" and "Mis solicitudes" in md(at),
      "[cliente] el botón del menú lateral cambia de sección igual que el de la barra")
check(current_marked(at, NAV), "[cliente] tras cambiar desde el menú lateral, la nueva sección queda marcada")

at.sidebar.button(key="side_contrasena").click().run()
check(at.session_state[NAV] == "👤 Mi perfil" and "pwd_current" in widget_keys(at)
      and "edit_phone" not in widget_keys(at) and "Cambiar contraseña" in md(at),
      "[cliente] «Cambiar contraseña» abre solo el cambio de contraseña")
at.sidebar.button(key=f"side_{NAV}_btn_0").click().run()
at.sidebar.button(key=f"side_{NAV}_btn_6").click().run()
check(at.session_state[NAV] == "👤 Mi perfil" and {"edit_phone", "pwd_current"} <= widget_keys(at)
      and "Mi perfil personal" in md(at), "[cliente] «Mi perfil» (sección) muestra los datos y la contraseña")

# Profesional
NAV = "professional_navigation"
at = new_app(front, PRO)
check(side(at) == ["side_" + k for k in bar_keys(at, NAV)] + ["side_contrasena", "side_suscripción", "side_verificación", "logout_button"],
      "[profesional] secciones de la barra y, en «Mi cuenta», Cambiar contraseña, Suscripción y Verificación")
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

# Administrador: no tiene «Mi perfil» en su barra, así que lo conserva en «Mi cuenta»
NAV = "admin_navigation"
at = new_app(front, ADMIN)
check(side(at) == ["side_" + k for k in bar_keys(at, NAV)] + ["side_perfil", "side_contrasena", "logout_button"],
      "[admin] secciones de la barra y, en «Mi cuenta», Mi perfil (no está en su barra) y Cambiar contraseña")
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
