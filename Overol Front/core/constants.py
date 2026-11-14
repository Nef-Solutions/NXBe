"""Constantes y configuración general de Overol."""

import os
from pathlib import Path

# Carpeta raíz del proyecto (proyecto_overol/), un nivel sobre core/
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "overol.db"
UPLOAD_DIR = APP_DIR / "documentos_verificacion"

# Todo el front trabaja contra el backend Django (el modo local con SQLite se eliminó).
API_BASE_URL = os.environ.get("OVEROL_API_URL", "http://127.0.0.1:8000/api/").rstrip("/") + "/"
API_TIMEOUT = 10

# Versión de la política de privacidad y términos de uso que acepta el usuario al registrarse
PRIVACY_POLICY_VERSION = "2026-10"

# Rol del backend → rol del front
API_ROLES = {"CLIENT": "cliente", "PROFESSIONAL": "profesional", "ADMIN": "admin"}


def use_api():
    # Etapa B: ya no existe el modo local. Las ramas que aún preguntan por él
    # están en pantallas ocultas (PANTALLAS_PENDIENTES_API) y se borran en la etapa H.
    return True


# Pantallas que todavía leen o escriben en SQLite: se ocultan de la barra hasta
# conectarlas a la API. Al terminar cada etapa se quitan de aquí las que ya migraron.
# Valor: etapa que la conecta (C solicitudes · D valoraciones y reclamos ·
# E notificaciones y tickets · F profesional · G admin).
PANTALLAS_PENDIENTES_API = {
    "cliente": {
        "🛠️ Mis reclamos": "D",
        "🔔 Notificaciones": "E",
    },
    "profesional": {
        "🔔 Notificaciones": "E",
        "🛠️ Reclamos": "D",
        "🎓 Desarrollo profesional": "F",
    },
    "admin": {
        "📊 Indicadores": "G",
        "🪪 Verificación": "G",
        "👥 Usuarios": "G",
        "⭐ Moderación": "G",
        "🛠️ Reclamos": "G",
        "🎓 Contenidos": "G",
        "📜 Trazabilidad": "G",
        "💬 Soporte": "G",
    },
}


def pantallas_visibles(role, options):
    """Opciones de la barra sin las pantallas pendientes de conectar a la API."""
    pending = PANTALLAS_PENDIENTES_API.get(role, {})
    return [option for option in options if option not in pending]

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

# Oficios destacados en la portada: los nombres son los del catálogo oficial del backend.
# La lista completa de oficios (66) sale de GET /api/catalog/categories/.
CATEGORIAS = [
    ("🔧", "Gasfitería", "Reparaciones, fugas y cañerías"),
    ("⚡", "Electricidad", "Instalaciones y reparaciones eléctricas"),
    ("🪚", "Carpintero", "Muebles, puertas y terminaciones"),
    ("🎨", "Pintor", "Interior, exterior y terminaciones"),
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

# Palabras clave extra por oficio para la búsqueda (Historia 4.16). Se suman a las
# `keywords` que entrega el backend para cada oficio.
PALABRAS_CLAVE_OFICIO = {
    "Gasfitería": [
        "agua",
        "fuga",
        "filtración",
        "filtracion",
        "cañería",
        "caneria",
        "tubería",
        "tuberia",
        "llave",
        "lavaplatos",
        "baño",
        "wc",
        "inodoro",
        "desagüe",
        "desague",
    ],
    "Electricidad": [
        "luz",
        "enchufe",
        "corriente",
        "cable",
        "eléctrico",
        "electrico",
        "electricidad",
        "interruptor",
        "automático",
        "automatico",
    ],
    "Carpintero": [
        "mueble",
        "madera",
        "puerta",
        "mesa",
        "silla",
        "closet",
        "clóset",
        "estante",
    ],
    "Pintor": [
        "pintar",
        "pintura",
        "pared",
        "techo",
        "color",
        "mancha",
        "pintado",
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
# El backend espera los días con su nombre completo
DIAS_COMPLETOS = dict(zip(DIAS_SEMANA, ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]))
HORAS = [f"{h:02d}:00" for h in range(6, 24)]

PREFERENCIAS_CONTACTO = ["WhatsApp", "Llamada telefónica", "Correo electrónico"]

# Oficios con ícono y descripción (portada y botones de categorías)
OFICIOS_INFO = list(CATEGORIAS) + [
    ("🔑", "Cerrajería", "Cerraduras, llaves y apertura de puertas"),
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

# Tickets de soporte (uno por solicitud y usuario, sobre el hilo de mensajes)
ESTADOS_TICKET = ["Abierto", "Resuelto"]
MAX_ASUNTO = 100

# Seguridad del inicio de sesión
MAX_INTENTOS_LOGIN = 3
MINUTOS_BLOQUEO = 5
DIAS_SESION = 7
