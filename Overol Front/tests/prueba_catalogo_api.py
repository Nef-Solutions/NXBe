"""Fase 3: catálogo y perfiles públicos desde la API (backend simulado en comun.py).
En modo api: tarjetas, filtros enviados al backend (oficio, especialidad, comuna), palabra clave
en el front, paginación, visitante sin nombres, «Disponible pronto» y backend caído.
En modo local: el catálogo sigue saliendo de SQLite y nada sale a la red."""

import os
from urllib.parse import parse_qs, urlsplit

from comun import (
    BACKEND_CAIDO, TAM_PAGINA, check, md, new_app, next_valid_slot, peticiones, preparar,
    reset_pending, terminar, texts, usuarios,
)

front = preparar()
U = usuarios(front)

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import database as db  # noqa: E402
from core.constants import use_api  # noqa: E402

CLIENT, PRO_USER = U["cliente"], U["carlos"]
PID = db.get_professional_by_user(PRO_USER)["id"]
CATALOG = db.get_all_professionals()
NAMES = [p["name"] for p in CATALOG]

# Una opinión con comentario conocida para Carlos
reset_pending(db, CLIENT, PID)
ok, rid = db.create_request(CLIENT, PID, db.get_trades(PID)[0]["trade"], "", "Santiago",
                            *next_valid_slot(db, PID), "Prueba del catálogo")
db.change_request_status(rid, "Aceptada", ["Pendiente"], professional_id=PID)
db.confirm_request_completion(rid, "client", client_id=CLIENT)
db.confirm_request_completion(rid, "professional", professional_id=PID)
conn = db.get_connection()
conn.execute(
    "INSERT INTO ratings (request_id, client_id, professional_id, quality, punctuality, treatment, comment, created_at) "
    "VALUES (?, ?, ?, 5, 5, 4, 'Muy prolijo y puntual con la llave', ?)",
    (rid, CLIENT, PID, db.now_str()),
)
conn.commit()
conn.close()


def card_ids(at):
    return {int(b.key.rsplit("_", 1)[1]) for b in at.button if (b.key or "").startswith("client_view_prof_")}


def search_page(user_id=None):
    at = new_app(front, user_id)
    at.button(key="client_navigation_btn_1" if user_id else "visitor_navigation_btn_1").click().run()
    return at


def last_list_query():
    for method, path in reversed(peticiones):
        if path.startswith("/catalog/professionals/?"):
            return {k: v[0] for k, v in parse_qs(urlsplit(path).query).items()}
    return None


def any_name(at):
    return [n for n in NAMES if n in md(at) or n in texts(at)]


