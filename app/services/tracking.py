import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class TrackingConnectionManager:
    """
    Gestor de conexiones WebSocket en memoria para seguimiento en vivo.
    Permite emitir las coordenadas del repartidor en tiempo real (sub-segundo)
    hacia clientes y empleados que estén viendo el mapa de un pedido sin sobrecargar la BD.
    """

    def __init__(self):
        # id_pedido -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, id_pedido: int, websocket: WebSocket):
        await websocket.accept()
        if id_pedido not in self.active_connections:
            self.active_connections[id_pedido] = []
        self.active_connections[id_pedido].append(websocket)
        logger.info(f"[WS TRACKING] Cliente conectado a seguimiento de pedido #{id_pedido}")

    def disconnect(self, id_pedido: int, websocket: WebSocket):
        if id_pedido in self.active_connections:
            if websocket in self.active_connections[id_pedido]:
                self.active_connections[id_pedido].remove(websocket)
            if not self.active_connections[id_pedido]:
                del self.active_connections[id_pedido]
        logger.info(f"[WS TRACKING] Cliente desconectado de pedido #{id_pedido}")

    async def broadcast_ubicacion(self, id_pedido: int, data: dict):
        if id_pedido in self.active_connections:
            mensaje = json.dumps(data)
            cerrados = []
            for ws in self.active_connections[id_pedido]:
                try:
                    await ws.send_text(mensaje)
                except Exception:
                    cerrados.append(ws)
            for ws in cerrados:
                self.disconnect(id_pedido, ws)


tracking_manager = TrackingConnectionManager()
