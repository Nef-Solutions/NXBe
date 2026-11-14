import re
import unicodedata


OUT_OF_SCOPE_RESPONSE = (
    'Soy el asistente exclusivo de Overol. Solo puedo ayudarte con diagnósticos '
    'de fallas en tu hogar, búsqueda de especialistas (gasfitería, electricidad, '
    'etc.) o dudas sobre nuestra plataforma. ¿En qué reparación te puedo orientar hoy?'
)

SAFETY_RESPONSE = (
    'Eso puede ser peligroso. Aléjate del área y no manipules instalaciones de gas '
    'ni eléctricas. Si hay olor a gas, humo, fuego o riesgo inmediato, evacúa y '
    'contacta a los servicios de emergencia o a tu proveedor de gas. Para revisarlo, '
    'solicita un profesional certificado de Overol.'
)

_DOMAIN_TERMS = (
    'overol', 'hogar', 'casa', 'departamento', 'domicilio', 'mantencion',
    'reparacion', 'arreglo', 'falla', 'averia', 'filtracion', 'humedad',
    'fuga', 'caneria', 'desague', 'wc', 'inodoro', 'lavaplatos', 'lavamanos',
    'llave de paso', 'calefont', 'caldera', 'agua caliente', 'gasfiter',
    'gasfiteria', 'gas', 'enchufe', 'interruptor', 'tablero electrico',
    'cableado', 'electricidad', 'electrico', 'luz', 'cortocircuito',
    'cerrajeria', 'cerradura', 'llave', 'puerta', 'ventana', 'carpinteria',
    'mueble', 'pintura', 'pintor', 'climatizacion', 'aire acondicionado',
    'techo', 'canaleta', 'piso', 'pared', 'profesional', 'especialista',
    'tecnico', 'visita', 'tarifa', 'garantia', 'verificacion', 'rut',
    'cedula', 'solicitud de servicio', 'contratar', 'oficio', 'certificado',
    'sec',
)

_INJECTION_PATTERNS = (
    r'\bignora(?:r)?\b.{0,50}\b(?:instrucciones|reglas|indicaciones|prompt)\b',
    r'\bolvida(?:r)?\b.{0,50}\b(?:instrucciones|reglas|indicaciones|prompt)\b',
    r'\bignore\b.{0,50}\b(?:previous|prior|all)\b',
    r'\bforget\b.{0,50}\b(?:instructions|rules|prompt)\b',
    r'\b(?:actua|actuar|finge|simula)\b.{0,40}\b(?:como|ser)\b',
    r'\b(?:act as|pretend to be|developer mode|jailbreak|dan mode)\b',
    r'\b(?:revela|muestra|imprime|copia)\b.{0,40}\b(?:prompt|instrucciones|reglas internas)\b',
)
_OFF_TOPIC_PATTERNS = (
    r'\b(?:receta|recetas|ingredientes|hornear)\b',
    r'\b(?:tarea escolar|deberes|ensayo escolar|resumen escolar|estudiar para)\b',
    r'\b(?:matematicas?|ecuaciones?|politica|elecciones?|futbol|deportes?|chistes?)\b',
    r'\b(?:programacion|escribir codigo|depurar codigo|cultura general)\b',
)

_GAS_EMERGENCY = re.compile(
    r'\b(?:olor|huele|fuga|escape)\b.{0,35}\b(?:gas|calefont)\b'
    r'|\b(?:gas|calefont)\b.{0,35}\b(?:fuga|escapando|se escapa)\b'
    r'|\b(?:incendio|fuego|explosion|exploto)\b'
)
_ELECTRICAL_EMERGENCY = re.compile(
    r'\b(?:chispa|chispas|arco electrico|cable pelado|electrocut|descarga electrica)\b'
)
_DANGEROUS_INSTRUCTIONS = re.compile(
    r'\b(?:puentea|puentear|anula|anular|desactiva|desactivar|manipula|manipular|'
    r'repara|reparar|conecta|conectar|desconecta|desconectar|empalma|empalmar|'
    r'cambia|cambiar|reemplaza|reemplazar|instala|instalar|abre|abrir|desarma|'
    r'desarmar|desmonta|desmontar|interviene|intervenir|ajusta|ajustar|purga|purgar)\b'
    r'.{0,55}\b(?:gas|calefont|caldera|medidor|tablero|cable|circuito|enchufe|'
    r'valvula|regulador|instalacion electrica)\b'
)


def _normalize(text):
    normalized = unicodedata.normalize('NFKD', text.casefold())
    return ''.join(char for char in normalized if not unicodedata.combining(char))


def is_in_domain(text):
    normalized = _normalize(text)
    return any(term in normalized for term in _DOMAIN_TERMS)


def inspect_message(text):
    normalized = _normalize(text)
    if any(re.search(pattern, normalized) for pattern in _INJECTION_PATTERNS):
        return OUT_OF_SCOPE_RESPONSE
    if _GAS_EMERGENCY.search(normalized) or _ELECTRICAL_EMERGENCY.search(normalized):
        return SAFETY_RESPONSE
    if _DANGEROUS_INSTRUCTIONS.search(normalized):
        return SAFETY_RESPONSE
    if any(re.search(pattern, normalized) for pattern in _OFF_TOPIC_PATTERNS):
        return OUT_OF_SCOPE_RESPONSE
    if not is_in_domain(text):
        return OUT_OF_SCOPE_RESPONSE
    return None


def validate_assistant_response(text):
    normalized = _normalize(text)
    if _DANGEROUS_INSTRUCTIONS.search(normalized):
        return SAFETY_RESPONSE
    if any(re.search(pattern, normalized) for pattern in _OFF_TOPIC_PATTERNS):
        return OUT_OF_SCOPE_RESPONSE
    if not is_in_domain(text):
        return OUT_OF_SCOPE_RESPONSE
    return None
