from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..deps import get_current_user
from ..schemas import RegistroIn, TokenOut, UsuarioOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def usuario_out(u: m.Usuario) -> UsuarioOut:
    return UsuarioOut(
        id_usuario=u.id_usuario, nombre_completo=u.nombre_completo,
        email=u.email, telefono=u.telefono, rol=u.rol.nombre,
    )


@router.post("/registro", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registro(data: RegistroIn, db: Session = Depends(get_db)):
    """Registra un CLIENTE. Los demás roles los crea el administrador."""
    email = str(data.email).lower()
    if db.scalar(select(m.Usuario.id_usuario).where(func.lower(m.Usuario.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    rol = db.scalar(select(m.Rol).where(m.Rol.nombre == "CLIENTE"))
    if rol is None:
        raise HTTPException(500, "Falta el rol CLIENTE. Ejecuta: python -m app.init_db")
    usuario = m.Usuario(
        id_rol=rol.id_rol, nombre_completo=data.nombre_completo, email=email,
        password=hash_password(data.password), telefono=data.telefono,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    return usuario_out(usuario)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """`username` es el correo electrónico."""
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == form.username.lower()))
    if usuario is None or not usuario.activo or not verify_password(form.password, usuario.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    usuario.last_login = datetime.now(timezone.utc)
    db.commit()
    return TokenOut(
        access_token=create_access_token(usuario.id_usuario, usuario.rol.nombre),
        id_usuario=usuario.id_usuario, rol=usuario.rol.nombre,
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: m.Usuario = Depends(get_current_user)):
    return usuario_out(usuario)
