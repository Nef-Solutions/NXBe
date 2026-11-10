"""Utilidades de seguridad: hash de contraseñas (PBKDF2), validaciones de RUT/correo
y cifrado de los documentos de verificación (Fernet)."""

import base64
import hashlib
import hmac
import os
import re
import secrets
from functools import lru_cache
from pathlib import Path

# Clave de los documentos de verificación: variable de entorno OVEROL_CLAVE_DOCUMENTOS; si no
# existe, un archivo de clave FUERA del repositorio (Documentos/Overol_envs), que se crea si falta.
# OVEROL_CLAVE_DOCUMENTOS_ARCHIVO permite usar otra ruta para ese archivo.
DOCUMENTS_KEY_ENV = "OVEROL_CLAVE_DOCUMENTOS"
DOCUMENTS_KEY_FILE_ENV = "OVEROL_CLAVE_DOCUMENTOS_ARCHIVO"
DEFAULT_DOCUMENTS_KEY_FILE = (
    Path(__file__).resolve().parents[3] / "Overol_envs" / "overol_clave_documentos.key"
)


def hash_password(password: str) -> str:
    """
    Hash PBKDF2-HMAC-SHA256 con salt aleatorio.
    Para producción se recomienda gestionar secretos y
    credenciales con infraestructura segura.
    """
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120_000,
    )
    return (
        "pbkdf2_sha256$120000$"
        + base64.b64encode(salt).decode()
        + "$"
        + base64.b64encode(derived).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


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


@lru_cache(maxsize=1)
def _documents_fernet():
    # Import diferido: la app arranca aunque falte cryptography (solo fallan subir y ver documentos).
    from cryptography.fernet import Fernet

    key = os.environ.get(DOCUMENTS_KEY_ENV, "").strip()

    if not key:
        path = Path(os.environ.get(DOCUMENTS_KEY_FILE_ENV) or DEFAULT_DOCUMENTS_KEY_FILE)

        if path.exists():
            key = path.read_text(encoding="ascii").strip()
        else:
            key = Fernet.generate_key().decode("ascii")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(key, encoding="ascii")
            print(
                f"[Overol] Se generó la clave de cifrado de documentos en {path}. "
                "Respáldala: sin ella no se pueden abrir los documentos ya cifrados."
            )

    return Fernet(key.encode("ascii"))


def encrypt_document(data: bytes) -> bytes:
    return _documents_fernet().encrypt(data)


def decrypt_document(token: bytes) -> bytes:
    return _documents_fernet().decrypt(token)
