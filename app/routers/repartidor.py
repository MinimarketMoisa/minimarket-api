from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .. import services
from ..database import get_db
from ..deps import require_roles
from ..schemas import (
    PedidoOut,
    PedidoParaRepartidorOut,
    RechazoIn,
    RechazoOut,
    RechazoRepartidorOut,
    RepartidorEstadoIn,
    UbicacionIn,
)

router = APIRouter(prefix="/repartidor", tags=["Repartidor"])


def _perfil(db: Session, usuario: m.Usuario) -> m.PerfilRepartidor:
    perfil = db.get(m.PerfilRepartidor, usuario.id_usuario)
    if perfil is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El usuario no tiene perfil de repartidor")
    return perfil


@router.get("/pedido-entrante", response_model=Optional[PedidoParaRepartidorOut])
def pedido_entrante(
    usuario: m.Usuario = Depends(require_roles("REPARTIDOR")),
    db: Session = Depends(get_db),
):
    """
    (Para Repartidor / App Móvil) Consulta si hay un nuevo pedido que acaba de caer
    y está esperando que este repartidor lo acepte o lo rechace.
    Incluye todos los datos de contacto y entrega del cliente (nombre, teléfono, dirección,
    referencia, sucursal de recogida y total) pero OMITIENDO su id_cliente.
    Si no hay pedidos pendientes de responder, devuelve null.
    """
    pedido = db.scalar(
        select(m.Pedido)
        .where(
            m.Pedido.id_repartidor == usuario.id_usuario,
            m.Pedido.estado_repartidor == "ASIGNADO",
            m.Pedido.estado.in_(services.ESTADOS_ACTIVOS),
        )
        .order_by(m.Pedido.fecha_creacion.desc())
    )
    if pedido is None:
        return None
    return services.pedido_para_repartidor_out(pedido, db)


@router.get("/mis-entregas", response_model=list[PedidoParaRepartidorOut])
def mis_entregas(
    estado_repartidor: Optional[str] = Query(
        None, description="Filtrar por 'ASIGNADO' (pendiente de aceptar) o 'ACEPTADO' (en curso)"
    ),
    usuario: m.Usuario = Depends(require_roles("REPARTIDOR")),
    db: Session = Depends(get_db),
):
    """
    Lista los pedidos asignados al repartidor con toda la información de entrega
    y contacto del cliente (sin su id_cliente).
    """
    query = (
        select(m.Pedido)
        .where(
            m.Pedido.id_repartidor == usuario.id_usuario,
            m.Pedido.estado.in_(services.ESTADOS_ACTIVOS),
        )
        .order_by(m.Pedido.fecha_creacion)
    )
    if estado_repartidor:
        query = query.where(m.Pedido.estado_repartidor == estado_repartidor.upper())

    pedidos = db.scalars(query).all()
    return [services.pedido_para_repartidor_out(p, db) for p in pedidos]


@router.get("/pedidos/{id_pedido}", response_model=PedidoParaRepartidorOut)
def ver_pedido_repartidor(
    id_pedido: int,
    usuario: m.Usuario = Depends(require_roles("REPARTIDOR")),
    db: Session = Depends(get_db),
):
    """Consulta la tarjeta completa de un pedido asignado a este repartidor."""
    pedido = db.get(m.Pedido, id_pedido)
    if pedido is None or pedido.id_repartidor != usuario.id_usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado o no asignado a ti")
    return services.pedido_para_repartidor_out(pedido, db)


@router.post("/pedidos/{id_pedido}/aceptar", response_model=PedidoParaRepartidorOut)
def aceptar_pedido(
    id_pedido: int,
    usuario: m.Usuario = Depends(require_roles("REPARTIDOR")),
    db: Session = Depends(get_db),
):
    """
    El repartidor acepta el pedido que la API le asignó.
    Pasa su estado de repartidor a 'ACEPTADO' y devuelve la tarjeta completa para la ruta.
    """
    pedido = db.get(m.Pedido, id_pedido)
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    pedido_aceptado = services.aceptar_pedido(db, pedido, usuario)
    return services.pedido_para_repartidor_out(pedido_aceptado, db)


@router.post("/pedidos/{id_pedido}/rechazar", response_model=RechazoRepartidorOut)
def rechazar_pedido(
    id_pedido: int,
    data: Optional[RechazoIn] = None,
    usuario: m.Usuario = Depends(require_roles("REPARTIDOR")),
    db: Session = Depends(get_db),
):
    """
    El repartidor rechaza el pedido.
    La API libera al repartidor actual (queda LIBRE) y reasigna automáticamente
    el pedido al siguiente repartidor libre más cercano.
    """
    pedido = db.get(m.Pedido, id_pedido)
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    motivo = data.motivo if data else None
    pedido_actualizado, reasignado = services.rechazar_pedido(db, pedido, usuario, motivo)

    msg = (
        "Pedido rechazado exitosamente y reasignado a otro repartidor disponible."
        if reasignado
        else "Pedido rechazado exitosamente. En espera de un repartidor libre en la zona."
    )

    return RechazoRepartidorOut(
        mensaje=msg,
        reasignado=reasignado,
        nuevo_repartidor_id=pedido_actualizado.id_repartidor,
        pedido=None,
    )



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

