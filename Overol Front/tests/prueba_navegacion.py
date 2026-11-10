"""Navegación de los 4 roles: opciones y orden de la barra, todas las secciones abren y
cada rol solo ve lo suyo."""

from comun import check, keys, md, new_app, plain, preparar, terminar, usuarios

front = preparar()
U = usuarios(front)

ROLES = {
    "visitante": (None, "visitor_navigation",
                  ["🏠 Inicio", "🔎 Profesionales", "ℹ️ Quiénes somos"]),
    "cliente": (U["cliente"], "client_navigation",
                ["🏠 Inicio", "🔎 Buscar profesionales", "📋 Mis solicitudes", "🛠️ Mis reclamos",
                 "🔔 Notificaciones", "👤 Mi perfil", "ℹ️ Quiénes somos"]),
    "profesional": (U["carlos"], "professional_navigation",
                    ["📋 Solicitudes", "🔔 Notificaciones", "👤 Mi perfil", "📍 Cobertura",
                     "🎓 Desarrollo profesional", "ℹ️ Quiénes somos"]),
    "admin": (U["admin"], "admin_navigation",
              ["📊 Indicadores", "🪪 Verificación", "👥 Usuarios", "⭐ Moderación", "🛠️ Reclamos",
               "🎓 Contenidos", "📜 Trazabilidad", "💬 Soporte", "ℹ️ Quiénes somos"]),
}
PRIVATE = ("Mis solicitudes", "Verificación", "Usuarios", "Trazabilidad", "Mis reclamos")

for role, (uid, nav, options) in ROLES.items():
    at = new_app(front, uid)
    labels = [plain(at.button(key=f"{nav}_btn_{i}").label) for i in range(len(options))]
    check(not at.exception and labels == options and f"{nav}_btn_{len(options)}" not in keys(at, nav),
          f"[{role}] {len(options)} opciones en el orden esperado")

    others = [n for r, (_, n, _) in ROLES.items() if r != role]
    check(not any(keys(at, n + "_btn_") for n in others), f"[{role}] no aparece la barra de otro rol")

    ok = True
    for i, option in enumerate(options):
        at.button(key=f"{nav}_btn_{i}").click().run()
        ok = ok and not at.exception and at.session_state[nav] == option
    check(ok, f"[{role}] todas las secciones abren sin excepción")
    check(not any("Asistente" in (b.label or "") for b in at.button), f"[{role}] sin «Asistente»")

# ---------- Visitante: solo secciones públicas y botón para ingresar ----------
at = new_app(front)
check("go_login_top" in keys(at, "go_login"), "[visitante] botón «Ingresar o registrarme» en la barra")
check(not any(any(p in (b.label or "") for p in PRIVATE) for b in at.button),
      "[visitante] no ve secciones privadas")
check(not any(b.key == "logout_button" for b in at.button), "[visitante] sin «Cerrar sesión»")

# ---------- Cliente: perfil abierto se cierra al cambiar de sección ----------
from core import database as db  # noqa: E402

PID = db.get_professional_by_user(U["carlos"])["id"]
at = new_app(front, U["cliente"])
at.button(key="client_navigation_btn_1").click().run()
at.button(key=f"client_view_prof_{PID}").click().run()
check(any(b.key == "back_from_profile" for b in at.button), "[cliente] abre el perfil de un profesional")
at.button(key="client_navigation_btn_0").click().run()
at.button(key="client_navigation_btn_1").click().run()
check(not any(b.key == "back_from_profile" for b in at.button), "[cliente] al cambiar de sección el perfil se cierra")
at.button(key=f"client_view_prof_{PID}").click().run()
at.button(key="back_from_profile").click().run()
check(not at.exception and any(k.startswith("client_view_prof_") for k in keys(at, "client_view_prof_")),
      "[cliente] «← Volver» regresa a la lista")

# ---------- Cerrar sesión: vuelve a la barra del visitante ----------
at = new_app(front, U["cliente"])
at.button(key="logout_button").click().run()
check(not at.exception and keys(at, "visitor_navigation_btn_") and not keys(at, "client_navigation_btn_"),
      "[cliente] «Cerrar sesión» vuelve a la vista de visitante")

# ---------- Admin: Indicadores es la sección inicial ----------
at = new_app(front, U["admin"])
check("Indicadores de la plataforma" in md(at), "[admin] parte en Indicadores")

terminar()
