from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

# --- ESQUEMAS DE ROL ---
class RolBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class RolCreate(RolBase):
    pass

class RolResponse(RolBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE CATEGORÍA ---
class CategoriaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    activa: bool = True

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE PRODUCTO ---
class ProductoBase(BaseModel):
    categoria_id: int
    nombre_producto: str
    descripcion_producto: Optional[str] = None
    precio_venta: Decimal
    stock_actual: int
    imagen: Optional[str] = None
    disponible: bool = True

class ProductoCreate(ProductoBase):
    pass

class ProductoResponse(ProductoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE SUCURSAL ---
class SucursalBase(BaseModel):
    nombre: str
    direccion: str
    telefono: str
    correo_contacto: Optional[str] = None
    activa: bool = True

class SucursalCreate(SucursalBase):
    pass

class SucursalResponse(SucursalBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE USUARIO ---
class UsuarioBase(BaseModel):
    rol_id: int
    nombre_usuario: str
    email: str
    nombre_completo: str
    telefono: Optional[str] = None
    direccion_entrega: Optional[str] = None
    activo: bool = True

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioResponse(UsuarioBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE PEDIDO ---
class DetallePedidoCreate(BaseModel):
    producto_id: int
    cantidad: int

class DetallePedidoResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    model_config = ConfigDict(from_attributes=True)

class PedidoCreate(BaseModel):
    cliente_id: int
    sucursal_id: int
    metodo_pago: str
    tipo_entrega: str
    direccion_destino: str
    detalles: List[DetallePedidoCreate]

class PedidoResponse(BaseModel):
    id: int
    cliente_id: int
    repartidor_id: Optional[int] = None
    sucursal_id: int
    estado: str
    metodo_pago: str
    tipo_entrega: str
    direccion_destino: str
    total_orden: Decimal
    fecha_pedido: datetime
    detalles: List[DetallePedidoResponse]
    model_config = ConfigDict(from_attributes=True)

    # --- ESQUEMAS DE ACTUALIZACIÓN DE USUARIO Y ROL ---
class RolUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

class UsuarioUpdate(BaseModel):
    rol_id: Optional[int] = None
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    direccion_entrega: Optional[str] = None
    activo: Optional[bool] = None

# --- ESQUEMAS DE ACTUALIZACIÓN DE PRODUCTO ---
class ProductoUpdate(BaseModel):
    categoria_id: Optional[int] = None
    nombre_producto: Optional[str] = None
    descripcion_producto: Optional[str] = None
    precio_venta: Optional[Decimal] = None
    stock_actual: Optional[int] = None
    imagen: Optional[str] = None
    disponible: Optional[bool] = None

# --- ESQUEMA PARA CAMBIAR ESTADO / ASIGNAR REPARTIDOR EN PEDIDO ---
class PedidoUpdateEstado(BaseModel):
    estado: Optional[str] = None  # PENDIENTE, EN_RUTA, ENTREGADO, CANCELADO
    repartidor_id: Optional[int] = None

    # --- ACTUALIZACIÓN DE CATEGORÍA Y SUCURSAL ---
class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    activa: Optional[bool] = None

class SucursalUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    correo_contacto: Optional[str] = None
    activa: Optional[bool] = None