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
    at.button(key="side_client_navigation_btn_1" if email else "side_visitor_navigation_btn_1").click().run()
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
check(set(at.selectbox(key="search_trade").options) == {"Todas", "Gasfitería", "Electricidad", "Carpintero",
                                                          "Pintor", "Cerrajería", "Soldador", "Jardinero"},
      "los oficios del filtro salen de GET /catalog/categories/, sin los retirados (Guardia, Niñera)")

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

# ---------- Portada: los 65 oficios del equipo, por categorías ----------
import ast  # noqa: E402
from pathlib import Path  # noqa: E402

from core.oficios import GRUPOS_OFICIOS, OFICIOS_EXCLUIDOS, OFICIOS_PORTADA  # noqa: E402

at = new_app(front)
trade_buttons = [b for b in at.button if (b.key or "").startswith("cat_visitor_navigation_")]
check(not at.exception and len(OFICIOS_PORTADA) == 54 and len(trade_buttons) == 54,
      "portada: muestra los 54 oficios vigentes de la lista del equipo")
check(not any(b.key.split("_", 3)[-1] in OFICIOS_EXCLUIDOS for b in trade_buttons)
      and "Cuidado de personas y mascotas" not in md(at),
      "portada: sin los oficios retirados ni la categoría que quedó vacía")
check(all(f"{title} <span>({len(oficios)})</span>" in md(at) for _, title, oficios in GRUPOS_OFICIOS),
      f"portada: los oficios van agrupados en {len(GRUPOS_OFICIOS)} categorías con su cantidad")
labels = {b.label for b in trade_buttons}
check({"🕸️ Instalador de malla anticaída", "💧 Impermeabilizador", "🧻 Papel mural",
       "📏 Cornisa y zócalo", "⛏️ Excavador", "🌬️ Aire acondicionado",
       "🏠 Techumbre", "🍳 Campanero de cocina"} <= labels
      and not labels & {"🧸 Niñera", "🔔 Citófono y videoportero", "🎮 Técnico de consolas", "🧹 Aseo"},
      "portada: nombres con la ortografía corregida («Campanero de cocina» se deja como en la lista)")
migration = Path(__file__).resolve().parents[2] / "backend" / "apps" / "catalog" / "migrations" / "0005_seed_official_trade_catalog.py"
if migration.exists():
    tree = ast.parse(migration.read_text(encoding="utf-8"))
    official = {name for name, _ in next(ast.literal_eval(n.value) for n in tree.body
                                         if isinstance(n, ast.Assign) and n.targets[0].id == "OFFICIAL_TRADES")}
    check({backend_name for _, backend_name, _ in OFICIOS_PORTADA} <= official,
          "portada: todos los oficios existen en el catálogo oficial del backend (migración catalog 0005)")
    check(OFICIOS_EXCLUIDOS <= official and not OFICIOS_EXCLUIDOS & {b for _, b, _ in OFICIOS_PORTADA},
          "cruce con el backend: los excluidos existen allá y se ignoran en la portada")
else:
    print("OK   (sin carpeta backend/: se omite el cruce con la migración catalog 0005)")

at.button(key="cat_visitor_navigation_Gasfitería").click().run()
check(not at.exception and at.session_state["visitor_navigation"] == "🔎 Profesionales"
      and at.session_state["search_trade"] == "Gasfitería" and last_list_query().get("category_id") == "1",
      "visitante: «Gasfíter» lleva al catálogo filtrado por Gasfitería")
at = new_app(front, CLIENTE, client_navigation="🏠 Inicio")
at.button(key="cat_client_navigation_Jardinero").click().run()
check(not at.exception and at.session_state["client_navigation"] == "🔎 Buscar profesionales"
      and at.session_state["search_trade"] == "Jardinero", "cliente: «Jardinero» lleva al catálogo filtrado por ese oficio")
at = new_app(front)
at.button(key="cat_visitor_navigation_Pasto sintético").click().run()
check(not at.exception and at.session_state["visitor_navigation"] == "🔎 Profesionales"
      and "todavía no está disponible" in texts(at),
      "un oficio que el catálogo aún no tiene: va al catálogo y avisa (como antes)")

# ---------- Oficios retirados aunque el backend los devuelva ----------
solo_retirado = backend.add_professional("guardia@demo.overol.cl", "Gustavo", "Guardia", "16789012-3",
                                         trades=[(8, 3, ["Vigilancia de eventos"])], coverage=["Santiago"], fee=9000)
mixto = backend.add_professional("mixto@demo.overol.cl", "Mario", "Mixto", "17890123-4",
                                 trades=[(2, 4, ["Iluminación"]), (8, 2, ["Vigilancia de eventos"])],
                                 coverage=["Santiago"], fee=11000)
pid_retirado, pid_mixto = 100 + solo_retirado, 100 + mixto
at = search_page(CLIENTE)
check(not at.exception and pid_mixto in card_ids(at) and pid_retirado not in card_ids(at),
      "catálogo: oculta al profesional que solo tiene oficios retirados; el que tiene otro oficio sigue")
check("Guardia" not in md(at) and "Vigilancia de eventos" not in md(at), "catálogo: las tarjetas no muestran el oficio retirado")
at.text_input(key="search_text").input("guardia vigilancia").run()
check(not at.exception and pid_retirado not in card_ids(at) and pid_mixto not in card_ids(at),
      "búsqueda por palabra clave: no encuentra a nadie por el oficio retirado")
at = AppTest.from_file(os.path.join(front, "app.py"), default_timeout=60)
at.query_params["profesional"] = str(pid_retirado)
at.run()
check(not at.exception and not any(b.key == "back_from_profile" for b in at.button),
      "enlace directo a un profesional con solo oficios retirados: no abre el perfil")
at = new_app(front, CLIENTE, client_navigation="🔎 Buscar profesionales", _client_prev_menu="🔎 Buscar profesionales",
             selected_professional=pid_mixto)
check(not at.exception and at.selectbox(key=f"request_trade_{pid_mixto}").options == ["Electricidad"],
      "solicitar visita: el formulario solo ofrece los oficios vigentes del profesional")
vid = backend.add_visit(CLIENTE, "guardia@demo.overol.cl", status="ACCEPTED")
at = new_app(front, CLIENTE, client_navigation="📋 Mis solicitudes")
check(not at.exception and "Guardia (oficio retirado)" in md(at),
      "una solicitud existente con un oficio retirado se sigue viendo, marcada «(oficio retirado)»")

# ---------- Backend caído ----------
backend.caido = True
at = new_app(front)
check(not at.exception and not any((b.key or "").startswith("home_feat_") for b in at.button),
      "backend caído: la portada abre sin cifras ni destacados")
at.button(key="side_visitor_navigation_btn_1").click().run()
check(not at.exception and any("No se pudo cargar el catálogo" in str(e.value) for e in at.error),
      "backend caído: la búsqueda muestra un error claro")
backend.caido = False

terminar()
