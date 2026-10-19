"""Constantes y configuración general de Overol."""

import os
from pathlib import Path

# Carpeta raíz del proyecto (proyecto_overol/), un nivel sobre core/
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "overol.db"
UPLOAD_DIR = APP_DIR / "documentos_verificacion"

# Origen de los datos de cuentas: "local" (SQLite) o "api" (backend Django).
# Por defecto "local", para que la demo no dependa del backend.
OVEROL_BACKEND = "api" if os.environ.get("OVEROL_BACKEND", "local").strip().lower() == "api" else "local"
API_BASE_URL = os.environ.get("OVEROL_API_URL", "http://127.0.0.1:8000/api/").rstrip("/") + "/"
API_TIMEOUT = 10

# Versión de la política de privacidad y términos de uso que acepta el usuario al registrarse
PRIVACY_POLICY_VERSION = "2026-10"


def use_api():
    return OVEROL_BACKEND == "api"

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
    "Vencida",
    "Cancelada",
    "Finalizada",
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

# Catálogo de especialidades por oficio (Historias 002, 008 y 018)
ESPECIALIDADES_POR_OFICIO = {
    "Gasfitería": [
        "Fugas de agua",
        "Destapes",
        "Grifería y artefactos sanitarios",
        "Calefont y termo",
    ],
    "Electricidad": [
        "Enchufes e interruptores",
        "Tableros eléctricos",
        "Iluminación",
        "Instalación de ventiladores",
    ],
    "Carpintería": [
        "Muebles a medida",
        "Reparación de puertas",
        "Closets",
        "Instalación de pisos",
    ],
    "Pintura": [
        "Pintura interior",
        "Pintura exterior",
        "Empastes y reparaciones",
        "Impermeabilización",
    ],
    "Maestro multipropósito": [
        "Reparaciones generales",
        "Instalaciones menores",
        "Mantención del hogar",
    ],
}

# Historia 021: motivos para rechazar una solicitud
MOTIVOS_RECHAZO = [
    "No disponible",
    "Fuera de mi zona de trabajo",
    "El servicio no corresponde a mi especialidad",
    "Otro",
]

# Historia 019: horario
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
HORAS = [f"{h:02d}:00" for h in range(6, 24)]

PREFERENCIAS_CONTACTO = ["WhatsApp", "Llamada telefónica", "Correo electrónico"]

# Oficios con ícono y descripción (portada y botones de categorías)
OFICIOS_INFO = list(CATEGORIAS) + [
    ("🧰", "Maestro multipropósito", "Reparaciones generales y trabajos menores del hogar"),
]

# Integrantes del equipo (Documento 01 – Product Vision)
EQUIPO = [
    (
        "Ximena Campos",
        "Product Owner",
        "Define la visión del producto, prioriza el backlog y vela porque Overol "
        "responda a las necesidades de clientes y profesionales.",
    ),
    (
        "Nefi Apablaza",
        "Desarrollador Back-end",
        "Construye la lógica del servicio, la base de datos y las reglas que "
        "mantienen seguros y consistentes los datos de la plataforma.",
    ),
    (
        "Benjamín Osses",
        "Desarrollador Front-end",
        "Diseña y desarrolla la interfaz de Overol, cuidando que cada tipo de "
        "usuario tenga una experiencia clara y simple de usar.",
    ),
]

# Una solicitud pendiente vence si el profesional no responde en este plazo
HORAS_VENCIMIENTO = 72

# Franjas horarias que el cliente puede pedir
FRANJAS_HORARIAS = [
    "09:00 - 11:00",
    "11:00 - 13:00",
    "15:00 - 17:00",
    "17:00 - 19:00",
]

# Máximo de caracteres en motivos de cancelación y mensajes a soporte
MAX_TEXTO = 500

# Seguridad del inicio de sesión
MAX_INTENTOS_LOGIN = 3
MINUTOS_BLOQUEO = 5
DIAS_SESION = 7
