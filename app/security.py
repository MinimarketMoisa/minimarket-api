"""Contraseñas en formato Django (pbkdf2_sha256) y tokens JWT tipados y revocables.

Las contraseñas se guardan con el mismo formato que usa Django, así un usuario
creado desde FastAPI puede iniciar sesión en Django Admin y viceversa.
"""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from .config import settings

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 870_000


def _pbkdf2(password: str, salt: str, iteraciones: int) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iteraciones)
    return base64.b64encode(dk).decode("ascii").strip()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(11)  # 22 caracteres, igual que Django
    return f"{ALGORITMO}${ITERACIONES}${salt}${_pbkdf2(password, salt, ITERACIONES)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algoritmo, iteraciones, salt, hash_ = encoded.split("$", 3)
        if algoritmo != ALGORITMO:
            return False
        esperado = _pbkdf2(password, salt, int(iteraciones))
    except (ValueError, AttributeError, TypeError):
        return False
    return hmac.compare_digest(esperado, hash_)


# Hash falso precalculado para responder en tiempo constante ante usuarios inexistentes
# (evita enumeración de usuarios midiendo tiempos de respuesta de PBKDF2)
DUMMY_HASH = hash_password("dummy_password_timing_attack_mitigation")


def password_fingerprint(encoded: str) -> str:
    """
    Huella digital del hash de contraseña.
    Si la contraseña cambia (en FastAPI o en Django Admin), todos los tokens viejos mueren inmediatamente.
    """
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]


def _firmar(claims: dict, tipo: str, vigencia: timedelta) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {**claims, "type": tipo, "iat": ahora, "exp": ahora + vigencia}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _leer(token: str, tipo: str) -> Optional[dict]:
    try:
        p = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError:
        return None
    if p.get("type") != tipo or not str(p["sub"]).isdigit():
        return None
    return p


def create_access_token(u) -> str:
    """Crea un access token con id, rol, versión de token y fingerprint de contraseña."""
    return _firmar(
        {
            "sub": str(u.id_usuario),
            "rol": u.rol.nombre,
            "ver": u.token_version,
            "pwd": password_fingerprint(u.password),
        },
        "access",
        timedelta(minutes=settings.jwt_expire_minutes),
    )


def decode_token(token: str) -> Optional[dict]:
    return _leer(token, "access")


def create_email_verification_token(id_usuario: int, email: str) -> str:
    return _firmar(
        {"sub": str(id_usuario), "email": email.lower()},
        "email_verification",
        timedelta(hours=settings.email_verification_token_expire_hours),
    )


def decode_email_verification_token(token: str) -> Optional[dict]:
    return _leer(token, "email_verification")


def create_email_change_token(id_usuario: int, nuevo_email: str) -> str:
    return _firmar(
        {"sub": str(id_usuario), "nuevo_email": nuevo_email.lower()},
        "email_change",
        timedelta(minutes=15),
    )


def decode_email_change_token(token: str) -> Optional[dict]:
    return _leer(token, "email_change")


def create_password_reset_token(u) -> str:
    """Token de un solo uso para restablecer contraseña."""
    return _firmar(
        {
            "sub": str(u.id_usuario),
            "ver": u.token_version,
            "pwd": password_fingerprint(u.password),
        },
        "password_reset",
        timedelta(minutes=settings.password_reset_token_expire_minutes),
    )


def decode_password_reset_token(token: str) -> Optional[dict]:
    return _leer(token, "password_reset")
