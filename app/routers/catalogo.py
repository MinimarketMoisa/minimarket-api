from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..deps import require_roles
from ..schemas import (CategoriaOut, DisponibilidadOut, MunicipioOut, ProductoIn,
                       ProductoOut, SucursalOut)

router = APIRouter(tags=["Catálogo"])


@router.get("/municipios", response_model=list[MunicipioOut])
def listar_municipios(db: Session = Depends(get_db)):
    return db.scalars(select(m.Municipio).order_by(m.Municipio.nombre)).all()


@router.get("/sucursales", response_model=list[SucursalOut])
def listar_sucursales(id_municipio: Optional[int] = None, db: Session = Depends(get_db)):
    q = select(m.Sucursal).where(m.Sucursal.activa.is_(True))
    if id_municipio is not None:
        q = q.where(m.Sucursal.id_municipio == id_municipio)
    return db.scalars(q.order_by(m.Sucursal.nombre)).all()


@router.get("/categorias", response_model=list[CategoriaOut])
def listar_categorias(db: Session = Depends(get_db)):
    return db.scalars(select(m.Categoria).order_by(m.Categoria.nombre)).all()


@router.get("/productos", response_model=list[ProductoOut])
def listar_productos(
    id_categoria: Optional[int] = None,
    q: Optional[str] = Query(None, min_length=1, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    consulta = select(m.Producto).where(m.Producto.activo.is_(True))
    if id_categoria is not None:
        consulta = consulta.where(m.Producto.id_categoria == id_categoria)
    if q:
        consulta = consulta.where(m.Producto.nombre.ilike(f"%{q}%"))
    return db.scalars(consulta.order_by(m.Producto.nombre).offset(skip).limit(limit)).all()


@router.get("/productos/{id_producto}", response_model=ProductoOut)
def detalle_producto(id_producto: int, db: Session = Depends(get_db)):
    producto = db.get(m.Producto, id_producto)
    if producto is None or not producto.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return producto


@router.get("/productos/{id_producto}/disponibilidad", response_model=list[DisponibilidadOut])
def disponibilidad(id_producto: int, db: Session = Depends(get_db)):
    """En qué sucursales hay stock de este producto."""
    filas = db.execute(
        select(m.Sucursal.id_sucursal, m.Sucursal.nombre, m.Inventario.stock_disponible)
        .join(m.Inventario, m.Inventario.id_sucursal == m.Sucursal.id_sucursal)
        .where(m.Inventario.id_producto == id_producto, m.Inventario.stock_disponible > 0,
               m.Sucursal.activa.is_(True))
        .order_by(m.Sucursal.nombre)
    ).all()
    return [DisponibilidadOut(id_sucursal=f[0], nombre_sucursal=f[1], stock_disponible=f[2]) for f in filas]


@router.post("/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(data: ProductoIn, _=Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    if db.get(m.Categoria, data.id_categoria) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    producto = m.Producto(**data.model_dump())
    db.add(producto)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El código de barras ya existe")
    return producto
