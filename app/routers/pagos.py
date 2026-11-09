import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
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

# -----------------------------------------------------------------------------
# Catálogo oficial estricto: 10 Tarjetas autorizadas para simulación realista
# - 8 de VISA (Compañía 1)
# - 2 de MASTERCARD (Compañía 2)
# - Tipos: Crédito y Débito
# - 10 Saldos diferentes
# - 1 tarjeta bloqueada por banco/fraude
# - 1 tarjeta con saldo insuficiente garantizado ($2.50)
# -----------------------------------------------------------------------------
CATALOGO_TARJETAS_DICT = {
    "4242424242424242": {
        "tipo": "APROBADA",
        "numero": "4242 4242 4242 4242",
        "nombre_titular": "JUAN PEREZ",
        "mes": "12",
        "anio": "2028",
        "cvv": "123",
        "resultado": "APROBADA",
        "descripcion": "Visa Platino con amplio cupo y fondos suficientes.",
        "franquicia": "VISA",
        "tipo_tarjeta": "CREDITO",
        "saldo_disponible": Decimal("1500.00"),
        "bloqueada": False,
    },
    "4012000000000016": {
        "tipo": "APROBADA",
        "numero": "4012 0000 0000 0016",
        "nombre_titular": "MARIA RODRIGUEZ",
        "mes": "10",
        "anio": "2027",
        "cvv": "456",
        "resultado": "APROBADA",
        "descripcion": "Cuenta de ahorros Visa Débito con fondos óptimos.",
        "franquicia": "VISA",
        "tipo_tarjeta": "DEBITO",
        "saldo_disponible": Decimal("800.00"),
        "bloqueada": False,
    },
    "4111111111111111": {
        "tipo": "APROBADA",
        "numero": "4111 1111 1111 1111",
        "nombre_titular": "CARLOS SANCHEZ",
        "mes": "08",
        "anio": "2029",
        "cvv": "789",
        "resultado": "APROBADA",
        "descripcion": "Visa Clásica estándar para compras medianas.",
        "franquicia": "VISA",
        "tipo_tarjeta": "CREDITO",
        "saldo_disponible": Decimal("500.00"),
        "bloqueada": False,
    },
    "4532111122223336": {
        "tipo": "APROBADA",
        "numero": "4532 1111 2222 3336",
        "nombre_titular": "LAURA GOMEZ",
        "mes": "05",
        "anio": "2028",
        "cvv": "321",
        "resultado": "APROBADA",
        "descripcion": "Tarjeta nómina Visa Débito con balance regular.",
        "franquicia": "VISA",
        "tipo_tarjeta": "DEBITO",
        "saldo_disponible": Decimal("300.00"),
        "bloqueada": False,
    },
    "4916333344445556": {
        "tipo": "APROBADA",
        "numero": "4916 3333 4444 5556",
        "nombre_titular": "ANDRES MARTINEZ",
        "mes": "11",
        "anio": "2027",
        "cvv": "654",
        "resultado": "APROBADA",
        "descripcion": "Visa Oro con saldo disponible moderado.",
        "franquicia": "VISA",
        "tipo_tarjeta": "CREDITO",
        "saldo_disponible": Decimal("150.00"),
        "bloqueada": False,
    },
    "4012888888881881": {
        "tipo": "APROBADA",
        "numero": "4012 8888 8888 1881",
        "nombre_titular": "SOFIA MORALES",
        "mes": "03",
        "anio": "2028",
        "cvv": "987",
        "resultado": "APROBADA",
        "descripcion": "Visa Débito juvenil para compras diarias.",
        "franquicia": "VISA",
        "tipo_tarjeta": "DEBITO",
        "saldo_disponible": Decimal("75.00"),
        "bloqueada": False,
    },
    "4444555566667779": {
        "tipo": "APROBADA",
        "numero": "4444 5555 6666 7779",
        "nombre_titular": "DIEGO CASTILLO",
        "mes": "09",
        "anio": "2027",
        "cvv": "147",
        "resultado": "APROBADA",
        "descripcion": "Visa Débito con saldo limitado ($25.00) para pedidos pequeños.",
        "franquicia": "VISA",
        "tipo_tarjeta": "DEBITO",
        "saldo_disponible": Decimal("25.00"),
        "bloqueada": False,
    },
    "4000000000000002": {
        "tipo": "FONDOS_INSUFICIENTES",
        "numero": "4000 0000 0000 0002",
        "nombre_titular": "KEVIN SALINAS",
        "mes": "12",
        "anio": "2028",
        "cvv": "258",
        "resultado": "DECLINADA (FONDOS_INSUFICIENTES)",
        "descripcion": "Simula saldo insuficiente en la cuenta (solo $2.50 USD disponibles).",
        "franquicia": "VISA",
        "tipo_tarjeta": "DEBITO",
        "saldo_disponible": Decimal("2.50"),
        "bloqueada": False,
    },
    "5105105105105100": {
        "tipo": "APROBADA",
        "numero": "5105 1051 0510 5100",
        "nombre_titular": "GABRIELA RIVAS",
        "mes": "07",
        "anio": "2028",
        "cvv": "369",
        "resultado": "APROBADA",
        "descripcion": "Segunda compañía: Mastercard Black con cupo premium.",
        "franquicia": "MASTERCARD",
        "tipo_tarjeta": "CREDITO",
        "saldo_disponible": Decimal("1200.00"),
        "bloqueada": False,
    },
    "5555555555554444": {
        "tipo": "DECLINADA_POR_BANCO",
        "numero": "5555 5555 5555 4444",
        "nombre_titular": "ROBERTO MEJIA",
        "mes": "12",
        "anio": "2028",
        "cvv": "741",
        "resultado": "DECLINADA (BLOQUEADA)",
        "descripcion": "Mastercard Débito bloqueada por sospecha de fraude o reporte bancario.",
        "franquicia": "MASTERCARD",
        "tipo_tarjeta": "DEBITO",
        "saldo_disponible": Decimal("650.00"),
        "bloqueada": True,
    },
}

