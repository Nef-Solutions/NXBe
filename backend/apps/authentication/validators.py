import re
from django.core.exceptions import ValidationError

def validate_rut_chileno(rut: str) -> str:
    """
    Valida y formatea un RUT chileno usando algoritmo Módulo 11.
    Acepta formatos como: '12.345.678-5', '12345678-k', '123456785'.
    Retorna el RUT limpio en formato canónico: XXXXXXXX-X (con K mayúscula).
    """
    if not rut:
        raise ValidationError("El RUT no puede estar vacío.")

    # 1. Limpieza de caracteres de formato
    rut_limpio = rut.replace(".", "").replace("-", "").strip().upper()

    if len(rut_limpio) < 8 or len(rut_limpio) > 9:
        raise ValidationError("El largo del RUT no es válido.")

    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1]

    if not cuerpo.isdigit():
        raise ValidationError("El cuerpo del RUT debe contener únicamente dígitos numéricos.")
    if set(cuerpo) == {'0'}:
        raise ValidationError("El cuerpo del RUT no puede estar compuesto solo por ceros.")

    # 2. Algoritmo Módulo 11
    suma = 0
    multiplicador = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = suma % 11
    esperado = 11 - resto
    dv_calculado = 'K' if esperado == 10 else '0' if esperado == 11 else str(esperado)

    if dv != dv_calculado:
        raise ValidationError(f"RUT inválido: el dígito verificador ingresado '{dv}' no coincide.")

    return f"{cuerpo}-{dv}"


def sanitize_person_name(name: str) -> str:
    """
    Sanitiza nombres y apellidos de personas.
    - Soporta apóstrofes legítimos como O'Higgins, D'Angelo, etc.
    - Normaliza apóstrofe tipográfico (’ -> ').
    - Elimina espacios sobrantes y caracteres de control o puntuación suelta al final.
    - Rechaza secuencias SQL maliciosas (; -- /* \x00).
    """
    if not name:
        return ""

    # 1. Normalizar apóstrofes tipográficos a apóstrofe estándar
    texto = name.replace("’", "'").replace("`", "'")

    # 2. Eliminar puntos o signos sueltos en los bordes y normalizar espacios múltiples
    texto = re.sub(r'[\s.]+$', '', texto)  # Quita espacios o puntos finales como en "O'higgin's . "
    texto = re.sub(r'^[\s.]+', '', texto)  # Quita del inicio si existiesen
    texto = re.sub(r'\s+', ' ', texto)     # Colapsa espacios dobles internos

    # 3. Lista de caracteres prohibidos directos (vectores de inyección)
    patrones_peligrosos = [r';', r'--', r'/\*', r'\*/', r'@@', r'char\(', r'nchar\(']
    for patron in patrones_peligrosos:
        if re.search(patron, texto, re.IGNORECASE):
            raise ValidationError("El nombre contiene secuencias o caracteres no permitidos.")

    # 4. Validar que contenga solo letras (incluye acentos, ñ/Ñ), espacios y apóstrofes
    patron_permitido = r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s']+$"
    if not re.match(patron_permitido, texto):
        raise ValidationError("El nombre solo debe contener letras, espacios y apóstrofes válidos.")

    return texto