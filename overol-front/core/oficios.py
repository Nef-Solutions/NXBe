"""Oficios de la portada: la lista oficial del equipo, agrupada por categorías.

Cada oficio es (nombre que se muestra, nombre exacto en el backend, ícono). El nombre que se
muestra corrige la ortografía de la lista del equipo; el del backend es el de
GET /api/catalog/categories/ (migración catalog 0005) y es el que filtra el catálogo.
Solo se incluyen oficios que existen en el backend.

OFICIOS_EXCLUIDOS es la lista central de oficios retirados de la plataforma (nombres del
backend). El front los oculta en todas partes aunque el backend los siga devolviendo: portada,
filtro y búsqueda del catálogo, registro, oficios del profesional y perfiles. Para devolver uno,
basta con quitarlo de esa lista.
"""

# Oficios retirados de la plataforma (15-11-2026). PEDIDO 0.13: que el backend los desactive.
OFICIOS_EXCLUIDOS = frozenset({
    # Toda la categoría «Cuidado de personas y mascotas»
    "Cuidador de adulto mayor",
    "Niñera",
    "Peluquería a domicilio",
    "Paseador de animales",
    "Peluquería canina",
    # Sueltos
    "Aseo",
    "Costurera",
    "Decoración",
    "Citófono y videoportero",
    "Guardia",
    "Técnico de consolas",
})


def oficio_visible(nombre):
    """False si el oficio (nombre del backend) fue retirado de la plataforma."""
    return (nombre or "").strip() not in OFICIOS_EXCLUIDOS


# Lista completa del equipo (incluye los retirados, para poder devolverlos fácilmente)
_TODOS_LOS_GRUPOS = [
    ("🏗️", "Construcción y terminaciones", [
        ("Albañil", "Albañil", "🧱"),
        ("Carpintero", "Carpintero", "🪚"),
        ("Mueblista", "Mueblista", "🪑"),
        ("Yesero", "Yesero", "🪣"),
        ("Ceramista", "Ceramista", "🔲"),
        ("Pintor", "Pintor", "🎨"),
        ("Tabiquero", "Tabiquero", "📐"),
        ("Trazador", "Trazador", "📏"),
        ("Soldador", "Soldador", "🔥"),
        ("Ventanero", "Ventanero", "🪟"),
        ("Espejos y vidrios", "Espejos y vidrios", "🪞"),
        ("Piso flotante", "Piso flotante", "🪵"),
        ("Techumbre", "Techumbre", "🏠"),
        ("Impermeabilizador", "Impermeabilizador", "💧"),
        ("Aislación térmica", "Aislación térmica", "🧊"),
        ("Papel mural", "Papel mural", "🧻"),
        ("Cornisa y zócalo", "Cornisas y zócalos", "📏"),
        ("Ampliaciones", "Ampliaciones", "🏘️"),
        ("Radier", "Radier", "🏗️"),
        ("Excavador", "Excavador", "⛏️"),
        ("Retiro de escombros", "Retiro de escombros", "🚛"),
        ("Ayudante por día", "Ayudante por día", "🙋"),
    ]),
    ("⚡", "Instalaciones y reparaciones", [
        ("Gasfíter", "Gasfitería", "🔧"),
        ("Eléctrico", "Electricidad", "⚡"),
        ("Electrónico", "Electrónico", "🔌"),
        ("Electromecánico", "Electromecánico", "⚙️"),
        ("Refrigeración", "Refrigeración", "❄️"),
        ("Aire acondicionado", "Aire acondicionado", "🌬️"),
        ("Destape de alcantarillado", "Destape de alcantarillado", "🚽"),
        ("Instalador de bombas", "Instalador de bombas", "⛽"),
        # Nombre de la lista del equipo; en el backend es «Instalador de campanas de cocina»
        ("Campanero de cocina", "Instalador de campanas de cocina", "🍳"),
        ("Iluminación", "Iluminación", "💡"),
        ("Paneles solares", "Paneles solares", "☀️"),
        ("Domótica", "Domótica", "📱"),
        ("Técnico de consolas", "Técnico de consolas", "🎮"),
    ]),
    ("🔐", "Seguridad", [
        ("Cerrajero", "Cerrajería", "🔑"),
        ("Cerradura inteligente", "Cerradura inteligente", "🔐"),
        ("Alarmas", "Alarmas", "🚨"),
        ("Instalador de cámaras", "Instalador de cámaras", "📹"),
        ("Citófono y videoportero", "Citófono y videoportero", "🔔"),
        ("Instalador de malla anticaída", "Instalación de malla anticaída", "🕸️"),
        ("Guardia", "Guardia", "💂"),
    ]),
    ("🧹", "Hogar y limpieza", [
        ("Aseo", "Aseo", "🧹"),
        ("Lavado de alfombras", "Lavado de alfombras", "🧽"),
        ("Fumigación y control de plagas", "Fumigación y control de plagas", "🐜"),
        ("Decoración", "Decoración", "🖼️"),
        ("Cortinas roller y persianas", "Cortinas roller y persianas", "🪟"),
        ("Tapicería", "Tapicería", "🛋️"),
        ("Costurera", "Costurera", "🧵"),
    ]),
    ("🌳", "Jardín y exterior", [
        ("Jardinero", "Jardinero", "🌱"),
        ("Regadío automático", "Regadío automático", "💦"),
        ("Pasto sintético", "Pasto sintético", "🌿"),
        ("Quinchos y parrillas", "Quinchos y parrillas", "🍖"),
        ("Pérgolas y terrazas", "Pérgolas y terrazas", "🏡"),
        ("Instalador de piscinas", "Instalador de piscinas", "🏊"),
        ("Limpieza de piscinas", "Limpieza de piscinas", "🫧"),
        ("Tinas y jacuzzi", "Tinas y jacuzzis", "🛁"),
    ]),
    ("🚗", "Vehículos", [
        ("Mecánico", "Mecánico", "🔩"),
        ("Vulcanización", "Vulcanización", "🛞"),
        ("Lavado de autos", "Lavado de autos", "🚗"),
    ]),
    ("🤝", "Cuidado de personas y mascotas", [
        ("Cuidador de adulto mayor", "Cuidador de adulto mayor", "🧓"),
        ("Niñera", "Niñera", "🧸"),
        ("Peluquería a domicilio", "Peluquería a domicilio", "💇"),
        ("Paseador de animales", "Paseador de animales", "🐕"),
        ("Peluquería canina", "Peluquería canina", "🐩"),
    ]),
]

# Portada: sin los oficios retirados; una categoría que queda vacía no se muestra
GRUPOS_OFICIOS = [
    (icono, titulo, visibles)
    for icono, titulo, oficios in _TODOS_LOS_GRUPOS
    if (visibles := [oficio for oficio in oficios if oficio_visible(oficio[1])])
]

# Todos los oficios de la portada: [(nombre que se muestra, nombre en el backend, ícono)]
OFICIOS_PORTADA = [oficio for _, _, oficios in GRUPOS_OFICIOS for oficio in oficios]
