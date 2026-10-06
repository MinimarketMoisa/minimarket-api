"""Modelos SQLAlchemy. Equivalen al script schema_minimarket.sql.

Los nombres de tablas y columnas son los mismos del diagrama, para que Django
pueda mapearlos con `inspectdb` sin renombrar nada.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Computed, Date, DateTime, ForeignKey,
    ForeignKeyConstraint, Identity, Index, Integer, Numeric, String,
    UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _pk():
    return mapped_column(BigInteger, Identity(always=False), primary_key=True)


def _fk(destino: str, *, nullable: bool = False, ondelete: str = "RESTRICT"):
    return mapped_column(
        BigInteger,
        ForeignKey(destino, ondelete=ondelete, onupdate="CASCADE"),
        nullable=nullable,
    )


class Rol(Base):
    __tablename__ = "rol"
    id_rol: Mapped[int] = _pk()
    nombre: Mapped[str] = mapped_column(String(50), unique=True)


class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario: Mapped[int] = _pk()
    id_rol: Mapped[int] = _fk("rol.id_rol")
    nombre_completo: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254))
    password: Mapped[str] = mapped_column(String(128))
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # Columnas que Django necesita para usar esta tabla como modelo de usuario / Admin
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    rol: Mapped["Rol"] = relationship()


# Correo unico sin distinguir mayusculas
Index("uq_usuario_email", func.lower(Usuario.__table__.c.email), unique=True)


class Municipio(Base):
    __tablename__ = "municipio"
    id_municipio: Mapped[int] = _pk()
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class Direccion(Base):
    __tablename__ = "direccion"
    id_direccion: Mapped[int] = _pk()
    id_cliente: Mapped[int] = _fk("usuario.id_usuario")
    id_municipio: Mapped[int] = _fk("municipio.id_municipio")
    detalle_direccion: Mapped[str] = mapped_column(String(300))
    punto_referencia: Mapped[Optional[str]] = mapped_column(String(300))

    __table_args__ = (UniqueConstraint("id_direccion", "id_cliente", name="uq_direccion_cliente"),)


class Sucursal(Base):
    __tablename__ = "sucursal"
    id_sucursal: Mapped[int] = _pk()
    id_municipio: Mapped[int] = _fk("municipio.id_municipio")
    nombre: Mapped[str] = mapped_column(String(100))
    direccion: Mapped[str] = mapped_column(String(300))
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    latitud: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    __table_args__ = (
        CheckConstraint("latitud BETWEEN -90 AND 90", name="ck_sucursal_latitud"),
        CheckConstraint("longitud BETWEEN -180 AND 180", name="ck_sucursal_longitud"),
    )


class Empleado(Base):
    __tablename__ = "empleado"
    id_empleado: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id_usuario", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True, autoincrement=False,
    )
    id_sucursal: Mapped[int] = _fk("sucursal.id_sucursal")
    cargo: Mapped[str] = mapped_column(String(50))


class PerfilRepartidor(Base):
    __tablename__ = "perfil_repartidor"
    id_repartidor: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id_usuario", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True, autoincrement=False,
    )
    estado_operativo: Mapped[str] = mapped_column(String(20), default="LIBRE", server_default=text("'LIBRE'"))
    placa_vehiculo: Mapped[Optional[str]] = mapped_column(String(20))
    latitud_actual: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    longitud_actual: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    ultima_actualizacion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("estado_operativo IN ('LIBRE', 'PENDIENTE')", name="ck_repartidor_estado"),
        CheckConstraint("latitud_actual BETWEEN -90 AND 90", name="ck_repartidor_latitud"),
        CheckConstraint("longitud_actual BETWEEN -180 AND 180", name="ck_repartidor_longitud"),
        CheckConstraint("(latitud_actual IS NULL) = (longitud_actual IS NULL)", name="ck_repartidor_coords"),
    )


class Categoria(Base):
    __tablename__ = "categoria"
    id_categoria: Mapped[int] = _pk()
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500))


class Producto(Base):
    __tablename__ = "producto"
    id_producto: Mapped[int] = _pk()
    id_categoria: Mapped[int] = _fk("categoria.id_categoria")
    codigo_barras: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[Optional[str]] = mapped_column(String(1000))
    precio_base: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    imagen_url: Mapped[Optional[str]] = mapped_column(String(500))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    __table_args__ = (CheckConstraint("precio_base >= 0", name="ck_producto_precio"),)


class Inventario(Base):
    __tablename__ = "inventario"
    id_inventario: Mapped[int] = _pk()
    id_sucursal: Mapped[int] = _fk("sucursal.id_sucursal")
    id_producto: Mapped[int] = _fk("producto.id_producto")
    stock_disponible: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint("stock_disponible >= 0", name="ck_inventario_stock"),
        UniqueConstraint("id_sucursal", "id_producto", name="uq_inventario_sucursal_producto"),
    )


class Pedido(Base):
    __tablename__ = "pedido"
    id_pedido: Mapped[int] = _pk()
    id_cliente: Mapped[int] = _fk("usuario.id_usuario")
    id_sucursal: Mapped[int] = _fk("sucursal.id_sucursal")
    id_repartidor: Mapped[Optional[int]] = _fk("perfil_repartidor.id_repartidor", nullable=True)
    id_direccion: Mapped[Optional[int]] = mapped_column(BigInteger)
    canal: Mapped[str] = mapped_column(String(10))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", server_default=text("'PENDIENTE'"))
    tipo_entrega: Mapped[str] = mapped_column(String(20))
    metodo_pago: Mapped[str] = mapped_column(String(20))
    estado_pago: Mapped[str] = mapped_column(String(20), default="PENDIENTE", server_default=text("'PENDIENTE'"))
    costo_envio: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), server_default=text("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    detalles: Mapped[list["DetallePedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        # La direccion debe ser del mismo cliente que hizo el pedido
        ForeignKeyConstraint(
            ["id_direccion", "id_cliente"],
            ["direccion.id_direccion", "direccion.id_cliente"],
            name="fk_pedido_direccion_cliente", ondelete="RESTRICT", onupdate="CASCADE",
        ),
        CheckConstraint("canal IN ('APP', 'WEB')", name="ck_pedido_canal"),
        CheckConstraint(
            "estado IN ('PENDIENTE', 'PREPARADO', 'EN_RUTA', 'ENTREGADO', 'CANCELADO')",
            name="ck_pedido_estado",
        ),
        CheckConstraint("tipo_entrega IN ('DOMICILIO', 'RETIRO')", name="ck_pedido_tipo_entrega"),
        CheckConstraint("metodo_pago IN ('CONTRA_ENTREGA', 'TRANSFERENCIA')", name="ck_pedido_metodo_pago"),
        CheckConstraint("estado_pago IN ('PENDIENTE', 'PAGADO')", name="ck_pedido_estado_pago"),
        CheckConstraint("costo_envio >= 0", name="ck_pedido_costo_envio"),
        CheckConstraint("total >= 0", name="ck_pedido_total"),
        CheckConstraint(
            "(tipo_entrega = 'DOMICILIO' AND id_direccion IS NOT NULL) OR "
            "(tipo_entrega = 'RETIRO' AND id_direccion IS NULL AND id_repartidor IS NULL AND costo_envio = 0)",
            name="ck_pedido_coherencia_entrega",
        ),
        Index("ix_pedido_cliente", "id_cliente"),
        Index("ix_pedido_sucursal_estado", "id_sucursal", "estado"),
        Index("ix_pedido_repartidor", "id_repartidor"),
        Index("ix_pedido_fecha", "fecha_creacion"),
    )


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"
    id_detalle: Mapped[int] = _pk()
    id_pedido: Mapped[int] = _fk("pedido.id_pedido", ondelete="CASCADE")
    id_producto: Mapped[int] = _fk("producto.id_producto")
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # precio congelado al comprar
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), Computed("cantidad * precio_unitario", persisted=True)
    )

    pedido: Mapped["Pedido"] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship()

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalle_cantidad"),
        CheckConstraint("precio_unitario >= 0", name="ck_detalle_precio"),
        UniqueConstraint("id_pedido", "id_producto", name="uq_detalle_pedido_producto"),
        Index("ix_detalle_producto", "id_producto"),
    )
