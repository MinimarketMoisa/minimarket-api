from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..deps import require_roles
from ..schemas import DireccionIn, DireccionOut

router = APIRouter(prefix="/direcciones", tags=["Direcciones"])


@router.get("", response_model=list[DireccionOut])
def mis_direcciones(usuario: m.Usuario = Depends(require_roles("CLIENTE")), db: Session = Depends(get_db)):
    return db.scalars(
        select(m.Direccion).where(m.Direccion.id_cliente == usuario.id_usuario).order_by(m.Direccion.id_direccion)
    ).all()


@router.post("", response_model=DireccionOut, status_code=status.HTTP_201_CREATED)
def crear_direccion(
    data: DireccionIn, usuario: m.Usuario = Depends(require_roles("CLIENTE")), db: Session = Depends(get_db)
):
    if db.get(m.Municipio, data.id_municipio) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Municipio no encontrado")
    direccion = m.Direccion(id_cliente=usuario.id_usuario, **data.model_dump())
    db.add(direccion)
    db.commit()
    return direccion


@router.delete("/{id_direccion}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_direccion(
    id_direccion: int, usuario: m.Usuario = Depends(require_roles("CLIENTE")), db: Session = Depends(get_db)
):
    direccion = db.get(m.Direccion, id_direccion)
    if direccion is None or direccion.id_cliente != usuario.id_usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dirección no encontrada")
    try:
        db.delete(direccion)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "La dirección ya se usó en pedidos y no se puede borrar")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