TARJETAS_PRUEBA_WOMPI: List[TarjetaPruebaOut] = [
    TarjetaPruebaOut(
        tipo=t["tipo"],
        numero=t["numero"],
        nombre_titular=t["nombre_titular"],
        mes=t["mes"],
        anio=t["anio"],
        cvv=t["cvv"],
        resultado=t["resultado"],
        descripcion=t["descripcion"],
        franquicia=t["franquicia"],
        tipo_tarjeta=t["tipo_tarjeta"],
        saldo_disponible=t["saldo_disponible"],
    )
    for t in CATALOGO_TARJETAS_DICT.values()
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
    (Web y Móvil) Lista el catálogo oficial de las 10 tarjetas de prueba del simulador de Wompi Sandbox.
    Incluye 8 tarjetas Visa y 2 Mastercard, con saldos individuales, créditos, débitos y casos de prueba.
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
    Aplica lista blanca estricta (solo acepta las 10 tarjetas oficiales del catálogo).
    
    Verificaciones automáticas:
    1. Lista blanca estricta de tarjetas autorizadas.
    2. Detección de tarjeta bloqueada por entidad bancaria.
    3. Validación de fecha de expiración.
    4. Validación de saldo disponible en cuenta vs monto del pedido.
    5. Aprobación, actualización del pedido a PAGADO, emisión de factura y notificación WebSocket.
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

    # 2. LISTA BLANCA ESTRICTA: Solo las 10 tarjetas autorizadas son procesadas
    tarjeta_autorizada = CATALOGO_TARJETAS_DICT.get(numero_limpio)
    if not tarjeta_autorizada:
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="DECLINADA",
            codigo_respuesta="TARJETA_NO_AUTORIZADA",
            mensaje=(
                "Tarjeta no autorizada: Solo se permiten las 10 tarjetas oficiales del catálogo de pruebas Wompi Sandbox. "
                "Consulte GET /pagos/wompi/tarjetas-prueba para ver las tarjetas autorizadas."
            ),
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=marca,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    franquicia = tarjeta_autorizada["franquicia"]
    tipo_tarjeta = tarjeta_autorizada["tipo_tarjeta"]
    saldo_disponible = tarjeta_autorizada["saldo_disponible"]

    # 3. REGLA A: Tarjeta expirada (fecha pasada)
    if anio < ahora.year or (anio == ahora.year and mes < ahora.month):
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="DECLINADA",
            codigo_respuesta="TARJETA_EXPIRADA",
            mensaje="Transacción declinada: La tarjeta ingresada se encuentra vencida.",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=franquicia,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    # 4. REGLA B: Tarjeta bloqueada por banco / sospecha de fraude
    if tarjeta_autorizada["bloqueada"]:
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="DECLINADA",
            codigo_respuesta="DECLINADA_POR_BANCO",
            mensaje="Transacción declinada: La tarjeta se encuentra bloqueada por la entidad financiera emisora (sospecha de fraude o reporte bancario).",
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=franquicia,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    # 5. REGLA C: Fondos insuficientes (saldo de la tarjeta < total del pedido)
    if pedido.total > saldo_disponible:
        return PagoWompiOut(
            id_transaccion=id_transaccion,
            id_pedido=pedido.id_pedido,
            codigo_pedido=pedido.codigo_pedido,
            estado_transaccion="DECLINADA",
            codigo_respuesta="FONDOS_INSUFICIENTES",
            mensaje=(
                f"Transacción declinada: Fondos insuficientes en la cuenta. "
                f"Saldo disponible: ${saldo_disponible:.2f} USD, "
                f"Total del pedido: ${pedido.total:.2f} USD."
            ),
            monto=pedido.total,
            moneda="USD",
            marca_tarjeta=franquicia,
            ultimos_cuatro=ultimos_cuatro,
            nombre_titular=data.nombre_titular.strip().upper(),
            fecha_transaccion=ahora,
            referencia_wompi=referencia_wompi,
            recibo_enviado_email=False,
        )

    # 6. Transacción APROBADA con éxito
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

    saldo_restante = saldo_disponible - pedido.total
    return PagoWompiOut(
        id_transaccion=id_transaccion,
        id_pedido=pedido.id_pedido,
        codigo_pedido=pedido.codigo_pedido,
        estado_transaccion="APROBADA",
        codigo_respuesta="APROBADA",
        mensaje=(
            f"¡Pago aprobado con éxito mediante {franquicia} {tipo_tarjeta}! "
            f"Saldo restante en cuenta: ${saldo_restante:.2f} USD."
        ),
        monto=pedido.total,
        moneda="USD",
        marca_tarjeta=franquicia,
        ultimos_cuatro=ultimos_cuatro,
        nombre_titular=data.nombre_titular.strip().upper(),
        fecha_transaccion=ahora,
        referencia_wompi=referencia_wompi,
        recibo_enviado_email=True,
    )
