"""Etapa F: «Mi perfil» del profesional (datos, vista pública con reputación y oficios con
GET/POST/PATCH/DELETE /professionals/me/trades/) y centro de desarrollo profesional."""

from comun import backend, calls, card_ids, check, md, new_app, preparar, terminar, texts, toasts

front = preparar()

PRO, PENDING, CLIENTE = "profesional1@demo.overol.cl", "pendiente@demo.overol.cl", "cliente1@demo.overol.cl"
pro = backend.professional(PRO)


def profile(email=PRO):
    return new_app(front, email, professional_navigation="👤 Mi perfil")


def last_body(method, prefix):
    found = calls(method, prefix)
    return found[-1][2] if found else None


# ---------- Datos personales y vista pública ----------
at = profile()
check(not at.exception and at.text_input(key="ro_name").value == "Carlos Muñoz", "pestaña de datos personales (/auth/me/)")
metrics = {m.label: m.value for m in at.metric}
check(metrics.get("Valoración promedio") == "4.5 ★" and metrics.get("Opiniones") == "1" and "Muy prolijo" in md(at),
      "vista pública con la valoración y las opiniones del catálogo")
at = profile(PENDING)
check("Tu perfil público aparece cuando estás **verificado**" in texts(at), "pendiente: explica por qué no aparece")

# ---------- Oficios ----------
at = profile()
check(calls("GET", "/professionals/me/trades/") and "Gasfitería" in md(at), "lista sus oficios con el nombre del backend")
tid = pro["trades"][0]["id"]
at.number_input(key=f"trade_years_{tid}").set_value(9)
at.multiselect(key=f"trade_specs_{tid}").select("Destapes")
at.button(key=f"trade_save_{tid}").click().run()
destapes = next(s for s, (n, _) in backend.specialties.items() if n == "Destapes")
check(last_body("PATCH", f"/professionals/me/trades/{tid}/") == {"years_experience": 9, "description": "", "specialties": [destapes]}
      and pro["trades"][0]["years_experience"] == 9 and "Destapes" in pro["trades"][0]["specialties"],
      "edita años y agrega especialidades (PATCH)")

at = profile()
at.selectbox(key="trade_new_category").select("Electricidad").run()
at.multiselect(key="trade_new_specs_2").select("Iluminación")
at.number_input(key="trade_new_years").set_value(3)
at.button(key="trade_add").click().run()
body = last_body("POST", "/professionals/me/trades/") or {}
check(body.get("category_id") == 2 and body.get("years_experience") == 3 and len(body.get("specialties", [])) == 1
      and any(t["category_id"] == 2 for t in pro["trades"]) and "Oficio «Electricidad» agregado" in toasts(at),
      "agrega un oficio con sus especialidades (POST)")
at = profile()
check("Electricidad" not in at.selectbox(key="trade_new_category").options, "no ofrece agregar un oficio que ya tiene")
check(not {"Guardia", "Niñera"} & set(at.selectbox(key="trade_new_category").options),
      "no ofrece agregar oficios retirados de la plataforma")
pro["trades"].append({"id": 9999, "category_id": 8, "years_experience": 1, "specialties": ["Vigilancia de eventos"]})
at = profile()
check(not at.exception and "Guardia" in md(at) and "oficio retirado de Overol" in md(at),
      "un oficio retirado que el profesional ya tenía se ve marcado, sin romper la pantalla")
pro["trades"].pop()

at.selectbox(key="trade_new_category").select("Soldador").run()
check("todavía no tiene especialidades" in texts(at), "oficio sin especialidades: avisa que no recibirá solicitudes")

new_tid = next(t["id"] for t in pro["trades"] if t["category_id"] == 2)
at.button(key=f"trade_off_{new_tid}").click().run()
check(calls("DELETE", f"/professionals/me/trades/{new_tid}/") and not next(t for t in pro["trades"] if t["id"] == new_tid)["is_active"],
      "desactiva un oficio (DELETE)")
at = profile()
check("⛔ desactivado" in md(at) and "no permite reactivar" in texts(at), "lo muestra desactivado (sin reactivar: no hay endpoint)")
cat = new_app(front, CLIENTE, client_navigation="🔎 Buscar profesionales")
cat.selectbox(key="search_trade").select("Electricidad").run()
check(pro["id"] not in card_ids(cat), "el oficio desactivado ya no aparece en el catálogo")

# ---------- Centro de desarrollo profesional ----------
at = new_app(front, PRO, professional_navigation="🎓 Desarrollo profesional")
check(not at.exception and calls("GET", "/professional-center/content/") and "Tributario" in md(at) and "Seguridad" in md(at),
      "lista los contenidos por módulo")
check(any("Trabajo seguro en altura" in m.value for m in at.markdown) and len(at.get("link_button")) == 3,
      "cada contenido tiene su enlace")
at.button(key="content_done_2").click().run()
check(last_body("POST", "/professional-center/progress/") == {"content": 2} and "✅ completado" in md(at),
      "marca un contenido como completado (POST /progress/)")
at = new_app(front, PRO, professional_navigation="🎓 Desarrollo profesional")
at.button(key="content_done_2").click().run()
check(not at.exception and "✅ completado" in md(at), "en otra sesión, el 400 «ya registrado» lo deja como completado")

terminar()
