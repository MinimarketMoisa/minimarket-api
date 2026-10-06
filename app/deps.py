from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    error = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado",
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
    return usuario


def require_roles(*roles: str):
    """Exige que el usuario del token tenga alguno de los roles indicados."""
    def comprobar(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol.nombre not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
        return usuario
    return comprobar
