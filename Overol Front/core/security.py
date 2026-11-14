"""Validaciones del formulario (RUT, correo, teléfono y contraseña). Las contraseñas y los
documentos los guarda el backend: el front ya no los procesa."""

import re


def normalize_rut(rut: str) -> str:
    return rut.upper().replace(".", "").replace(" ", "")


def validate_rut_format(rut: str) -> bool:
    rut = normalize_rut(rut)
    return bool(re.fullmatch(r"\d{7,8}-[\dK]", rut))


def validate_email(email: str) -> bool:
    return bool(
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email.strip(),
        )
    )


def validate_rut_dv(rut: str) -> bool:
    """Valida el dígito verificador del RUT chileno (módulo 11)."""
    rut = normalize_rut(rut)
    if not re.fullmatch(r"\d{7,8}-[\dK]", rut):
        return False

    body, dv = rut.split("-")
    total, factor = 0, 2
    for digit in reversed(body):
        total += int(digit) * factor
        factor = 2 if factor == 7 else factor + 1

    remainder = 11 - (total % 11)
    expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)
    return dv == expected


def validate_password_strength(password: str) -> list:
    """Devuelve una lista de requisitos que la contraseña NO cumple."""
    problems = []
    if len(password) < 8:
        problems.append("al menos 8 caracteres")
    if not re.search(r"[A-Za-z]", password):
        problems.append("al menos una letra")
    if not re.search(r"\d", password):
        problems.append("al menos un número")
    return problems


def validate_phone(phone: str) -> bool:
    """Teléfono con 8 a 15 dígitos (admite +, espacios y guiones)."""
    digits = re.sub(r"\D", "", phone or "")
    return bool(re.fullmatch(r"[\d\s+\-]+", (phone or "").strip())) and 8 <= len(digits) <= 15
