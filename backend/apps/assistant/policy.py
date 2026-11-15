import re
import unicodedata


OUT_OF_SCOPE_RESPONSE = (
    'Cuéntame qué problema del hogar tienes y te recomiendo el oficio del catálogo '
    'que puede ayudarte.'
)

UNIDENTIFIED_TRADE_RESPONSE = (
    'No logro identificar el oficio adecuado con esa descripción. '
    '¿Puedes contarme brevemente qué elemento necesita reparación?'
)

_DOMAIN_TERMS = (
    'overol', 'hogar', 'casa', 'departamento', 'domicilio', 'mantencion',
    'reparacion', 'arreglo', 'falla', 'averia', 'filtracion', 'humedad',
    'fuga', 'gotera', 'gotea', 'goteo', 'bano', 'ducha', 'grifo', 'grifos',
    'banera', 'caneria', 'desague', 'wc', 'inodoro',
    'lavaplatos', 'lavamanos', 'lavatorio', 'llave de paso', 'calefont',
    'caldera', 'agua caliente', 'gasfiter', 'gasfiteria', 'gas', 'enchufe',
    'interruptor', 'tablero electrico', 'cableado', 'electricidad', 'electrico',
    'luz', 'cortocircuito', 'cerrajeria', 'cerradura', 'llave', 'puerta',
    'ventana', 'carpinteria', 'mueble', 'pintura', 'pintor', 'climatizacion',
    'aire acondicionado', 'techo', 'canaleta', 'piso', 'grieta', 'pared', 'profesional',
    'especialista', 'tecnico', 'visita', 'tarifa', 'garantia', 'verificacion',
    'rut', 'cedula', 'solicitud de servicio', 'contratar', 'oficio',
    'certificado', 'sec',
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

def normalize_text(text):
    normalized = unicodedata.normalize('NFKD', text.casefold())
    return ''.join(char for char in normalized if not unicodedata.combining(char))


def is_in_domain(text):
    normalized = normalize_text(text)
    return any(term in normalized for term in _DOMAIN_TERMS)


def inspect_message(text):
    normalized = normalize_text(text)
    if any(re.search(pattern, normalized) for pattern in _INJECTION_PATTERNS):
        return OUT_OF_SCOPE_RESPONSE
    if any(re.search(pattern, normalized) for pattern in _OFF_TOPIC_PATTERNS):
        return OUT_OF_SCOPE_RESPONSE
    if not is_in_domain(text):
        return OUT_OF_SCOPE_RESPONSE
    return None
