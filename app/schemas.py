from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator

# En el JSON los montos y coordenadas salen como numero (no como texto)
Num = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

TipoEntrega = Literal["DOMICILIO", "RETIRO"]
MetodoPago = Literal["CONTRA_ENTREGA", "TRANSFERENCIA"]
Canal = Literal["APP", "WEB"]
EstadoPedido = Literal["PENDIENTE", "PREPARADO", "EN_RUTA", "ENTREGADO", "CANCELADO"]
EstadoPago = Literal["PENDIENTE", "PAGADO"]
EstadoRepartidor = Literal["LIBRE", "PENDIENTE"]

ROLES_PERMITIDOS = {"CLIENTE", "REPARTIDOR", "EMPLEADO", "ADMIN"}


def validar_password(v: str) -> str:
    if len(v) < 8 or len(v) > 128:
        raise ValueError("La contraseña debe tener entre 8 y 128 caracteres")
    if v.lower() in {"12345678", "password", "contrasena", "qwerty1234", "admin1234"}:
        raise ValueError("La contraseña elegida es demasiado común o insegura")
    return v


def validar_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or "." not in v.split("@")[-1] or len(v) < 5 or len(v) > 254:
        raise ValueError("Dirección de correo electrónico inválida")
    return v


def validar_imagen_url(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v_clean = v.strip()
    if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
        raise ValueError("La URL de la imagen debe comenzar con http:// o https://")
    if "javascript:" in v_clean.lower():
        raise ValueError("URL de imagen no permitida")
    return v_clean


def validar_rol(v: Optional[str]) -> Optional[str]:
    if v is not None and v.upper() not in ROLES_PERMITIDOS:
        raise ValueError(f"Rol inválido. Roles válidos: {', '.join(sorted(ROLES_PERMITIDOS))}")
    return v.upper() if v else None


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Autenticacion ----
class RegistroIn(BaseModel):
    nombre_completo: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    telefono: Optional[str] = Field(default=None, max_length=20)

    @field_validator("email")
    @classmethod
    def _val_email(cls, v: str) -> str:
        return validar_email(v)

    @field_validator("password")
    @classmethod
    def _val_pwd(cls, v: str) -> str:
        return validar_password(v)


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
    activo: bool = True
    email_verificado: bool = False


class RegistroOut(UsuarioOut):
    mensaje: str = "Registro exitoso. Te hemos enviado un correo a tu Gmail con el enlace de verificación."


class ClienteAdminOut(BaseModel):
    id_usuario: int
    nombre_completo: str
    email: str
    telefono: Optional[str] = None
    rol: str
    activo: bool
    email_verificado: bool
    last_login: Optional[datetime] = None


class ClienteAdminUpdate(BaseModel):
    nombre_completo: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=20)
    activo: Optional[bool] = None
    email_verificado: Optional[bool] = None
    rol: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _val_pwd(cls, v: Optional[str]) -> Optional[str]:
        return validar_password(v) if v else None

    @field_validator("rol")
    @classmethod
    def _val_rol(cls, v: Optional[str]) -> Optional[str]:
        return validar_rol(v)


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

    @field_validator("imagen_url")
    @classmethod
    def _val_img(cls, v: Optional[str]) -> Optional[str]:
        return validar_imagen_url(v)


class DisponibilidadOut(BaseModel):
    id_sucursal: int
    nombre_sucursal: str
    stock_disponible: int


# ---- Direcciones ----
class DireccionIn(BaseModel):
    id_municipio: int
    detalle_direccion: str = Field(min_length=3, max_length=300)
    punto_referencia: Optional[str] = Field(default=None, max_length=300)
    latitud: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitud: Optional[Decimal] = Field(default=None, ge=-180, le=180)


class DireccionOut(ORM):
    id_direccion: int
    id_municipio: int
    detalle_direccion: str
    punto_referencia: Optional[str] = None
    latitud: Optional[Num] = None
    longitud: Optional[Num] = None


# ---- Pedidos ----
class PedidoItemIn(BaseModel):
    id_producto: int
    cantidad: int = Field(gt=0, le=1000)


class PedidoIn(BaseModel):
    items: list[PedidoItemIn] = Field(min_length=1, max_length=50)
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
    nombre_repartidor: Optional[str] = None
    telefono_repartidor: Optional[str] = None
    id_direccion: Optional[int] = None
    canal: str
    tipo_entrega: str
    metodo_pago: str
    estado: str
    estado_pago: str
    estado_repartidor: Optional[str] = None
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


class RechazoIn(BaseModel):
    motivo: Optional[str] = Field(None, max_length=200)


class RechazoOut(BaseModel):
    mensaje: str
    reasignado: bool
    nuevo_repartidor_id: Optional[int] = None
    pedido: PedidoOut


class ClienteParaRepartidorOut(BaseModel):
    nombre_completo: str
    telefono: Optional[str] = None


class DestinoEntregaOut(BaseModel):
    id_direccion: Optional[int] = None
    detalle_direccion: str
    punto_referencia: Optional[str] = None
    municipio: Optional[str] = None
    latitud: Optional[Num] = None
    longitud: Optional[Num] = None


class SucursalEntregaOut(BaseModel):
    id_sucursal: int
    nombre: str
    direccion: str
    telefono: Optional[str] = None
    latitud: Optional[Num] = None
    longitud: Optional[Num] = None


