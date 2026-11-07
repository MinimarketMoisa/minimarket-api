import re
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models as m
from .. import services
from ..database import get_db
from ..deps import get_current_user
from ..schemas import PagoWompiIn, PagoWompiOut, TarjetaPruebaOut
from ..services.email import enviar_factura_pedido
from ..services.tracking import tracking_manager

router = APIRouter(prefix="/pagos", tags=["Pagos (Wompi Sandbox)"])

TARJETAS_PRUEBA_WOMPI = [
    TarjetaPruebaOut(
        tipo="APROBADA",
        numero="4242 4242 4242 4242",
        nombre_titular="JUAN PEREZ",
        mes="12",
        anio="2028",
        cvv="123",
        resultado="APROBADA",
        descripcion="Simula un pago exitoso con tarjeta Visa y fondos suficientes.",
    ),
    TarjetaPruebaOut(
        tipo="FONDOS_INSUFICIENTES",
        numero="4000 0000 0000 0002",
        nombre_titular="CARLOS GOMEZ",
        mes="12",
        anio="2028",
        cvv="123",
        resultado="DECLINADA (FONDOS_INSUFICIENTES)",
        descripcion="Simula saldo insuficiente en la cuenta bancaria del cliente.",
    ),
    TarjetaPruebaOut(
        tipo="DECLINADA_POR_BANCO",
        numero="4000 0000 0000 0003",
        nombre_titular="MARIA LOPEZ",
        mes="12",
        anio="2028",
        cvv="123",
        resultado="DECLINADA (RECHAZO_BANCARIO)",
        descripcion="Simula sospecha de fraude o tarjeta bloqueada por el banco emisor.",
    ),
    TarjetaPruebaOut(
        tipo="TARJETA_EXPIRADA",
        numero="4000 0000 0000 0004",
        nombre_titular="ANA HERNANDEZ",
        mes="01",
        anio="2022",
        cvv="123",
        resultado="DECLINADA (TARJETA_EXPIRADA)",
        descripcion="Simula una tarjeta cuya fecha de expiración ya caducó.",
    ),
]


def _detectar_marca(numero_limpio: str) -> str:
    if numero_limpio.startswith("4"):
        return "VISA"
    if numero_limpio.startswith(("51", "52", "53", "54", "55")) or (
        len(numero_limpio) >= 4 and 2221 <= int(numero_limpio[:4]) <= 2720
    ):
        return "MASTERCARD"
    if numero_limpio.startswith(("34", "37")):
        return "AMERICAN_EXPRESS"
    if numero_limpio.startswith(("6011", "65")):
        return "DISCOVER"
    return "TARJETA_CREDITO"


@router.get("/wompi/tarjetas-prueba", response_model=List[TarjetaPruebaOut])
def listar_tarjetas_prueba():
    """
    (Web y Móvil) Lista el catálogo de tarjetas de prueba del simulador de Wompi Sandbox.
    Ideal para mostrar botones de prueba rápida en la interfaz de usuario.
    """
    return TARJETAS_PRUEBA_WOMPI


