from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m
from .. import services
from ..database import SessionLocal, get_db
from ..deps import authenticate_token, get_current_user, require_roles
from ..limiter import limiter
from ..schemas import (
    DenunciaIn,
    DenunciaOut,
    EstadoIn,
    EstadoPedido,
    MensajeRespuesta,
    PagoIn,
    PedidoIn,
    PedidoOut,
    ResolverDenunciaIn,
    SeguimientoPedidoOut,
)
from ..services.email import enviar_factura_pedido
from ..services.tracking import tracking_manager

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def datos_factura(p: m.Pedido) -> dict:
    return {
        "id_pedido": p.id_pedido,
        "fecha": p.fecha_creacion,
        "metodo_pago": p.metodo_pago,
        "estado_pago": p.estado_pago,
        "tipo_entrega": p.tipo_entrega,
        "costo_envio": p.costo_envio,
        "total": p.total,
        "lineas": [
            (
                d.producto.nombre if d.producto else f"Producto #{d.id_producto}",
                d.cantidad,
                d.precio_unitario,
            )
            for d in p.detalles
        ],
    }


def _obtener(db: Session, id_pedido: int, usuario: m.Usuario) -> m.Pedido:
    pedido = db.get(m.Pedido, id_pedido)
    # 404 tambien cuando no es suyo, para no revelar que el pedido existe
    if pedido is None or not services.puede_ver_pedido(db, usuario, pedido):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return pedido


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    data: PedidoIn,
    background_tasks: BackgroundTasks,
    usuario: m.Usuario = Depends(require_roles("CLIENTE", "REPARTIDOR")),
    db: Session = Depends(get_db),
):
    """
    Elige sola la sucursal que cubre todo el pedido y, si es a domicilio,
    asigna el repartidor libre más cercano a esa sucursal.
    Envía automáticamente la factura completa por correo al cliente.
    """
    pedido = services.crear_pedido(db, usuario, data)
    background_tasks.add_task(
        enviar_factura_pedido,
        usuario.email,
        usuario.nombre_completo,
        datos_factura(pedido),
    )
    return services.pedido_a_out(pedido)


