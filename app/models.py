from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(200), nullable=True)

    usuarios = relationship("Usuario", back_populates="rol")


class Sucursal(Base):
    __tablename__ = "sucursales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    direccion = Column(String(200), nullable=False)
    telefono = Column(String(15), nullable=False)
    correo_contacto = Column(String(254), nullable=True)
    activa = Column(Boolean, default=True, nullable=False)

    pedidos = relationship("Pedido", back_populates="sucursal")


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    activa = Column(Boolean, default=True, nullable=False)

    productos = relationship("Producto", back_populates="categoria")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    nombre_usuario = Column(String(150), unique=True, nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(254), nullable=False)
    nombre_completo = Column(String(150), nullable=False)
    telefono = Column(String(15), nullable=True)
    direccion_entrega = Column(String(200), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)

    rol = relationship("Rol", back_populates="usuarios")
    pedidos_como_cliente = relationship(
        "Pedido", 
        back_populates="cliente", 
        foreign_keys="Pedido.cliente_id"
    )
    pedidos_como_repartidor = relationship(
        "Pedido", 
        back_populates="repartidor", 
        foreign_keys="Pedido.repartidor_id"
    )


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    nombre_producto = Column(String(150), nullable=False)
    descripcion_producto = Column(Text, nullable=True)
    precio_venta = Column(Numeric(10, 2), nullable=False)
    stock_actual = Column(Integer, default=0, nullable=False)
    imagen = Column(String(255), nullable=True)
    disponible = Column(Boolean, default=True, nullable=False)

    categoria = relationship("Categoria", back_populates="productos")
    detalles_pedido = relationship("DetallePedido", back_populates="producto")


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        CheckConstraint("precio_venta > 0", name="chk_precio_positivo"),
        CheckConstraint("stock_actual >= 0", name="chk_stock_no_negativo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    repartidor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    estado = Column(String(20), default="PENDIENTE", nullable=False)
    metodo_pago = Column(String(20), nullable=False)
    tipo_entrega = Column(String(20), nullable=False)
    direccion_destino = Column(String(200), nullable=False)
    total_orden = Column(Numeric(10, 2), default=0.00, nullable=False)
    fecha_pedido = Column(DateTime, default=datetime.utcnow, nullable=False)

    cliente = relationship("Usuario", back_populates="pedidos_como_cliente", foreign_keys=[cliente_id])
    repartidor = relationship("Usuario", back_populates="pedidos_como_repartidor", foreign_keys=[repartidor_id])
    sucursal = relationship("Sucursal", back_populates="pedidos")
    detalles = relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")


class DetallePedido(Base):
    __tablename__ = "detalles_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    pedido = relationship("Pedido", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_pedido")