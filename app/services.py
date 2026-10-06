"""Reglas de negocio: eleccion de sucursal, asignacion de repartidor y estados."""
import math
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .config import settings
from .schemas import DetalleOut, PedidoIn, PedidoOut

ESTADOS_ACTIVOS = ("PENDIENTE", "PREPARADO", "EN_RUTA")

# estado actual -> estados a los que puede pasar
TRANSICIONES = {
    "PENDIENTE": {"PREPARADO", "CANCELADO"},
    "PREPARADO": {"EN_RUTA", "ENTREGADO", "CANCELADO"},
    "EN_RUTA": {"ENTREGADO"},
}


# ------------------------------------------------------------------ utilidades
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def puede_gestionar_sucursal(db: Session, usuario: m.Usuario, id_sucursal: int) -> bool:
    rol = usuario.rol.nombre
    if rol == "ADMIN":
        return True
    if rol == "EMPLEADO":
        emp = db.get(m.Empleado, usuario.id_usuario)
        return emp is not None and emp.id_sucursal == id_sucursal
    return False


def puede_ver_pedido(db: Session, usuario: m.Usuario, pedido: m.Pedido) -> bool:
    rol = usuario.rol.nombre
    if rol == "CLIENTE":
        return pedido.id_cliente == usuario.id_usuario
    if rol == "REPARTIDOR":
        return pedido.id_repartidor == usuario.id_usuario
    return puede_gestionar_sucursal(db, usuario, pedido.id_sucursal)


def pedido_a_out(p: m.Pedido) -> PedidoOut:
    detalles = [
        DetalleOut(
            id_producto=d.id_producto,
            nombre_producto=d.producto.nombre,
            cantidad=d.cantidad,
            precio_unitario=d.precio_unitario,
            subtotal=d.precio_unitario * d.cantidad,
        )
        for d in p.detalles
    ]
    return PedidoOut(
        id_pedido=p.id_pedido, id_cliente=p.id_cliente, id_sucursal=p.id_sucursal,
        id_repartidor=p.id_repartidor, id_direccion=p.id_direccion, canal=p.canal,
        tipo_entrega=p.tipo_entrega, metodo_pago=p.metodo_pago, estado=p.estado,
        estado_pago=p.estado_pago, costo_envio=p.costo_envio, total=p.total,
        fecha_creacion=p.fecha_creacion, detalles=detalles,
    )


# ------------------------------------------------------------------ repartidores
def asignar_repartidor(db: Session, pedido: m.Pedido) -> bool:
    """Asigna el repartidor LIBRE mas cercano a la sucursal del pedido."""
    if pedido.tipo_entrega != "DOMICILIO" or pedido.id_repartidor is not None:
        return False
    sucursal = db.get(m.Sucursal, pedido.id_sucursal)
    libres = db.scalars(
        select(m.PerfilRepartidor)
        .join(m.Usuario, m.Usuario.id_usuario == m.PerfilRepartidor.id_repartidor)
        .where(
            m.PerfilRepartidor.estado_operativo == "LIBRE",
            m.PerfilRepartidor.latitud_actual.is_not(None),
            m.Usuario.activo.is_(True),
        )
        .with_for_update(skip_locked=True, of=m.PerfilRepartidor)
    ).all()
    if not libres:
        return False
    mejor = min(
        libres,
        key=lambda r: haversine_km(
            float(sucursal.latitud), float(sucursal.longitud),
            float(r.latitud_actual), float(r.longitud_actual),
        ),
    )
    mejor.estado_operativo = "PENDIENTE"
    pedido.id_repartidor = mejor.id_repartidor
    return True


def asignar_pendientes(db: Session) -> None:
    """Reintenta asignar repartidor a los pedidos a domicilio que quedaron sin uno."""
    pendientes = db.scalars(
        select(m.Pedido)
        .where(
            m.Pedido.tipo_entrega == "DOMICILIO",
            m.Pedido.id_repartidor.is_(None),
            m.Pedido.estado.in_(("PENDIENTE", "PREPARADO")),
        )
        .order_by(m.Pedido.fecha_creacion, m.Pedido.id_pedido)
        .with_for_update(skip_locked=True)
    ).all()
    for pedido in pendientes:
        if not asignar_repartidor(db, pedido):
            break


def liberar_repartidor(db: Session, pedido: m.Pedido) -> None:
    if pedido.id_repartidor is None:
        return
    perfil = db.get(m.PerfilRepartidor, pedido.id_repartidor)
    if perfil is not None:
        perfil.estado_operativo = "LIBRE"


