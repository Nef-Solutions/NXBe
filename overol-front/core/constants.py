"""Constantes y configuración general de Overol."""

from pathlib import Path

from core.config import API_BASE_URL, API_TIMEOUT  # noqa: F401  (se leen de variables de entorno)
from core.oficios import OFICIOS_PORTADA

# Carpeta raíz del proyecto (proyecto_overol/), un nivel sobre core/
APP_DIR = Path(__file__).resolve().parent.parent

# Todo el front trabaja contra el backend Django (el modo local con SQLite se eliminó).
# La URL de la API y el resto de la configuración por entorno están en core/config.py.

# Versión de la política de privacidad y términos de uso que acepta el usuario al registrarse
PRIVACY_POLICY_VERSION = "2026-10"

# Rol del backend → rol del front
API_ROLES = {"CLIENT": "cliente", "PROFESSIONAL": "profesional", "ADMIN": "admin"}


# Pantallas sin endpoint en el backend: se ocultan de la barra y se reactivan cuando
# exista (PEDIDO_BACKEND_PARA_NEFI.md). Valor: «pedido».
PANTALLAS_PENDIENTES_API = {
    "cliente": {},
    "profesional": {},
    "admin": {
        "⭐ Moderación": "pedido",
        "🎓 Contenidos": "pedido",
        "📜 Trazabilidad": "pedido",
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

# Oficios de la portada: lista oficial del equipo agrupada por categorías (core/oficios.py).
# La lista completa de oficios del backend (66) sale de GET /api/catalog/categories/.

ROLES = {
    "cliente": "Cliente",
    "profesional": "Profesional",
    "admin": "Administrador",
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

# Ícono de cada oficio del backend (perfiles): sale de la lista de la portada (core/oficios.py)
OFICIOS_INFO = [(icono, backend, nombre) for nombre, backend, icono in OFICIOS_PORTADA]

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

# Franjas horarias que el cliente puede pedir
FRANJAS_HORARIAS = [
    "09:00 - 11:00",
    "11:00 - 13:00",
    "15:00 - 17:00",
    "17:00 - 19:00",
]

# Máximo de caracteres en motivos de cancelación y mensajes a soporte
MAX_TEXTO = 500

# Asunto de un ticket de soporte (el backend acepta hasta 160)
MAX_ASUNTO = 100

# Duración de la sesión persistente («Mantener mi sesión iniciada»)
DIAS_SESION = 7

# Overol solo cobra la suscripción del profesional: el servicio se paga directo al profesional.
FEE_NOTE = "La tarifa se paga directamente al profesional; Overol no cobra comisión por los servicios."
