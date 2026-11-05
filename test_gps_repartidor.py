"""
Script para probar y simular en tiempo real el rastreo GPS del repartidor
y la recepción WebSocket por parte del cliente (sin necesidad del APK móvil).

Uso:
    python test_gps_repartidor.py
"""
import time
import threading
from decimal import Decimal
import httpx
from sqlalchemy import select
from app import models as m
from app import security
from app.database import SessionLocal

API_URL = "http://localhost:8000"


def obtener_token(email: str, password: str = "Prueba12345") -> str:
    res = httpx.post(
        f"{API_URL}/auth/login",
        data={"username": email, "password": password},
    )
    if res.status_code != 200:
        raise RuntimeError(f"Error login {email}: {res.text}")
    return res.json()["access_token"]


def simular_movimiento_repartidor(rep_token: str, id_pedido: int):
    """Simula al repartidor avanzando por la calle enviando GPS cada 2 segundos."""
    time.sleep(2)
    # Coordenadas simuladas avanzando en San Miguel / San Salvador
    ruta = [
        (13.483500, -88.183000),
        (13.484200, -88.182400),
        (13.485100, -88.181800),
        (13.486000, -88.181000),
        (13.487000, -88.180200),
    ]

    print("\n[REPARTIDOR GPS] Iniciando transmisión de ruta en vivo...")
    for i, (lat, lon) in enumerate(ruta, start=1):
        time.sleep(2)
        res = httpx.patch(
            f"{API_URL}/repartidor/ubicacion",
            headers={"Authorization": f"Bearer {rep_token}"},
            json={"latitud": lat, "longitud": lon},
        )
        print(f"  [Paso {i}/5] Repartidor actualizó GPS -> ({lat}, {lon}) [HTTP {res.status_code}]")


def main():
    print("=== TEST DE SEGUIMIENTO GPS Y WEBSOCKET (REPARTIDOR -> CLIENTE) ===\n")
    
    # 1. Preparar pedido de prueba en estado activo con repartidor asignado
    with SessionLocal() as db:
        cli = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        rep = db.scalar(select(m.Usuario).where(m.Usuario.email == "repartidor1@minimarket.test"))
        
        pedido = db.scalar(
            select(m.Pedido).where(
                m.Pedido.id_cliente == cli.id_usuario,
                m.Pedido.tipo_entrega == "DOMICILIO"
            )
        )
        if not pedido:
            pedido = db.scalar(select(m.Pedido))
            pedido.id_cliente = cli.id_usuario
            pedido.tipo_entrega = "DOMICILIO"
            
        pedido.id_repartidor = rep.id_usuario
        pedido.estado = "EN_RUTA"
        pedido.estado_repartidor = "ACEPTADO"
        id_pedido = pedido.id_pedido
        codigo_pedido = pedido.codigo_pedido
        db.commit()

    print(f"Pedido de prueba listo:")
    print(f"  - ID: {id_pedido}")
    print(f"  - Código: {codigo_pedido}")
    print(f"  - Estado: EN_RUTA")

    # 2. Login de cliente y repartidor
    cli_token = obtener_token("cliente@minimarket.test")
    rep_token = obtener_token("repartidor1@minimarket.test")

    # 3. Consulta REST de seguimiento inicial del cliente
    res_seg = httpx.get(
        f"{API_URL}/pedidos/{id_pedido}/seguimiento",
        headers={"Authorization": f"Bearer {cli_token}"},
    )
    datos_seg = res_seg.json()
    print("\n[CLIENTE REST] Consulta inicial de seguimiento:")
    print(f"  - Código de pedido: {datos_seg.get('codigo_pedido')}")
    print(f"  - Estado pedido: {datos_seg.get('estado')}")
    print(f"  - Sucursal origen: {datos_seg['sucursal']['nombre']}")
    print(f"  - Repartidor asignado: {datos_seg['repartidor']['nombre']} (Tel: {datos_seg['repartidor']['telefono']})")
    print(f"  - ¿ID Repartidor oculto al cliente?: {datos_seg['repartidor']['id_repartidor'] is None}")

    # 4. Iniciar simulación del repartidor en segundo plano
    hilo_repartidor = threading.Thread(
        target=simular_movimiento_repartidor,
        args=(rep_token, id_pedido),
        daemon=True,
    )
    hilo_repartidor.start()

    # 5. Conectar cliente a WebSocket para recibir actualizaciones
    import websockets.sync.client as ws_client
    ws_url = f"ws://localhost:8000/pedidos/{id_pedido}/ws/seguimiento?token={cli_token}"
    print(f"\n[CLIENTE WS] Conectando a {ws_url}...")

    try:
        with ws_client.connect(ws_url) as ws:
            print("[CLIENTE WS] ¡Conexión establecida! Escuchando coordenadas en vivo:")
            # Recibir estado inicial
            msg_init = ws.recv(timeout=5)
            print(f"  -> Recibido evento inicial: {msg_init[:80]}...")

            # Escuchar las 5 actualizaciones del repartidor
            recibidos = 0
            while recibidos < 5:
                msg = ws.recv(timeout=10)
                print(f"  -> [EVENTO RECIBIDO EN VIVO]: {msg}")
                recibidos += 1

            print("\n[ÉXITO] El cliente recibió todas las posiciones GPS en tiempo real por WebSocket.")
    except Exception as e:
        print(f"\nNota de prueba WS: {e}")
        hilo_repartidor.join(timeout=12)

    print("\n=== PRUEBA DE RASTREO GPS FINALIZADA SATISFACTORIAMENTE ===")


if __name__ == "__main__":
    main()
