import calendar
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..deps import require_roles
from ..schemas import (
    RendimientoRepartidorOut,
    ReporteDiarioOut,
    ReporteMensualOut,
    ResumenSucursalOut,
    TopProductoOut,
    VentaPorDiaOut,
)

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes y Estadísticas (Empresa)"],
    dependencies=[Depends(require_roles("ADMIN", "EMPLEADO"))],
)


@router.get("/pedidos/{id_pedido}", response_model=dict)
def reporte_pedido_empresa(
    id_pedido: int,
    db: Session = Depends(get_db),
):
    """
    (Empresa / Admin / Empleado) Genera el reporte de auditoría operacional y financiero
    de un pedido específico: datos del cliente, tiempos, repartidor, sucursal, productos y totales.
    """
    pedido = db.get(m.Pedido, id_pedido)
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    cliente = db.get(m.Usuario, pedido.id_cliente)
    sucursal = db.get(m.Sucursal, pedido.id_sucursal)

    nombre_repartidor = None
    telefono_repartidor = None
    if pedido.id_repartidor:
        rep = db.get(m.Usuario, pedido.id_repartidor)
        if rep:
            nombre_repartidor = rep.nombre_completo
            telefono_repartidor = rep.telefono

    detalles_reporte = []
    subtotal_prod = Decimal("0.00")
    for d in pedido.detalles:
        sub = d.cantidad * d.precio_unitario
        subtotal_prod += sub
        detalles_reporte.append(
            {
                "id_producto": d.id_producto,
                "nombre_producto": d.producto.nombre if d.producto else f"Producto #{d.id_producto}",
                "categoria": d.producto.categoria.nombre if d.producto and d.producto.categoria else "Sin categoría",
                "codigo_barras": d.producto.codigo_barras if d.producto else None,
                "cantidad": d.cantidad,
                "precio_unitario": float(d.precio_unitario),
                "subtotal": float(sub),
            }
        )

    return {
        "id_pedido": pedido.id_pedido,
        "fecha_creacion": pedido.fecha_creacion,
        "estado": pedido.estado,
        "canal": pedido.canal,
        "tipo_entrega": pedido.tipo_entrega,
        "metodo_pago": pedido.metodo_pago,
        "estado_pago": pedido.estado_pago,
        "costo_envio": float(pedido.costo_envio or 0),
        "subtotal_productos": float(subtotal_prod),
        "total_general": float(pedido.total),
        "cliente": {
            "id_cliente": cliente.id_usuario if cliente else pedido.id_cliente,
            "nombre": cliente.nombre_completo if cliente else "Desconocido",
            "email": cliente.email if cliente else "",
            "telefono": cliente.telefono if cliente else None,
        },
        "sucursal": {
            "id_sucursal": sucursal.id_sucursal if sucursal else pedido.id_sucursal,
            "nombre": sucursal.nombre if sucursal else "Sucursal",
            "direccion": sucursal.direccion if sucursal else "",
        },
        "repartidor": {
            "id_repartidor": pedido.id_repartidor,
            "nombre": nombre_repartidor,
            "telefono": telefono_repartidor,
            "estado_entrega": pedido.estado_repartidor,
        } if pedido.id_repartidor else None,
        "detalles_productos": detalles_reporte,
    }