@router.post("/wompi/simular", response_model=PagoWompiOut)
async def simular_pago_wompi(
    data: PagoWompiIn,
    background_tasks: BackgroundTasks,
    usuario: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    (Simulador Wompi Sandbox) Procesa el cobro simulado con tarjeta para un pedido.
    Si la tarjeta es aprobada:
    1. Marca el estado_pago del pedido como 'PAGADO'.
    2. Registra el método como 'TARJETA' con el ID de transacción de Wompi.
    3. Envía automáticamente la factura fiscal por correo electrónico.
    4. Notifica en vivo a través del WebSocket a la App Móvil y Web.
    """
    pedido = db.get(m.Pedido, data.id_pedido)
    if pedido is None or not services.puede_ver_pedido(db, usuario, pedido):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    if pedido.estado == "CANCELADO":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede procesar el pago de un pedido cancelado.",
        )

    if pedido.estado_pago == "PAGADO":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El pedido #{pedido.id_pedido} ya se encuentra pagado previamente.",
        )

    # 1. Normalización y sanitización de datos de tarjeta
    numero_limpio = re.sub(r"\D", "", data.numero_tarjeta)
    cvv_limpio = re.sub(r"\D", "", data.cvv)
    ahora = datetime.now(timezone.utc)
    marca = _detectar_marca(numero_limpio)
    ultimos_cuatro = numero_limpio[-4:] if len(numero_limpio) >= 4 else "0000"
    id_transaccion = f"WOMPI-SIM-{secrets.token_hex(6).upper()}"
    referencia_wompi = f"REF-{secrets.token_hex(4).upper()}"

    # Validaciones de formato
    if len(numero_limpio) < 13 or len(numero_limpio) > 19:
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="ERROR_DATOS",
            codigo_respuesta="DATOS_INVALIDOS",
            mensaje="Número de tarjeta inválido (debe contener entre 13 y 19 dígitos).",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=marca,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    if len(cvv_limpio) not in (3, 4):
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="ERROR_DATOS",
            codigo_respuesta="DATOS_INVALIDOS",
            mensaje="Código de seguridad CVV inválido (debe tener 3 o 4 dígitos).",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=marca,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    try:
        mes = int(data.mes_expiracion)
        anio_raw = int(data.anio_expiracion)
        anio = anio_raw if anio_raw >= 2000 else 2000 + anio_raw
        if mes < 1 or mes > 12:
            raise ValueError
    except (ValueError, TypeError):
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="ERROR_DATOS",
            codigo_respuesta="DATOS_INVALIDOS",
            mensaje="Mes o año de expiración con formato inválido.",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=marca,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    # 2. Reglas de simulación de Wompi Sandbox
    # Caso A: Tarjeta expirada (fecha pasada o terminación 0004)
    if (anio < ahora.year or (anio == ahora.year and mes < ahora.month)) or numero_limpio.endswith("0004"):
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="DECLINADA",
            codigo_respuesta="TARJETA_EXPIRADA",
            mensaje="Transacción declinada: La tarjeta ingresada se encuentra vencida.",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=marca,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    # Caso B: Fondos insuficientes (terminación 0002)
    if numero_limpio.endswith("0002"):
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="DECLINADA",
            codigo_respuesta="FONDOS_INSUFICIENTES",
            mensaje="Transacción declinada: La cuenta asociada no cuenta con fondos suficientes.",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=marca,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    # Caso C: Declinada por banco / sospecha de fraude (terminación 0003)
    if numero_limpio.endswith("0003"):
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="DECLINADA",
            codigo_respuesta="DECLINADA_POR_BANCO",
            mensaje="Transacción declinada por la entidad financiera emisora (sospecha de bloqueo preventivo).",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=marca,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    # 3. Transacción APROBADA con éxito
    pedido.metodo_pago = "TARJETA"
    pedido.estado_pago = "PAGADO"
    pedido.referencia_pago = id_transaccion
    db.commit()
    db.refresh(pedido)

    # Enviar factura por correo en segundo plano
    email_destino = (data.email_pagador or "").strip() or usuario.email
    background_tasks.add_task(
        enviar_factura_pedido,
        email_destino,
        usuario.nombre_completo,
        services.datos_factura(pedido),
    )

    # Emitir evento en tiempo real por WebSocket
    await tracking_manager.broadcast_ubicacion(
        pedido.id_pedido,
        {
            "evento": "pago_confirmado",
            "id_pedido": pedido.id_pedido,
            "codigo_pedido": pedido.codigo_pedido,
            "estado_pago": "PAGADO",
            "metodo_pago": "TARJETA",
            "id_transaccion": id_transaccion,
            "monto": float(pedido.total),
        },
    )

    return PagoWompiOut(
        id_transaccion=id_transaccion,
        id_pedido=pedido.id_pedido,
        codigo_pedido=pedido.codigo_pedido,
        estado_transaccion="APROBADA",
        codigo_respuesta="APROBADA",
        mensaje="¡Pago aprobado con éxito! Tu transacción ha sido procesada por Wompi Sandbox.",
        monto=pedido.total,
        moneda="USD",
        marca_tarjeta=marca,
        ultimos_cuatro=ultimos_cuatro,
        nombre_titular=data.nombre_titular.strip().upper(),
        fecha_transaccion=ahora,
        referencia_wompi=referencia_wompi,
        recibo_enviado_email=True,
    )
