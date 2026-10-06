from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .. import services
from ..database import get_db
from ..deps import require_roles
from ..schemas import InventarioIn, InventarioOut

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/sucursal/{id_sucursal}", response_model=list[InventarioOut])
def ver_inventario(
    id_sucursal: int,
    usuario: m.Usuario = Depends(require_roles("EMPLEADO", "ADMIN")), db: Session = Depends(get_db),
):
    if not services.puede_gestionar_sucursal(db, usuario, id_sucursal):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Esa no es tu sucursal")
    filas = db.execute(
        select(m.Inventario, m.Producto.nombre)
        .join(m.Producto, m.Producto.id_producto == m.Inventario.id_producto)
        .where(m.Inventario.id_sucursal == id_sucursal)
        .order_by(m.Producto.nombre)
    ).all()
    return [
        InventarioOut(
            id_sucursal=inv.id_sucursal, id_producto=inv.id_producto, nombre_producto=nombre,
            stock_disponible=inv.stock_disponible, fecha_vencimiento=inv.fecha_vencimiento,
        )
        for inv, nombre in filas
    ]


@router.put("", response_model=InventarioOut)
def fijar_stock(
    data: InventarioIn,
    usuario: m.Usuario = Depends(require_roles("EMPLEADO", "ADMIN")), db: Session = Depends(get_db),
):
    """Fija el stock de un producto en una sucursal (ingreso de mercadería o ajuste)."""
    if not services.puede_gestionar_sucursal(db, usuario, data.id_sucursal):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Esa no es tu sucursal")
    producto = db.get(m.Producto, data.id_producto)
    if producto is None or db.get(m.Sucursal, data.id_sucursal) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto o sucursal no encontrados")
    inv = db.scalars(
        select(m.Inventario)
        .where(m.Inventario.id_sucursal == data.id_sucursal, m.Inventario.id_producto == data.id_producto)
        .with_for_update()
    ).first()
    if inv is None:
        inv = m.Inventario(id_sucursal=data.id_sucursal, id_producto=data.id_producto)
        db.add(inv)
    inv.stock_disponible = data.stock_disponible
    inv.fecha_vencimiento = data.fecha_vencimiento
    db.commit()
    return InventarioOut(
        id_sucursal=inv.id_sucursal, id_producto=inv.id_producto, nombre_producto=producto.nombre,
        stock_disponible=inv.stock_disponible, fecha_vencimiento=inv.fecha_vencimiento,
    )
