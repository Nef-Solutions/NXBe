"""Navegación de los 4 roles con las pantallas pendientes de la API ocultas
(PANTALLAS_PENDIENTES_API), perfil abierto que se cierra al cambiar de sección y cerrar sesión."""

from comun import backend, calls, check, keys, md, nav_labels, new_app, preparar, terminar, texts

front = preparar()

from core.constants import PANTALLAS_PENDIENTES_API  # noqa: E402

CLIENTE, PRO, ADMIN = "cliente1@demo.overol.cl", "profesional1@demo.overol.cl", "admin@demo.overol.cl"
ROLES = {
    "visitante": (None, "visitor_navigation", ["🏠 Inicio", "🔎 Profesionales", "ℹ️ Quiénes somos"]),
    "cliente": (CLIENTE, "client_navigation",
                ["🏠 Inicio", "🔎 Buscar profesionales", "📋 Mis solicitudes", "👤 Mi perfil", "ℹ️ Quiénes somos"]),
    "profesional": (PRO, "professional_navigation",
                    ["📋 Solicitudes", "👤 Mi perfil", "📍 Cobertura", "ℹ️ Quiénes somos"]),
    "admin": (ADMIN, "admin_navigation", ["ℹ️ Quiénes somos"]),
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
    check(not any("Asistente" in (b.label or "") for b in at.button), f"[{role}] sin «Asistente»")

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

# ---------- Admin: mientras el panel se conecta, se usa /admin/ de Django ----------
at = new_app(front, ADMIN)
check("/admin/" in texts(at) and not keys(at, "admin_approve_"), "[admin] aviso del administrador de Django")

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

terminar()
