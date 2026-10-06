"""Contraseñas en formato Django (pbkdf2_sha256) y tokens JWT.

Las contraseñas se guardan con el mismo formato que usa Django, asi un usuario
creado desde FastAPI puede iniciar sesion en Django Admin y viceversa.
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
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(esperado, hash_)


def create_access_token(id_usuario: int, rol: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(id_usuario), "rol": rol, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
