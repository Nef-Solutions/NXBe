"""Búsqueda por palabra clave (historia 4.16): mayúsculas y tildes, varias palabras,
filtros, «Limpiar búsqueda» y visitante sin nombres."""

from comun import backend, card_ids as ids, check, md, new_app, preparar, terminar

front = preparar()

CLIENTE = "cliente1@demo.overol.cl"
CARLOS = backend.professional("profesional1@demo.overol.cl")["id"]  # Gasfitería
DANIEL = backend.professional("profesional2@demo.overol.cl")["id"]  # Electricidad
MARCELO = backend.professional("profesional3@demo.overol.cl")["id"]  # Carpintería y pintura
NAMES = ["Carlos Muñoz", "Daniel Soto", "Marcelo Rojas"]
U = {"cliente": CLIENTE}


def open_search(email):
    at = new_app(front, email)
    nav = "client_navigation" if email else "visitor_navigation"
    at.button(key=f"{nav}_btn_1").click().run()
    return at


def search(user_id, text):
    at = open_search(user_id)
    at.text_input(key="search_text").input(text).run()
    return at, ids(at)


# ---------- Cliente: nombre, mayúsculas y tildes ----------
for text in ("carlos", "CARLOS", "Muñoz", "munoz", "MUÑOZ"):
    at, found = search(U["cliente"], text)
    check(not at.exception and found == {CARLOS}, f"[cliente] «{text}» encuentra solo a Carlos")

# ---------- Oficio, especialidad y palabras clave (con y sin tilde) ----------
for text, expected in (
    ("gasfitería", {CARLOS}), ("gasfiteria", {CARLOS}),
    ("cañería", {CARLOS}), ("caneria", {CARLOS}), ("cañerías", {CARLOS}),
    ("enchufe", {DANIEL}), ("eléctrico", {DANIEL}), ("electrico", {DANIEL}),
    ("pintar", {MARCELO}), ("Calefont", {CARLOS}),
):
    at, found = search(U["cliente"], text)
    check(not at.exception and expected <= found and not (found - expected),
          f"[cliente] «{text}» → {sorted(expected)}")

# ---------- Varias palabras: deben coincidir todas; las palabras vacías no cuentan ----------
at, found = search(U["cliente"], "fuga agua")
check(found == {CARLOS}, "[cliente] «fuga agua» (dos palabras del mismo oficio) encuentra a Carlos")
at, found = search(U["cliente"], "fuga enchufe")
check(found == set(), "[cliente] «fuga enchufe» (oficios distintos) no encuentra a nadie")
at, found = search(U["cliente"], "arreglo de una fuga")
check(found == set(), "[cliente] «arreglo» no está en ningún perfil: con todas las palabras, sin resultados")
at, found = search(U["cliente"], "una fuga en el baño")
check(found == {CARLOS}, "[cliente] «una fuga en el baño» ignora «una», «en», «el»")
at, found = search(U["cliente"], "   ")
check(len(found) >= 3, "[cliente] texto en blanco muestra a todos")

# ---------- Nunca busca en datos personales ----------
for text in ("12345678", "12345678-5"):
    at, found = search(U["cliente"], text)
    check(found == set(), f"[cliente] el RUT «{text}» no encuentra a nadie")

# ---------- Sin resultados: mensaje y «Limpiar búsqueda» ----------
at, found = search(U["cliente"], "xyzabc")
check(found == set() and "xyzabc" in md(at) and any(b.key == "search_clear" for b in at.button),
      "[cliente] sin resultados: mensaje con el texto buscado y «Limpiar búsqueda»")
at.button(key="search_clear").click().run()
check(not at.exception and at.text_input(key="search_text").value == "" and len(ids(at)) >= 3,
      "[cliente] «Limpiar búsqueda» borra el texto y vuelve a mostrar a todos")

# ---------- Filtros combinados con la palabra clave ----------
at = open_search(U["cliente"])
at.selectbox(key="search_trade").select("Electricidad").run()
check(ids(at) == {DANIEL}, "[cliente] filtro de oficio «Electricidad»")
at.text_input(key="search_text").input("fuga").run()
check(ids(at) == set() and any(b.key == "search_clear" for b in at.button),
      "[cliente] «fuga» + Electricidad: sin resultados y ofrece limpiar")
at.button(key="search_clear").click().run()
check(at.selectbox(key="search_trade").value == "Todas" and len(ids(at)) >= 3,
      "[cliente] limpiar también reinicia los filtros")

# ---------- Visitante: tarjetas anónimas y sin búsqueda por nombre ----------
at = open_search(None)
page = md(at)
check(not at.exception and len(ids(at)) >= 3 and not any(n in page for n in NAMES),
      "[visitante] ve las tarjetas sin nombres")
for text in ("carlos", "Muñoz", "daniel soto"):
    at, found = search(None, text)
    check(found == set(), f"[visitante] «{text}» no encuentra por nombre")
at, found = search(None, "cañería")
check(found == {CARLOS} and "Carlos" not in md(at), "[visitante] busca por oficio y la tarjeta sigue anónima")
at.button(key=f"client_view_prof_{CARLOS}").click().run()
page = md(at)
check(not at.exception and not any(n in page for n in NAMES) and "profesional1@demo.overol.cl" not in page
      and not any(b.key == f"send_request_{CARLOS}" for b in at.button)
      and any(b.key == f"go_login_profile_{CARLOS}" for b in at.button),
      "[visitante] el perfil público no muestra nombre ni contacto y pide ingresar para solicitar")

terminar()
