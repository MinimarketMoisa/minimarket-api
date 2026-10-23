import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario
from .security import decode_token, password_fingerprint

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise error
    try:
        id_usuario = int(payload["sub"])
    except (KeyError, ValueError):
        raise error

    usuario = db.get(Usuario, id_usuario)
    if usuario is None or not usuario.activo:
        raise error

    # Revocación de sesiones: verificar versión del token
    if "ver" not in payload or payload["ver"] != usuario.token_version:
        raise error

    # Revocación por cambio de contraseña (incluso si se cambió desde Django Admin)
    if "pwd" not in payload or not hmac.compare_digest(
        payload["pwd"], password_fingerprint(usuario.password)
    ):
        raise error

    # Exigir verificación de correo
    if not usuario.email_verificado:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Debes verificar tu correo electrónico antes de continuar.",
        )

    return usuario


def require_roles(*roles: str):
    """Exige que el usuario del token tenga alguno de los roles indicados."""
    def comprobar(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol.nombre not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
        return usuario
    return comprobar
