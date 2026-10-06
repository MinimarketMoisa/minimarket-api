from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer

# En el JSON los montos y coordenadas salen como numero (no como texto)
Num = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

TipoEntrega = Literal["DOMICILIO", "RETIRO"]
MetodoPago = Literal["CONTRA_ENTREGA", "TRANSFERENCIA"]
Canal = Literal["APP", "WEB"]
EstadoPedido = Literal["PENDIENTE", "PREPARADO", "EN_RUTA", "ENTREGADO", "CANCELADO"]
EstadoPago = Literal["PENDIENTE", "PAGADO"]
EstadoRepartidor = Literal["LIBRE", "PENDIENTE"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Autenticacion ----
class RegistroIn(BaseModel):
    nombre_completo: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    telefono: Optional[str] = Field(default=None, max_length=20)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id_usuario: int
    rol: str


class UsuarioOut(BaseModel):
    id_usuario: int
    nombre_completo: str
    email: str
    telefono: Optional[str] = None
    rol: str


# ---- Catalogo ----
class MunicipioOut(ORM):
    id_municipio: int
    nombre: str


class SucursalOut(ORM):
    id_sucursal: int
    id_municipio: int
    nombre: str
    direccion: str
    telefono: Optional[str] = None
    latitud: Num
    longitud: Num


class CategoriaOut(ORM):
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None


class ProductoOut(ORM):
    id_producto: int
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: Num
    imagen_url: Optional[str] = None
    activo: bool


class ProductoIn(BaseModel):
    id_categoria: int
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    codigo_barras: Optional[str] = Field(default=None, max_length=50)
    precio_base: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    imagen_url: Optional[str] = Field(default=None, max_length=500)


class DisponibilidadOut(BaseModel):
    id_sucursal: int
    nombre_sucursal: str
    stock_disponible: int


# ---- Direcciones ----
class DireccionIn(BaseModel):
    id_municipio: int
    detalle_direccion: str = Field(min_length=3, max_length=300)
    punto_referencia: Optional[str] = Field(default=None, max_length=300)


class DireccionOut(ORM):
    id_direccion: int
    id_municipio: int
    detalle_direccion: str
    punto_referencia: Optional[str] = None


# ---- Pedidos ----
class PedidoItemIn(BaseModel):
    id_producto: int
    cantidad: int = Field(gt=0, le=1000)


class PedidoIn(BaseModel):
    items: list[PedidoItemIn] = Field(min_length=1)
    tipo_entrega: TipoEntrega
    metodo_pago: MetodoPago
    canal: Canal
    id_direccion: Optional[int] = None   # obligatorio si es DOMICILIO
    id_sucursal: Optional[int] = None    # obligatorio si es RETIRO


class DetalleOut(BaseModel):
    id_producto: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Num
    subtotal: Num


class PedidoOut(BaseModel):
    id_pedido: int
    id_cliente: int
    id_sucursal: int
    id_repartidor: Optional[int] = None
    id_direccion: Optional[int] = None
    canal: str
    tipo_entrega: str
    metodo_pago: str
    estado: str
    estado_pago: str
    costo_envio: Num
    total: Num
    fecha_creacion: Optional[datetime] = None
    detalles: list[DetalleOut]


class EstadoIn(BaseModel):
    estado: EstadoPedido


class PagoIn(BaseModel):
    estado_pago: EstadoPago


# ---- Repartidor ----
class UbicacionIn(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class RepartidorEstadoIn(BaseModel):
    estado: EstadoRepartidor


# ---- Inventario ----
class InventarioIn(BaseModel):
    id_sucursal: int
    id_producto: int
    stock_disponible: int = Field(ge=0)
    fecha_vencimiento: Optional[date] = None


class InventarioOut(BaseModel):
    id_sucursal: int
    id_producto: int
    nombre_producto: str
    stock_disponible: int
    fecha_vencimiento: Optional[date] = None
