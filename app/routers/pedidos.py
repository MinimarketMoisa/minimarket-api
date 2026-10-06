from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .. import services
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..schemas import EstadoIn, EstadoPedido, PagoIn, PedidoIn, PedidoOut

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def _obtener(db: Session, id_pedido: int, usuario: m.Usuario) -> m.Pedido:
    pedido = db.get(m.Pedido, id_pedido)
    # 404 tambien cuando no es suyo, para no revelar que el pedido existe
    if pedido is None or not services.puede_ver_pedido(db, usuario, pedido):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return pedido


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    data: PedidoIn, usuario: m.Usuario = Depends(require_roles("CLIENTE")), db: Session = Depends(get_db)
):
    """Elige sola la sucursal que cubre todo el pedido y, si es a domicilio,
    asigna el repartidor libre más cercano a esa sucursal."""
    return services.pedido_a_out(services.crear_pedido(db, usuario, data))


@router.get("/mis-pedidos", response_model=list[PedidoOut])
def mis_pedidos(usuario: m.Usuario = Depends(require_roles("CLIENTE")), db: Session = Depends(get_db)):
    pedidos = db.scalars(
        select(m.Pedido).where(m.Pedido.id_cliente == usuario.id_usuario).order_by(m.Pedido.id_pedido.desc())
    ).all()
    return [services.pedido_a_out(p) for p in pedidos]


@router.get("", response_model=list[PedidoOut])
def listar_pedidos(
    estado: Optional[EstadoPedido] = None,
    id_sucursal: Optional[int] = None,
    usuario: m.Usuario = Depends(require_roles("EMPLEADO", "ADMIN")),
    db: Session = Depends(get_db),
):
    """Para personal: el EMPLEADO ve solo su sucursal, el ADMIN ve todas."""
    consulta = select(m.Pedido)
    if usuario.rol.nombre == "EMPLEADO":
        emp = db.get(m.Empleado, usuario.id_usuario)
        if emp is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "El empleado no tiene sucursal asignada")
        consulta = consulta.where(m.Pedido.id_sucursal == emp.id_sucursal)
    elif id_sucursal is not None:
        consulta = consulta.where(m.Pedido.id_sucursal == id_sucursal)
    if estado:
        consulta = consulta.where(m.Pedido.estado == estado)
    pedidos = db.scalars(consulta.order_by(m.Pedido.id_pedido.desc()).limit(200)).all()
    return [services.pedido_a_out(p) for p in pedidos]


@router.get("/{id_pedido}", response_model=PedidoOut)
def detalle_pedido(id_pedido: int, usuario: m.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.pedido_a_out(_obtener(db, id_pedido, usuario))


@router.patch("/{id_pedido}/estado", response_model=PedidoOut)
def cambiar_estado(
    id_pedido: int, data: EstadoIn,
    usuario: m.Usuario = Depends(get_current_user), db: Session = Depends(get_db),
):
    pedido = _obtener(db, id_pedido, usuario)
    return services.pedido_a_out(services.cambiar_estado(db, pedido, data.estado, usuario))


@router.patch("/{id_pedido}/pago", response_model=PedidoOut)
def actualizar_pago(
    id_pedido: int, data: PagoIn,
    usuario: m.Usuario = Depends(require_roles("EMPLEADO", "ADMIN")), db: Session = Depends(get_db),
):
    """Confirmar una transferencia recibida."""
    pedido = _obtener(db, id_pedido, usuario)
    pedido.estado_pago = data.estado_pago
    db.commit()
    return services.pedido_a_out(pedido)


@router.post("/{id_pedido}/asignar-repartidor", response_model=PedidoOut)
def asignar_repartidor(
    id_pedido: int,
    usuario: m.Usuario = Depends(require_roles("EMPLEADO", "ADMIN")), db: Session = Depends(get_db),
):
    pedido = _obtener(db, id_pedido, usuario)
    if not services.asignar_repartidor(db, pedido):
        raise HTTPException(status.HTTP_409_CONFLICT, "No hay repartidores libres o el pedido ya tiene uno")
    db.commit()
    return services.pedido_a_out(pedido)