class PedidoParaRepartidorOut(BaseModel):
    id_pedido: int
    estado: str
    estado_repartidor: Optional[str] = None
    canal: str
    metodo_pago: str
    estado_pago: str
    costo_envio: Num
    total: Num
    fecha_creacion: Optional[datetime] = None
    cliente: ClienteParaRepartidorOut
    destino: Optional[DestinoEntregaOut] = None
    sucursal: SucursalEntregaOut
    detalles: list[DetalleOut]


class RechazoRepartidorOut(BaseModel):
    mensaje: str
    reasignado: bool
    nuevo_repartidor_id: Optional[int] = None
    pedido: Optional[PedidoParaRepartidorOut] = None


# ---- Seguimiento y Tracking en Vivo ----
class SucursalSeguimientoOut(BaseModel):
    id_sucursal: int
    nombre: str
    direccion: str
    telefono: Optional[str] = None
    latitud: Optional[Num] = None
    longitud: Optional[Num] = None


class DestinoSeguimientoOut(BaseModel):
    id_direccion: Optional[int] = None
    detalle_direccion: str
    punto_referencia: Optional[str] = None
    municipio: Optional[str] = None
    latitud: Optional[Num] = None
    longitud: Optional[Num] = None


class RepartidorSeguimientoOut(BaseModel):
    id_repartidor: int
    nombre: str
    telefono: Optional[str] = None
    latitud: Optional[Num] = None
    longitud: Optional[Num] = None
    ultima_actualizacion: Optional[datetime] = None


class SeguimientoPedidoOut(BaseModel):
    id_pedido: int
    estado: str
    estado_repartidor: Optional[str] = None
    tipo_entrega: str
    canal: str
    sucursal: SucursalSeguimientoOut
    destino: Optional[DestinoSeguimientoOut] = None
    repartidor: Optional[RepartidorSeguimientoOut] = None


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


class SolicitarCambioEmailIn(BaseModel):
    nuevo_email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, description="Contraseña actual para verificar tu identidad")

    @field_validator("nuevo_email")
    @classmethod
    def _val_email(cls, v: str) -> str:
        return validar_email(v)


class ConfirmarCambioEmailIn(BaseModel):
    token: str


class VerificarEmailIn(BaseModel):
    token: str


class ReenviarVerificacionIn(BaseModel):
    email: str = Field(min_length=5, max_length=254)

    @field_validator("email")
    @classmethod
    def _val_email(cls, v: str) -> str:
        return validar_email(v)


class OlvideContrasenaIn(BaseModel):
    email: str = Field(min_length=5, max_length=254)

    @field_validator("email")
    @classmethod
    def _val_email(cls, v: str) -> str:
        return validar_email(v)


class RestablecerContrasenaIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _val_pwd(cls, v: str) -> str:
        return validar_password(v)


class MensajeRespuesta(BaseModel):
    mensaje: str
    verificado: Optional[bool] = None


class CategoriaIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)


class ProductoUpdate(BaseModel):
    id_categoria: Optional[int] = None
    codigo_barras: Optional[str] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    precio_base: Optional[Decimal] = Field(None, gt=0)
    precio: Optional[Decimal] = Field(None, gt=0)
    imagen_url: Optional[str] = Field(None, max_length=500)
    activo: Optional[bool] = None

    @field_validator("imagen_url")
    @classmethod
    def _val_img(cls, v: Optional[str]) -> Optional[str]:
        return validar_imagen_url(v)


# ---- Denuncias ----
class DenunciaIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=1000)


class DenunciaOut(BaseModel):
    id_denuncia: int
    id_pedido: int
    id_cliente: int
    nombre_cliente: str
    id_repartidor: int
    nombre_repartidor: str
    motivo: str
    descripcion: Optional[str] = None
    estado: str
    fecha_creacion: datetime
    resolucion_admin: Optional[str] = None


class ResolverDenunciaIn(BaseModel):
    estado: Literal["PENDIENTE", "INVESTIGANDO", "RESUELTO", "DESESTIMADA"]
    resolucion_admin: Optional[str] = Field(None, max_length=500)


# ---- Reportes ----
class ResumenSucursalOut(BaseModel):
    id_sucursal: int
    nombre_sucursal: str
    total_pedidos: int
    total_ventas: Num


class TopProductoOut(BaseModel):
    id_producto: int
    nombre_producto: str
    unidades_vendidas: int
    ingresos: Num


class ReporteDiarioOut(BaseModel):
    fecha: date
    total_pedidos: int
    pedidos_entregados: int
    pedidos_cancelados: int
    pedidos_en_proceso: int
    ingresos_totales: Num
    ingresos_productos: Num
    ingresos_envio: Num
    por_metodo_pago: dict[str, Num]
    por_sucursal: list[ResumenSucursalOut]
    top_productos: list[TopProductoOut]


class VentaPorDiaOut(BaseModel):
    dia: int
    total_pedidos: int
    total_ventas: Num


class RendimientoRepartidorOut(BaseModel):
    id_repartidor: int
    nombre_repartidor: str
    entregas_completadas: int


class ReporteMensualOut(BaseModel):
    anio: int
    mes: int
    total_pedidos: int
    ingresos_totales: Num
    ingresos_productos: Num
    ingresos_envio: Num
    tasa_efectividad_porcentaje: float
    ventas_por_dia: list[VentaPorDiaOut]
    ventas_por_sucursal: list[ResumenSucursalOut]
    rendimiento_repartidores: list[RendimientoRepartidorOut]
    top_productos_mes: list[TopProductoOut]
