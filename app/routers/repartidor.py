from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .. import services
from ..database import get_db
from ..deps import require_roles
from ..schemas import PedidoOut, RepartidorEstadoIn, UbicacionIn

router = APIRouter(prefix="/repartidor", tags=["Repartidor"])


def _perfil(db: Session, usuario: m.Usuario) -> m.PerfilRepartidor:
    perfil = db.get(m.PerfilRepartidor, usuario.id_usuario)
    if perfil is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El usuario no tiene perfil de repartidor")
    return perfil


@router.get("/mis-entregas", response_model=list[PedidoOut])
def mis_entregas(usuario: m.Usuario = Depends(require_roles("REPARTIDOR")), db: Session = Depends(get_db)):
    pedidos = db.scalars(
        select(m.Pedido)
        .where(m.Pedido.id_repartidor == usuario.id_usuario, m.Pedido.estado.in_(services.ESTADOS_ACTIVOS))
        .order_by(m.Pedido.fecha_creacion)
    ).all()
    return [services.pedido_a_out(p) for p in pedidos]


@router.patch("/ubicacion", status_code=status.HTTP_204_NO_CONTENT)
def actualizar_ubicacion(
    data: UbicacionIn, usuario: m.Usuario = Depends(require_roles("REPARTIDOR")), db: Session = Depends(get_db)
):
    """La app móvil la envía cada cierto tiempo."""
    perfil = _perfil(db, usuario)
    perfil.latitud_actual = Decimal(str(data.latitud))
    perfil.longitud_actual = Decimal(str(data.longitud))
    perfil.ultima_actualizacion = datetime.now(timezone.utc)
    db.flush()
    if perfil.estado_operativo == "LIBRE":
        services.asignar_pendientes(db)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/estado")
def cambiar_estado(
    data: RepartidorEstadoIn, usuario: m.Usuario = Depends(require_roles("REPARTIDOR")), db: Session = Depends(get_db)
):
    """LIBRE = disponible. PENDIENTE = ocupado (o fuera de servicio)."""
    perfil = _perfil(db, usuario)
    if data.estado == "LIBRE":
        activas = db.scalar(
            select(m.Pedido.id_pedido).where(
                m.Pedido.id_repartidor == usuario.id_usuario, m.Pedido.estado.in_(services.ESTADOS_ACTIVOS)
            ).limit(1)
        )
        if activas is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Tienes entregas activas; termínalas primero")
    perfil.estado_operativo = data.estado
    db.flush()
    if data.estado == "LIBRE":
        services.asignar_pendientes(db)
    db.commit()
    return {"estado": perfil.estado_operativo}
