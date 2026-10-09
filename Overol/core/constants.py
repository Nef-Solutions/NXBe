"""Constantes y configuración general de Overol."""

from pathlib import Path

# Carpeta raíz del proyecto (proyecto_overol/), un nivel sobre core/
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "overol.db"
UPLOAD_DIR = APP_DIR / "documentos_verificacion"

COMUNAS = [
    "Santiago",
    "Maipú",
    "Pudahuel",
    "Las Condes",
    "Ñuñoa",
    "Providencia",
    "La Florida",
]

ZONAS_HOGAR = [
    "Cocina",
    "Baño",
    "Dormitorio",
    "Living / comedor",
    "Exterior",
    "Otra zona",
]

CATEGORIAS = [
    ("🔧", "Gasfitería", "Reparaciones, fugas y cañerías"),
    ("⚡", "Electricidad", "Instalaciones y reparaciones eléctricas"),
    ("🪚", "Carpintería", "Muebles, puertas y terminaciones"),
    ("🎨", "Pintura", "Interior, exterior y terminaciones"),
]

ROLES = {
    "cliente": "Cliente",
    "profesional": "Profesional",
    "admin": "Administrador",
}

ESTADOS_SOLICITUD = [
    "Pendiente",
    "Aceptada",
    "Rechazada",
    "Completada",
    "Cancelada",
]

ESTADOS_RECLAMO = [
    "Abierto",
    "En mediación",
    "Resuelto",
    "Cerrado",
]

OFICIOS = [
    "Gasfitería",
    "Electricidad",
    "Carpintería",
    "Pintura",
    "Maestro multipropósito",
]

ESPECIALIDADES = ["Gasfitería", "Electricidad", "Carpintería", "Pintura"]
