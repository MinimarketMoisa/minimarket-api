"""Reglas de negocio: eleccion de sucursal, asignacion de repartidor y estados."""
import math
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings
from ..schemas import (
    ClienteParaRepartidorOut,
    DestinoEntregaOut,
    DetalleOut,
    PedidoIn,
    PedidoOut,
    PedidoParaRepartidorOut,
    SucursalEntregaOut,
)

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
    if rol == "ADMIN":
        return True
    if pedido.id_cliente == usuario.id_usuario:
        return True
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

    nombre_repartidor = None
    telefono_repartidor = None
    if p.id_repartidor:
        if hasattr(p, "repartidor_perfil") and p.repartidor_perfil and p.repartidor_perfil.usuario:
            nombre_repartidor = p.repartidor_perfil.usuario.nombre_completo
            telefono_repartidor = p.repartidor_perfil.usuario.telefono
        else:
            sess = Session.object_session(p)
            if sess:
                rep = sess.get(m.Usuario, p.id_repartidor)
                if rep:
                    nombre_repartidor = rep.nombre_completo
                    telefono_repartidor = rep.telefono

    return PedidoOut(
        id_pedido=p.id_pedido,
        id_cliente=p.id_cliente,
        id_sucursal=p.id_sucursal,
        id_repartidor=p.id_repartidor,
        nombre_repartidor=nombre_repartidor,
        telefono_repartidor=telefono_repartidor,
        id_direccion=p.id_direccion,
        canal=p.canal,
        tipo_entrega=p.tipo_entrega,
        metodo_pago=p.metodo_pago,
        estado=p.estado,
        estado_pago=p.estado_pago,
        estado_repartidor=getattr(p, "estado_repartidor", None),
        costo_envio=p.costo_envio,
        total=p.total,
        fecha_creacion=p.fecha_creacion,
        detalles=detalles,
    )


def pedido_para_repartidor_out(p: m.Pedido, db: Session) -> PedidoParaRepartidorOut:
    """
    Construye la vista de pedido enriquecida específicamente para repartidores:
    Oculta el id_cliente por privacidad pero incluye el nombre y teléfono del cliente,
    los datos completos de la dirección destino y los datos completos de la sucursal de origen.
    """
    cliente = db.get(m.Usuario, p.id_cliente)
    cliente_out = ClienteParaRepartidorOut(
        nombre_completo=cliente.nombre_completo if cliente else "Cliente",
        telefono=cliente.telefono if cliente else None,
    )

    destino_out = None
    if p.id_direccion:
        dir_obj = db.get(m.Direccion, p.id_direccion)
        if dir_obj:
            destino_out = DestinoEntregaOut(
                id_direccion=dir_obj.id_direccion,
                detalle_direccion=dir_obj.detalle_direccion,
                punto_referencia=dir_obj.punto_referencia,
                municipio=dir_obj.municipio.nombre if dir_obj.municipio else None,
            )

    sucursal = db.get(m.Sucursal, p.id_sucursal)
    sucursal_out = SucursalEntregaOut(
        id_sucursal=sucursal.id_sucursal,
        nombre=sucursal.nombre,
        direccion=sucursal.direccion,
        telefono=sucursal.telefono,
        latitud=sucursal.latitud,
        longitud=sucursal.longitud,
    )

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

    return PedidoParaRepartidorOut(
        id_pedido=p.id_pedido,
        estado=p.estado,
        estado_repartidor=getattr(p, "estado_repartidor", None),
        canal=p.canal,
        metodo_pago=p.metodo_pago,
        estado_pago=p.estado_pago,
        costo_envio=p.costo_envio,
        total=p.total,
        fecha_creacion=p.fecha_creacion,
        cliente=cliente_out,
        destino=destino_out,
        sucursal=sucursal_out,
        detalles=detalles,
    )