# ------------------------------------------------------------------ pedidos
def crear_pedido(db: Session, cliente: m.Usuario, data: PedidoIn) -> m.Pedido:
    # 1) juntar lineas repetidas del mismo producto
    cantidades: dict[int, int] = {}
    for it in data.items:
        cantidades[it.id_producto] = cantidades.get(it.id_producto, 0) + it.cantidad
    ids_productos = list(cantidades)

    productos = {
        p.id_producto: p
        for p in db.scalars(select(m.Producto).where(m.Producto.id_producto.in_(ids_productos)))
    }
    no_disponibles = [i for i in ids_productos if i not in productos or not productos[i].activo]
    if no_disponibles:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Productos no disponibles: {no_disponibles}")

    # 2) sucursales candidatas segun el tipo de entrega
    if data.tipo_entrega == "DOMICILIO":
        if data.id_direccion is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un pedido a domicilio requiere id_direccion")
        direccion = db.get(m.Direccion, data.id_direccion)
        if direccion is None or direccion.id_cliente != cliente.id_usuario:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Dirección no encontrada")
        filtro = m.Sucursal.id_municipio == direccion.id_municipio
        id_direccion = direccion.id_direccion
    else:
        if data.id_sucursal is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un pedido para retirar requiere id_sucursal")
        filtro = m.Sucursal.id_sucursal == data.id_sucursal
        id_direccion = None

    sucursales = db.scalars(
        select(m.Sucursal).where(m.Sucursal.activa.is_(True), filtro).order_by(m.Sucursal.id_sucursal)
    ).all()
    if not sucursales:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay sucursales disponibles para esa zona")

    # 3) bloquear las filas de inventario y elegir una sucursal que cubra TODO el pedido
    filas = db.scalars(
        select(m.Inventario)
        .where(
            m.Inventario.id_sucursal.in_([s.id_sucursal for s in sucursales]),
            m.Inventario.id_producto.in_(ids_productos),
        )
        .order_by(m.Inventario.id_inventario)
        .with_for_update()
    ).all()
    stock = {(f.id_sucursal, f.id_producto): f for f in filas}

    elegida = None
    for s in sucursales:
        if all(
            (s.id_sucursal, pid) in stock and stock[(s.id_sucursal, pid)].stock_disponible >= cant
            for pid, cant in cantidades.items()
        ):
            elegida = s
            break
    if elegida is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ninguna sucursal tiene stock suficiente para todos los productos del pedido",
        )

    # 4) descontar stock y congelar precios
    envio = settings.costo_envio if data.tipo_entrega == "DOMICILIO" else Decimal("0")
    subtotal = Decimal("0")
    detalles = []
    for pid, cant in cantidades.items():
        stock[(elegida.id_sucursal, pid)].stock_disponible -= cant
        precio = productos[pid].precio_base
        subtotal += precio * cant
        detalles.append(m.DetallePedido(id_producto=pid, cantidad=cant, precio_unitario=precio))

    pedido = m.Pedido(
        id_cliente=cliente.id_usuario, id_sucursal=elegida.id_sucursal, id_direccion=id_direccion,
        canal=data.canal, tipo_entrega=data.tipo_entrega, metodo_pago=data.metodo_pago,
        estado="PENDIENTE", estado_pago="PENDIENTE", costo_envio=envio, total=subtotal + envio,
        detalles=detalles,
    )
    db.add(pedido)
    db.flush()
    if pedido.tipo_entrega == "DOMICILIO":
        asignar_repartidor(db, pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


def restaurar_stock(db: Session, pedido: m.Pedido) -> None:
    for d in pedido.detalles:
        inv = db.scalars(
            select(m.Inventario)
            .where(m.Inventario.id_sucursal == pedido.id_sucursal, m.Inventario.id_producto == d.id_producto)
            .with_for_update()
        ).first()
        if inv is not None:
            inv.stock_disponible += d.cantidad


def cambiar_estado(db: Session, pedido: m.Pedido, nuevo: str, usuario: m.Usuario) -> m.Pedido:
    rol = usuario.rol.nombre
    if nuevo not in TRANSICIONES.get(pedido.estado, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"No se puede pasar de {pedido.estado} a {nuevo}"
        )
    gestiona = puede_gestionar_sucursal(db, usuario, pedido.id_sucursal)
    es_su_repartidor = rol == "REPARTIDOR" and pedido.id_repartidor == usuario.id_usuario
    domicilio = pedido.tipo_entrega == "DOMICILIO"

    if nuevo == "PREPARADO":
        permitido = gestiona
    elif nuevo == "EN_RUTA":
        if not domicilio or pedido.id_repartidor is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Solo un pedido a domicilio con repartidor puede ir en ruta")
        permitido = rol == "ADMIN" or es_su_repartidor
    elif nuevo == "ENTREGADO":
        if domicilio and pedido.estado != "EN_RUTA":
            raise HTTPException(status.HTTP_409_CONFLICT, "Un pedido a domicilio debe pasar por EN_RUTA")
        permitido = (rol == "ADMIN" or es_su_repartidor) if domicilio else gestiona
    else:  # CANCELADO
        permitido = gestiona or (
            rol == "CLIENTE" and pedido.id_cliente == usuario.id_usuario and pedido.estado == "PENDIENTE"
        )
    if not permitido:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para este cambio de estado")

    if nuevo == "CANCELADO":
        restaurar_stock(db, pedido)
        liberar_repartidor(db, pedido)
    elif nuevo == "ENTREGADO":
        liberar_repartidor(db, pedido)
        if pedido.metodo_pago == "CONTRA_ENTREGA":
            pedido.estado_pago = "PAGADO"

    pedido.estado = nuevo
    db.flush()
    if nuevo in ("CANCELADO", "ENTREGADO"):
        asignar_pendientes(db)
    db.commit()
    return pedido
