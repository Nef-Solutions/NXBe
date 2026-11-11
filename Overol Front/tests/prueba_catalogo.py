"""Catálogo y perfiles públicos desde la API: tarjetas, filtros enviados al backend (oficio,
especialidad, comuna), palabra clave en el front, paginación, visitante sin nombres,
«Disponible pronto», enlace directo, portada y backend caído."""

import os
from urllib.parse import parse_qs, urlsplit

from comun import backend, calls, card_ids, check, md, new_app, preparar, terminar, texts

front = preparar()

from streamlit.testing.v1 import AppTest  # noqa: E402

CLIENTE = "cliente1@demo.overol.cl"
PID = backend.professional("profesional1@demo.overol.cl")["id"]
CATALOG = {u["professional"]["id"]: u for u in backend._approved()}
NAMES = [f"{u['first_name']} {u['last_name']}" for u in CATALOG.values()]
PENDING = backend.professional("pendiente@demo.overol.cl")["id"]


def search_page(email=None):
    at = new_app(front, email)
    at.button(key="client_navigation_btn_1" if email else "visitor_navigation_btn_1").click().run()
    return at


def last_list_query():
    found = calls("GET", "/catalog/professionals/?")
    return {k: v[0] for k, v in parse_qs(urlsplit(found[-1][1]).query).items()} if found else {}


def any_name(at):
    return [n for n in NAMES if n in md(at) or n in texts(at)]


# ---------- Visitante: tarjetas desde la API, sin nombres ----------
backend.calls.clear()
at = search_page()
check(not at.exception and calls("GET", "/catalog/professionals/?"), "el catálogo se pide a GET /api/catalog/professionals/")
check(card_ids(at) == set(CATALOG) and PENDING not in card_ids(at),
      f"muestra los {len(CATALOG)} profesionales aprobados (no el pendiente)")
check(not any_name(at) and f"Profesional #{PID}" in md(at), "visitante: tarjetas sin nombres")
query = last_list_query()
check("keyword" not in query and "latitude" not in query, "no envía keyword ni coordenadas al backend")

at.text_input(key="search_text").input("Carlos").run()
check(card_ids(at) == set(), "visitante: buscar un nombre no encuentra a nadie")
at.text_input(key="search_text").input("fúga").run()
check(card_ids(at) == {PID}, "palabra clave del front sobre los resultados (fúga → gasfitería)")

# ---------- Perfil público del visitante ----------
at.text_input(key="search_text").input("").run()
backend.calls.clear()
at.button(key=f"client_view_prof_{PID}").click().run()
check(not at.exception and calls("GET", f"/catalog/professionals/{PID}/"), "el perfil se pide a GET /catalog/professionals/{id}/")
check(f"Profesional #{PID}" in md(at) and not any_name(at), "visitante: perfil sin nombre")
check("Muy prolijo y puntual" in md(at) and any(b.key == f"go_login_profile_{PID}" for b in at.button),
      "visitante: ve las opiniones y el botón para ingresar")

# ---------- Cliente: nombres y filtros enviados al backend ----------
at = search_page(CLIENTE)
check(all(n in md(at) for n in NAMES), "cliente: las tarjetas muestran el nombre")
at.selectbox(key="search_trade").select("Gasfitería").run()
check(last_list_query().get("category_id") == "1" and card_ids(at) == {PID}, "oficio Gasfitería → category_id=1")
at.selectbox(key="search_specialty_Gasfitería").select("Calefont y termo").run()
check(last_list_query().get("specialty_id") and card_ids(at) == {PID}, "especialidad → specialty_id")
at.selectbox(key="search_specialty_Gasfitería").select("Todas")
at.selectbox(key="search_trade").select("Todas")
at.selectbox(key="search_commune").select("Ñuñoa").run()
expected = {pid for pid, u in CATALOG.items() if "Ñuñoa" in u["professional"]["coverage_communes"]}
check(last_list_query().get("commune") == "Ñuñoa" and card_ids(at) == expected, "comuna → commune=Ñuñoa, filtrada por el backend")
check(set(at.selectbox(key="search_trade").options) == {"Todas", "Gasfitería", "Electricidad", "Carpintería",
                                                          "Pintura", "Cerrajería"},
      "los oficios del filtro salen de GET /catalog/categories/")

# ---------- Paginación ----------
backend.page_size_max = 1
backend.calls.clear()
at = search_page(CLIENTE)
check(card_ids(at) == set(CATALOG) and len(calls("GET", "/catalog/professionals/?")) >= len(CATALOG),
      "recorre todas las páginas")
backend.page_size_max = 50

# ---------- Oficio que el backend no tiene (p. ej. desde una categoría de la portada) ----------
at = new_app(front, CLIENTE, client_navigation="🔎 Buscar profesionales", search_trade="Maestro multipropósito")
check(not at.exception and any("«Maestro multipropósito» todavía no está disponible" in i.value for i in at.info),
      "oficio que no está en el catálogo: aviso y muestra todos")

# ---------- Cliente: perfil con el formulario de solicitud ----------
at = search_page(CLIENTE)
backend.calls.clear()
at.button(key=f"client_view_prof_{PID}").click().run()
check(not at.exception and "Carlos Muñoz" in md(at), "cliente: el perfil muestra el nombre")
check(any(b.key == f"send_request_{PID}" for b in at.button) and not [c for c in backend.calls if c[0] != "GET"],
      "cliente: el perfil trae «Solicitar visita» (sin enviar nada todavía)")

# ---------- Enlace directo ?profesional=ID ----------
at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
at.query_params["profesional"] = str(PID)
at.run()
check(not at.exception and f"Profesional #{PID}" in md(at) and "Muy prolijo" in md(at), "?profesional=ID abre el perfil")
at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
at.query_params["profesional"] = str(PENDING)
at.run()
check(not at.exception and not any(b.key == "back_from_profile" for b in at.button),
      "?profesional= de un profesional no aprobado (404): no abre nada")

# ---------- Portada: cifras y destacados desde la API ----------
at = new_app(front)
feat = {int(b.key.rsplit("_", 1)[1]) for b in at.button if (b.key or "").startswith("home_feat_")}
check(not at.exception and feat and feat <= set(CATALOG) and not any_name(at), "portada: destacados del backend, sin nombres")
check(f'metric-number">{len(CATALOG)}<' in md(at), f"portada: «{len(CATALOG)} profesionales verificados» sale del catálogo")

# ---------- Backend caído ----------
backend.caido = True
at = new_app(front)
check(not at.exception and not any((b.key or "").startswith("home_feat_") for b in at.button),
      "backend caído: la portada abre sin cifras ni destacados")
at.button(key="visitor_navigation_btn_1").click().run()
check(not at.exception and any("No se pudo cargar el catálogo" in str(e.value) for e in at.error),
      "backend caído: la búsqueda muestra un error claro")
backend.caido = False

terminar()