# ------------------------------------------------------------------ repartidores
def repartidor_mas_cercano(
    db: Session, lat_sucursal: float, lon_sucursal: float, excluidos: Optional[set[int]] = None
) -> Optional[m.PerfilRepartidor]:
    """Busca el repartidor LIBRE más cercano a la sucursal, ignorando los id_repartidor en excluidos."""
    candidatos = db.scalars(
        select(m.PerfilRepartidor)
        .join(m.Usuario, m.PerfilRepartidor.id_repartidor == m.Usuario.id_usuario)
        .where(
            m.PerfilRepartidor.estado_operativo == "LIBRE",
            m.PerfilRepartidor.latitud_actual.is_not(None),
            m.PerfilRepartidor.longitud_actual.is_not(None),
            m.Usuario.activo.is_(True),
        )
    ).all()
    if excluidos:
        candidatos = [c for c in candidatos if c.id_repartidor not in excluidos]
    if not candidatos:
        return None
    return min(
        candidatos,
        key=lambda r: haversine_km(
            lat_sucursal, lon_sucursal, float(r.latitud_actual), float(r.longitud_actual)
        ),
    )


def asignar_repartidor(db: Session, pedido: m.Pedido) -> bool:
    """Asigna al repartidor libre más cercano que NO haya rechazado previamente este pedido."""
    if pedido.tipo_entrega != "DOMICILIO" or pedido.id_repartidor is not None:
        return False
    sucursal = db.get(m.Sucursal, pedido.id_sucursal)
    if sucursal is None or sucursal.latitud is None or sucursal.longitud is None:
        return False

    rechazados = set(
        db.scalars(
            select(m.RechazoPedido.id_repartidor).where(m.RechazoPedido.id_pedido == pedido.id_pedido)
        ).all()
    )
    # Si el cliente que pide es también repartidor, no puede auto-asignarse su propio pedido
    rechazados.add(pedido.id_cliente)

    elegido = repartidor_mas_cercano(
        db, float(sucursal.latitud), float(sucursal.longitud), excluidos=rechazados
    )
    if elegido is None:
        return False

    pedido.id_repartidor = elegido.id_repartidor
    pedido.estado_repartidor = "ASIGNADO"
    return True


def asignar_pendientes(db: Session) -> None:
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
    pedido.estado_repartidor = None


def aceptar_pedido(db: Session, pedido: m.Pedido, usuario: m.Usuario) -> m.Pedido:
    """El repartidor acepta el pedido asignado."""
    # Bloquear la fila del pedido para prevenir condiciones de carrera
    p = db.scalars(
        select(m.Pedido).where(m.Pedido.id_pedido == pedido.id_pedido).with_for_update()
    ).first()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    if p.id_repartidor != usuario.id_usuario:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este pedido no está asignado a ti")
    if p.estado not in ("PENDIENTE", "PREPARADO"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No se puede aceptar un pedido en estado {p.estado}",
        )
    if p.estado_repartidor == "ACEPTADO":
        return p
    if p.estado_repartidor != "ASIGNADO":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El pedido no está en espera de aceptación (estado actual: {p.estado_repartidor})",
        )

    p.estado_repartidor = "ACEPTADO"
    perfil = db.get(m.PerfilRepartidor, usuario.id_usuario)
    if perfil is not None:
        perfil.estado_operativo = "PENDIENTE"
    db.commit()
    db.refresh(p)
    return p


def rechazar_pedido(
    db: Session, pedido: m.Pedido, usuario: m.Usuario, motivo: Optional[str] = None
) -> tuple[m.Pedido, bool]:
    """El repartidor rechaza el pedido. Se libera al repartidor y se reasigna a otro."""
    p = db.scalars(
        select(m.Pedido).where(m.Pedido.id_pedido == pedido.id_pedido).with_for_update()
    ).first()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    if p.id_repartidor != usuario.id_usuario:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este pedido no está asignado a ti")
    if p.estado not in ("PENDIENTE", "PREPARADO") or p.estado_repartidor != "ASIGNADO":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede rechazar el pedido en su estado actual",
        )

    # 1) Registrar rechazo
    rechazo = m.RechazoPedido(
        id_pedido=p.id_pedido,
        id_repartidor=usuario.id_usuario,
        motivo=motivo,
    )
    db.add(rechazo)

    # 2) Liberar al repartidor que rechazó
    perfil = db.get(m.PerfilRepartidor, usuario.id_usuario)
    if perfil is not None:
        perfil.estado_operativo = "LIBRE"

    # 3) Desvincular del pedido
    p.id_repartidor = None
    p.estado_repartidor = None
    db.flush()

    # 4) Reasignar al siguiente repartidor libre más cercano
    reasignado = asignar_repartidor(db, p)

    db.commit()
    db.refresh(p)
    return p, reasignado