if use_api():
    # ---------- Visitante: tarjetas desde la API, sin nombres ----------
    peticiones.clear()
    at = search_page()
    check(not at.exception and any(p.startswith("/catalog/professionals/?") for _, p in peticiones),
          "[api] el catálogo se pide a GET /api/catalog/professionals/")
    check(card_ids(at) == {p["id"] for p in CATALOG}, f"[api] muestra los {len(CATALOG)} profesionales del backend")
    check(not any_name(at) and f"Profesional #{PID}" in md(at), "[api] visitante: tarjetas sin nombres")
    query = last_list_query() or {}
    check("keyword" not in query and "latitude" not in query, "[api] no envía keyword ni coordenadas al backend")

    at.text_input(key="search_text").input(NAMES[0].split()[0]).run()
    check(card_ids(at) == set(), "[api] visitante: buscar un nombre no encuentra a nadie")
    at.text_input(key="search_text").input("fúga").run()
    check(PID in card_ids(at), "[api] palabra clave del front sobre los resultados (fúga → gasfitería)")

    # ---------- Perfil público del visitante ----------
    at.text_input(key="search_text").input("").run()
    peticiones.clear()
    at.button(key=f"client_view_prof_{PID}").click().run()
    check(not at.exception and ("GET", f"/catalog/professionals/{PID}/") in peticiones,
          "[api] el perfil se pide a GET /api/catalog/professionals/{id}/")
    check(f"Profesional #{PID}" in md(at) and not any_name(at), "[api] visitante: perfil sin nombre")
    check("Muy prolijo y puntual" in md(at) and any(b.key == f"go_login_profile_{PID}" for b in at.button),
          "[api] visitante: ve las opiniones y el botón para ingresar")

    # ---------- Cliente: nombres, filtros enviados al backend ----------
    at = search_page(CLIENT)
    check(all(n in md(at) for n in NAMES), "[api] cliente: las tarjetas muestran el nombre")

    trade = db.get_trades(PID)[0]["trade"]
    at.selectbox(key="search_trade").select(trade).run()
    query = last_list_query() or {}
    check(query.get("category_id") and PID in card_ids(at), f"[api] oficio «{trade}» → category_id={query.get('category_id')}")
    spec = next(k for k in at.selectbox(key=f"search_specialty_{trade}").options if k != "Todas")
    at.selectbox(key=f"search_specialty_{trade}").select(spec).run()
    check((last_list_query() or {}).get("specialty_id"), f"[api] especialidad «{spec}» → specialty_id")
    at.selectbox(key=f"search_specialty_{trade}").select("Todas")
    at.selectbox(key="search_trade").select("Todas")
    at.selectbox(key="search_commune").select("Ñuñoa").run()
    check((last_list_query() or {}).get("commune") == "Ñuñoa", "[api] comuna → commune=Ñuñoa")
    expected = {p["id"] for p in CATALOG if "Ñuñoa" in p["coverage"].split(",")}
    check(card_ids(at) == expected, "[api] el filtro por comuna lo aplica el backend")

    # ---------- Paginación ----------
    TAM_PAGINA[0] = 1
    peticiones.clear()
    at = search_page(CLIENT)
    pages = [p for _, p in peticiones if p.startswith("/catalog/professionals/?")]
    check(card_ids(at) == {p["id"] for p in CATALOG} and len(pages) >= len(CATALOG),
          f"[api] recorre todas las páginas ({len(pages)} peticiones)")
    TAM_PAGINA[0] = 50

    # ---------- Oficio que el backend no tiene ----------
    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    at.session_state["authenticated"] = True
    at.session_state["user_id"] = CLIENT
    at.session_state["client_navigation"] = "🔎 Buscar profesionales"
    at.session_state["search_trade"] = "Cerrajería"
    at.run()
    check(not at.exception and any("«Cerrajería» todavía no está disponible" in i.value for i in at.info),
          "[api] oficio que no está en el catálogo: aviso y muestra todos")

    # ---------- Cliente: perfil con «Disponible pronto» ----------
    at = search_page(CLIENT)
    peticiones.clear()
    at.button(key=f"client_view_prof_{PID}").click().run()
    name = db.get_professional_by_id(PID)["name"]
    check(not at.exception and name in md(at), "[api] cliente: el perfil muestra el nombre")
    check(any("Disponible pronto" in i.value for i in at.info)
          and not any((b.key or "").startswith("send_request_") for b in at.button)
          and not any(m != "GET" for m, _ in peticiones),
          "[api] «Solicitar visita» muestra «Disponible pronto» y no envía nada")

    # ---------- Enlace directo ?profesional=ID ----------
    at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
    at.query_params["profesional"] = str(PID)
    at.run()
    check(not at.exception and f"Profesional #{PID}" in md(at) and "Muy prolijo" in md(at),
          "[api] ?profesional=ID abre el perfil desde la API")

    # ---------- Portada: destacados desde la API ----------
    at = new_app(front)
    feat = {int(b.key.rsplit("_", 1)[1]) for b in at.button if (b.key or "").startswith("home_feat_")}
    check(not at.exception and feat and feat <= {p["id"] for p in CATALOG} and not any_name(at),
          "[api] portada: destacados del backend, sin nombres para el visitante")

    # ---------- Backend caído ----------
    BACKEND_CAIDO[0] = True
    at = new_app(front)
    check(not at.exception and not any((b.key or "").startswith("home_feat_") for b in at.button),
          "[api] backend caído: la portada abre sin destacados")
    at = search_page(CLIENT)
    check(not at.exception and any("No se pudo cargar el catálogo" in str(e.value) for e in at.error),
          "[api] backend caído: «Buscar profesionales» muestra un error claro")
    BACKEND_CAIDO[0] = False

else:
    # ---------- Modo local: igual que antes y sin red ----------
    peticiones.clear()
    at = search_page()
    check(not at.exception and card_ids(at) == {p["id"] for p in CATALOG} and not any_name(at),
          "[local] visitante: tarjetas desde SQLite, sin nombres")
    at = search_page(CLIENT)
    at.button(key=f"client_view_prof_{PID}").click().run()
    check(not at.exception and any(b.key == f"send_request_{PID}" for b in at.button)
          and not any("Disponible pronto" in i.value for i in at.info),
          "[local] cliente: el perfil mantiene el formulario «Solicitar visita»")
    check("Muy prolijo y puntual" in md(at), "[local] cliente: el perfil muestra las opiniones")
    check(peticiones == [], f"[local] ninguna petición a la red ({len(peticiones)})")

terminar()