@router.get("/diario", response_model=ReporteDiarioOut)
def reporte_diario(
    fecha: Optional[date] = Query(None, description="Fecha a consultar (YYYY-MM-DD). Por defecto: hoy"),
    id_sucursal: Optional[int] = Query(None, description="Filtrar por ID de sucursal"),
    usuario: m.Usuario = Depends(require_roles("ADMIN", "EMPLEADO")),
    db: Session = Depends(get_db),
):
    """
    (Empresa / Admin) Genera el reporte diario consolidado de ventas, pedidos por estado,
    ingresos por método de pago y productos más vendidos.
    """
    dia_consulta = fecha or datetime.now(timezone.utc).date()
    inicio_dia = datetime.combine(dia_consulta, time.min).replace(tzinfo=timezone.utc)
    fin_dia = datetime.combine(dia_consulta, time.max).replace(tzinfo=timezone.utc)

    # Si es empleado, filtrar automáticamente por su sucursal
    if usuario.rol.nombre == "EMPLEADO":
        emp = db.get(m.Empleado, usuario.id_usuario)
        if emp:
            id_sucursal = emp.id_sucursal

    query_pedidos = select(m.Pedido).where(
        m.Pedido.fecha_creacion >= inicio_dia,
        m.Pedido.fecha_creacion <= fin_dia,
    )
    if id_sucursal:
        query_pedidos = query_pedidos.where(m.Pedido.id_sucursal == id_sucursal)

    pedidos = db.scalars(query_pedidos).all()

    total_pedidos = len(pedidos)
    pedidos_entregados = sum(1 for p in pedidos if p.estado == "ENTREGADO")
    pedidos_cancelados = sum(1 for p in pedidos if p.estado == "CANCELADO")
    pedidos_en_proceso = sum(1 for p in pedidos if p.estado in ("PENDIENTE", "PREPARADO", "EN_RUTA"))

    # Ingresos (solo de pedidos que no fueron cancelados)
    pedidos_validos = [p for p in pedidos if p.estado != "CANCELADO"]
    ingresos_totales = sum((p.total for p in pedidos_validos), Decimal("0.00"))
    ingresos_envio = sum((p.costo_envio for p in pedidos_validos), Decimal("0.00"))
    ingresos_productos = ingresos_totales - ingresos_envio

    # Por método de pago
    metodos: dict[str, Decimal] = {"CONTRA_ENTREGA": Decimal("0.00"), "TRANSFERENCIA": Decimal("0.00")}
    for p in pedidos_validos:
        metodos[p.metodo_pago] = metodos.get(p.metodo_pago, Decimal("0.00")) + p.total

    # Por sucursal
    ventas_suc: dict[int, dict] = {}
    for p in pedidos_validos:
        if p.id_sucursal not in ventas_suc:
            suc = db.get(m.Sucursal, p.id_sucursal)
            nom = suc.nombre if suc else f"Sucursal #{p.id_sucursal}"
            ventas_suc[p.id_sucursal] = {"id_sucursal": p.id_sucursal, "nombre_sucursal": nom, "total_pedidos": 0, "total_ventas": Decimal("0.00")}
        ventas_suc[p.id_sucursal]["total_pedidos"] += 1
        ventas_suc[p.id_sucursal]["total_ventas"] += p.total

    resumen_sucursales = [ResumenSucursalOut(**v) for v in ventas_suc.values()]

    # Top productos vendidos del día
    prod_ventas: dict[int, dict] = {}
    for p in pedidos_validos:
        for d in p.detalles:
            if d.id_producto not in prod_ventas:
                prod = db.get(m.Producto, d.id_producto)
                nom = prod.nombre if prod else f"Producto #{d.id_producto}"
                prod_ventas[d.id_producto] = {"id_producto": d.id_producto, "nombre_producto": nom, "unidades_vendidas": 0, "ingresos": Decimal("0.00")}
            prod_ventas[d.id_producto]["unidades_vendidas"] += d.cantidad
            prod_ventas[d.id_producto]["ingresos"] += d.cantidad * d.precio_unitario

    top_productos = sorted(
        [TopProductoOut(**v) for v in prod_ventas.values()],
        key=lambda x: x.unidades_vendidas,
        reverse=True,
    )[:10]

    return ReporteDiarioOut(
        fecha=dia_consulta,
        total_pedidos=total_pedidos,
        pedidos_entregados=pedidos_entregados,
        pedidos_cancelados=pedidos_cancelados,
        pedidos_en_proceso=pedidos_en_proceso,
        ingresos_totales=ingresos_totales,
        ingresos_productos=ingresos_productos,
        ingresos_envio=ingresos_envio,
        por_metodo_pago=metodos,
        por_sucursal=resumen_sucursales,
        top_productos=top_productos,
    )