# ------------------------------------------------------------------ pedidos
def crear_pedido(db: Session, cliente: m.Usuario, data: PedidoIn) -> m.Pedido:
    # Límite de pedidos pendientes para evitar acaparamiento de stock
    pendientes_cliente = db.scalar(
        select(func.count(m.Pedido.id_pedido)).where(
            m.Pedido.id_cliente == cliente.id_usuario,
            m.Pedido.estado == "PENDIENTE",
        )
    ) or 0
    if pendientes_cliente >= 5:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Has alcanzado el límite de 5 pedidos pendientes activos. Espera a que se procesen o cancela los anteriores.",
        )

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
    stock = {(i.id_sucursal, i.id_producto): i for i in filas}

    elegida: Optional[m.Sucursal] = None
    for s in sucursales:
        cubre = all(stock.get((s.id_sucursal, pid), m.Inventario(stock_disponible=0)).stock_disponible >= cant
                    for pid, cant in cantidades.items())
        if cubre:
            elegida = s
            break
    if elegida is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ninguna sucursal tiene stock de todos los productos del pedido")

    # 4) descontar inventario y armar el pedido
    subtotal = Decimal("0.00")
    envio = settings.costo_envio if data.tipo_entrega == "DOMICILIO" else Decimal("0.00")
    detalles = []
    for pid, cant in cantidades.items():
        stock[(elegida.id_sucursal, pid)].stock_disponible -= cant
        precio = productos[pid].precio_base
        subtotal += precio * cant
        detalles.append(m.DetallePedido(id_producto=pid, cantidad=cant, precio_unitario=precio))

    pedido = m.Pedido(
        id_cliente=cliente.id_usuario,
        id_sucursal=elegida.id_sucursal,
        id_direccion=id_direccion,
        canal=data.canal,
        tipo_entrega=data.tipo_entrega,
        metodo_pago=data.metodo_pago,
        estado="PENDIENTE",
        estado_pago="PENDIENTE",
        costo_envio=envio,
        total=subtotal + envio,
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
    # Bloquear el pedido con with_for_update para prevenir doble cancelación o carreras
    p = db.scalars(
        select(m.Pedido).where(m.Pedido.id_pedido == pedido.id_pedido).with_for_update()
    ).first()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    # Si el pedido ya está cancelado o entregado, es inmutable
    if p.estado in ("CANCELADO", "ENTREGADO"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El pedido ya está en estado final '{p.estado}' y no puede modificarse",
        )

    rol = usuario.rol.nombre

    # Si es ADMIN, permite cambiar a cualquier estado directo salvo los inmutables ya validados
    if rol != "ADMIN" and nuevo not in TRANSICIONES.get(p.estado, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"No se puede pasar de {p.estado} a {nuevo}"
        )

    gestiona = puede_gestionar_sucursal(db, usuario, p.id_sucursal)
    es_su_repartidor = rol == "REPARTIDOR" and p.id_repartidor == usuario.id_usuario
    domicilio = p.tipo_entrega == "DOMICILIO"

    if rol == "ADMIN":
        permitido = True
    elif nuevo == "PREPARADO":
        permitido = gestiona
    elif nuevo == "EN_RUTA":
        if not domicilio or p.id_repartidor is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Solo un pedido a domicilio con repartidor puede ir en ruta")
        if getattr(p, "estado_repartidor", None) != "ACEPTADO":
            raise HTTPException(status.HTTP_409_CONFLICT, "Debes aceptar el pedido antes de ponerlo en ruta")
        permitido = es_su_repartidor
    elif nuevo == "ENTREGADO":
        if domicilio and p.estado != "EN_RUTA":
            raise HTTPException(status.HTTP_409_CONFLICT, "Un pedido a domicilio debe pasar por EN_RUTA")
        permitido = es_su_repartidor if domicilio else gestiona
    else:  # CANCELADO
        permitido = gestiona or (
            p.id_cliente == usuario.id_usuario and p.estado == "PENDIENTE"
        )

    if not permitido:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para este cambio de estado")

    if nuevo == "CANCELADO":
        restaurar_stock(db, p)
        liberar_repartidor(db, p)
    elif nuevo == "ENTREGADO":
        liberar_repartidor(db, p)
        if p.metodo_pago == "CONTRA_ENTREGA":
            p.estado_pago = "PAGADO"

    p.estado = nuevo
    db.flush()
    if nuevo in ("CANCELADO", "ENTREGADO"):
        asignar_pendientes(db)
    db.commit()
    db.refresh(p)
    return p