@router.get("/mis-pedidos", response_model=list[PedidoOut])
def mis_pedidos(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    usuario: m.Usuario = Depends(require_roles("CLIENTE", "REPARTIDOR")),
    db: Session = Depends(get_db),
):
    pedidos = db.scalars(
        select(m.Pedido)
        .where(m.Pedido.id_cliente == usuario.id_usuario)
        .order_by(m.Pedido.id_pedido.desc())
        .offset(offset)
        .limit(limit)
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


@router.get("/{id_pedido}/seguimiento", response_model=SeguimientoPedidoOut)
def obtener_seguimiento(
    id_pedido: int,
    usuario: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    (Web y Móvil) Obtiene los datos geográficos y de seguimiento de un pedido:
    - Coordenadas y datos de la sucursal de origen.
    - Coordenadas y dirección de entrega del cliente.
    - Coordenadas en vivo y contacto del repartidor asignado.
    Ideal para dibujar la ruta y los marcadores iniciales en Google Maps / Mapbox / Leaflet.
    """
    pedido = _obtener(db, id_pedido, usuario)
    return services.seguimiento_pedido_out(pedido, db)


@router.websocket("/{id_pedido}/ws/seguimiento")
@router.websocket("/{id_pedido}/ws")
async def ws_seguimiento(
    websocket: WebSocket,
    id_pedido: int,
    token: Optional[str] = Query(None),
):
    """
    WebSocket en tiempo real para seguimiento del pedido.
    Se conecta pasando el token JWT en el query string:
    wss://minimarket-api.duckdns.org/pedidos/{id_pedido}/ws/seguimiento?token=<JWT_TOKEN>
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token requerido")
        return

    with SessionLocal() as db:
        try:
            usuario = authenticate_token(token, db)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido o expirado")
            return

        pedido = db.get(m.Pedido, id_pedido)
        if pedido is None or not services.puede_ver_pedido(db, usuario, pedido):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Pedido no encontrado o sin permisos")
            return

        estado_inicial = services.seguimiento_pedido_out(pedido, db).model_dump(mode="json")

    await tracking_manager.connect(id_pedido, websocket)
    try:
        await websocket.send_json({
            "evento": "estado_inicial",
            "datos": estado_inicial,
        })
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        tracking_manager.disconnect(id_pedido, websocket)
    except Exception:
        tracking_manager.disconnect(id_pedido, websocket)


@router.patch("/{id_pedido}/estado", response_model=PedidoOut)
async def cambiar_estado(
    id_pedido: int,
    data: EstadoIn,
    background_tasks: BackgroundTasks,
    usuario: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pedido = _obtener(db, id_pedido, usuario)
    pedido_actualizado = services.cambiar_estado(db, pedido, data.estado, usuario)
    # Notificar via WebSocket a quien esté viendo el pedido en vivo
    await tracking_manager.broadcast_ubicacion(
        id_pedido,
        {
            "evento": "estado_pedido_actualizado",
            "id_pedido": id_pedido,
            "estado": pedido_actualizado.estado,
            "estado_repartidor": getattr(pedido_actualizado, "estado_repartidor", None),
        },
    )
    # Si fue entregado, enviar confirmación final de entrega / ticket
    if data.estado == "ENTREGADO":
        cliente = db.get(m.Usuario, pedido_actualizado.id_cliente)
        if cliente:
            background_tasks.add_task(
                enviar_factura_pedido,
                cliente.email,
                cliente.nombre_completo,
                datos_factura(pedido_actualizado),
            )
    return services.pedido_a_out(pedido_actualizado)


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


@router.post("/{id_pedido}/enviar-factura", response_model=MensajeRespuesta)
@limiter.limit("5/hour")
def reenviar_factura(
    request: Request,
    id_pedido: int,
    background_tasks: BackgroundTasks,
    usuario: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envía la factura completa y detallada de la compra al correo del cliente."""
    pedido = db.get(m.Pedido, id_pedido)
    if pedido is None or not (pedido.id_cliente == usuario.id_usuario or usuario.rol.nombre == "ADMIN"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    cliente = db.get(m.Usuario, pedido.id_cliente)
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    background_tasks.add_task(
        enviar_factura_pedido,
        cliente.email,
        cliente.nombre_completo,
        datos_factura(pedido),
    )
    return MensajeRespuesta(mensaje="Te enviamos la factura a tu correo registrado.")


@router.post("/{id_pedido}/denunciar", response_model=DenunciaOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def denunciar_repartidor(
    request: Request,
    id_pedido: int,
    data: DenunciaIn,
    usuario: m.Usuario = Depends(require_roles("CLIENTE", "REPARTIDOR")),
    db: Session = Depends(get_db),
):
    """
    Permite al cliente denunciar al repartidor asignado a su pedido
    (ej. si el pedido nunca llegó, hubo mala conducta, etc.).
    """
    pedido = db.get(m.Pedido, id_pedido)
    if pedido is None or pedido.id_cliente != usuario.id_usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    if pedido.id_repartidor is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Este pedido no tiene ningún repartidor asignado para denunciar.",
        )

    existente = db.scalar(
        select(m.DenunciaRepartidor).where(
            m.DenunciaRepartidor.id_pedido == id_pedido,
            m.DenunciaRepartidor.estado.in_(("PENDIENTE", "INVESTIGANDO")),
        )
    )
    if existente:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe un reporte en trámite para este pedido.",
        )

    repartidor = db.get(m.Usuario, pedido.id_repartidor)
    nombre_repartidor = repartidor.nombre_completo if repartidor else "Desconocido"

    denuncia = m.DenunciaRepartidor(
        id_pedido=pedido.id_pedido,
        id_cliente=usuario.id_usuario,
        id_repartidor=pedido.id_repartidor,
        motivo=data.motivo,
        descripcion=data.descripcion,
        estado="PENDIENTE",
    )
    db.add(denuncia)
    try:
        db.commit()
        db.refresh(denuncia)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe un reporte en trámite para este pedido.",
        )

    return DenunciaOut(
        id_denuncia=denuncia.id_denuncia,
        id_pedido=denuncia.id_pedido,
        id_cliente=denuncia.id_cliente,
        nombre_cliente=usuario.nombre_completo,
        id_repartidor=denuncia.id_repartidor,
        nombre_repartidor=nombre_repartidor,
        motivo=denuncia.motivo,
        descripcion=denuncia.descripcion,
        estado=denuncia.estado,
        fecha_creacion=denuncia.fecha_creacion,
        resolucion_admin=denuncia.resolucion_admin,
    )


@router.get("/denuncias/todas", response_model=list[DenunciaOut])
def listar_denuncias(
    estado: Optional[str] = Query(None, description="Filtrar por 'PENDIENTE', 'INVESTIGANDO', 'RESUELTO', 'DESESTIMADA'"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    usuario: m.Usuario = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    """(Solo ADMIN) Consulta todas las denuncias realizadas contra repartidores."""
    query = select(m.DenunciaRepartidor)
    if estado:
        query = query.where(m.DenunciaRepartidor.estado == estado.upper())
    denuncias = db.scalars(
        query.order_by(m.DenunciaRepartidor.fecha_creacion.desc()).offset(offset).limit(limit)
    ).all()

    resultado = []
    for d in denuncias:
        resultado.append(
            DenunciaOut(
                id_denuncia=d.id_denuncia,
                id_pedido=d.id_pedido,
                id_cliente=d.id_cliente,
                nombre_cliente=d.cliente.nombre_completo if d.cliente else "Desconocido",
                id_repartidor=d.id_repartidor,
                nombre_repartidor=d.repartidor.nombre_completo if d.repartidor else "Desconocido",
                motivo=d.motivo,
                descripcion=d.descripcion,
                estado=d.estado,
                fecha_creacion=d.fecha_creacion,
                resolucion_admin=d.resolucion_admin,
            )
        )
    return resultado


@router.patch("/denuncias/{id_denuncia}", response_model=DenunciaOut)
def resolver_denuncia(
    id_denuncia: int,
    data: ResolverDenunciaIn,
    usuario: m.Usuario = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    """(Solo ADMIN) Actualiza el estado de una denuncia y añade notas de resolución."""
    denuncia = db.get(m.DenunciaRepartidor, id_denuncia)
    if denuncia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Denuncia no encontrada")

    denuncia.estado = data.estado
    if data.resolucion_admin is not None:
        denuncia.resolucion_admin = data.resolucion_admin
    db.commit()
    db.refresh(denuncia)

    return DenunciaOut(
        id_denuncia=denuncia.id_denuncia,
        id_pedido=denuncia.id_pedido,
        id_cliente=denuncia.id_cliente,
        nombre_cliente=denuncia.cliente.nombre_completo if denuncia.cliente else "Desconocido",
        id_repartidor=denuncia.id_repartidor,
        nombre_repartidor=denuncia.repartidor.nombre_completo if denuncia.repartidor else "Desconocido",
        motivo=denuncia.motivo,
        descripcion=denuncia.descripcion,
        estado=denuncia.estado,
        fecha_creacion=denuncia.fecha_creacion,
        resolucion_admin=denuncia.resolucion_admin,
    )