@router.get("/mensual", response_model=ReporteMensualOut)
def reporte_mensual(
    anio: Optional[int] = Query(None, description="Año (ej. 2026). Por defecto: año actual"),
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mes (1-12). Por defecto: mes actual"),
    id_sucursal: Optional[int] = Query(None, description="Filtrar por ID de sucursal"),
    usuario: m.Usuario = Depends(require_roles("ADMIN", "EMPLEADO")),
    db: Session = Depends(get_db),
):
    """
    (Empresa / Admin) Genera el reporte mensual con desglose de ventas por día,
    rendimiento de repartidores y ranking de productos estrella.
    """
    ahora = datetime.now(timezone.utc)
    anio_sel = anio or ahora.year
    mes_sel = mes or ahora.month

    if usuario.rol.nombre == "EMPLEADO":
        emp = db.get(m.Empleado, usuario.id_usuario)
        if emp:
            id_sucursal = emp.id_sucursal

    query_pedidos = select(m.Pedido).where(
        extract("year", m.Pedido.fecha_creacion) == anio_sel,
        extract("month", m.Pedido.fecha_creacion) == mes_sel,
    )
    if id_sucursal:
        query_pedidos = query_pedidos.where(m.Pedido.id_sucursal == id_sucursal)

    pedidos = db.scalars(query_pedidos).all()

    total_pedidos = len(pedidos)
    pedidos_entregados = sum(1 for p in pedidos if p.estado == "ENTREGADO")
    pedidos_cancelados = sum(1 for p in pedidos if p.estado == "CANCELADO")

    # Tasa de efectividad de entrega
    completados = pedidos_entregados + pedidos_cancelados
    tasa_efectividad = round((pedidos_entregados / completados * 100), 2) if completados > 0 else 100.0

    pedidos_validos = [p for p in pedidos if p.estado != "CANCELADO"]
    ingresos_totales = sum((p.total for p in pedidos_validos), Decimal("0.00"))
    ingresos_envio = sum((p.costo_envio for p in pedidos_validos), Decimal("0.00"))
    ingresos_productos = ingresos_totales - ingresos_envio

    # Ventas por día del mes
    dias_en_mes = calendar.monthrange(anio_sel, mes_sel)[1]
    dias_dict: dict[int, dict] = {d: {"dia": d, "total_pedidos": 0, "total_ventas": Decimal("0.00")} for d in range(1, dias_en_mes + 1)}

    for p in pedidos_validos:
        dia_num = p.fecha_creacion.day if p.fecha_creacion else 1
        if dia_num in dias_dict:
            dias_dict[dia_num]["total_pedidos"] += 1
            dias_dict[dia_num]["total_ventas"] += p.total

    ventas_por_dia = [VentaPorDiaOut(**v) for v in dias_dict.values()]

    # Ventas por sucursal
    ventas_suc: dict[int, dict] = {}
    for p in pedidos_validos:
        if p.id_sucursal not in ventas_suc:
            suc = db.get(m.Sucursal, p.id_sucursal)
            nom = suc.nombre if suc else f"Sucursal #{p.id_sucursal}"
            ventas_suc[p.id_sucursal] = {"id_sucursal": p.id_sucursal, "nombre_sucursal": nom, "total_pedidos": 0, "total_ventas": Decimal("0.00")}
        ventas_suc[p.id_sucursal]["total_pedidos"] += 1
        ventas_suc[p.id_sucursal]["total_ventas"] += p.total

    ventas_por_sucursal = [ResumenSucursalOut(**v) for v in ventas_suc.values()]

    # Rendimiento de repartidores (solo entregas completadas)
    rep_entregas: dict[int, dict] = {}
    for p in pedidos:
        if p.estado == "ENTREGADO" and p.id_repartidor:
            if p.id_repartidor not in rep_entregas:
                u_rep = db.get(m.Usuario, p.id_repartidor)
                nom_rep = u_rep.nombre_completo if u_rep else f"Repartidor #{p.id_repartidor}"
                rep_entregas[p.id_repartidor] = {"id_repartidor": p.id_repartidor, "nombre_repartidor": nom_rep, "entregas_completadas": 0}
            rep_entregas[p.id_repartidor]["entregas_completadas"] += 1

    rendimiento_repartidores = sorted(
        [RendimientoRepartidorOut(**v) for v in rep_entregas.values()],
        key=lambda x: x.entregas_completadas,
        reverse=True,
    )

    # Top productos del mes
    prod_ventas: dict[int, dict] = {}
    for p in pedidos_validos:
        for d in p.detalles:
            if d.id_producto not in prod_ventas:
                prod = db.get(m.Producto, d.id_producto)
                nom = prod.nombre if prod else f"Producto #{d.id_producto}"
                prod_ventas[d.id_producto] = {"id_producto": d.id_producto, "nombre_producto": nom, "unidades_vendidas": 0, "ingresos": Decimal("0.00")}
            prod_ventas[d.id_producto]["unidades_vendidas"] += d.cantidad
            prod_ventas[d.id_producto]["ingresos"] += d.cantidad * d.precio_unitario

    top_productos_mes = sorted(
        [TopProductoOut(**v) for v in prod_ventas.values()],
        key=lambda x: x.unidades_vendidas,
        reverse=True,
    )[:10]

    return ReporteMensualOut(
        anio=anio_sel,
        mes=mes_sel,
        total_pedidos=total_pedidos,
        ingresos_totales=ingresos_totales,
        ingresos_productos=ingresos_productos,
        ingresos_envio=ingresos_envio,
        tasa_efectividad_porcentaje=tasa_efectividad,
        ventas_por_dia=ventas_por_dia,
        ventas_por_sucursal=ventas_por_sucursal,
        rendimiento_repartidores=rendimiento_repartidores,
        top_productos_mes=top_productos_mes,
    )
