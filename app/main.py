from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from . import models, schemas
from .database import engine, get_db

# Crea las 7 tablas en PostgreSQL si aún no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Minimarket REST API",
    description="API para App Móvil (Flutter), Web y Gestión de Inventario",
    version="1.0.0"
)

# Habilitar CORS para peticiones desde emuladores o web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health Check"])
def health_check():
    return {"status": "ok", "message": "Minimarket API activa"}


# --------------------- CATEGORÍAS ---------------------
@app.get("/api/categorias/", response_model=List[schemas.CategoriaResponse], tags=["Categorías"])
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(models.Categoria).all()

@app.post("/api/categorias/", response_model=schemas.CategoriaResponse, status_code=status.HTTP_201_CREATED, tags=["Categorías"])
def crear_categoria(categoria: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    existente = db.query(models.Categoria).filter(models.Categoria.nombre == categoria.nombre).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una categoría con el nombre '{categoria.nombre}'.",
        )

    db_cat = models.Categoria(**categoria.model_dump())
    db.add(db_cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una categoría con el nombre '{categoria.nombre}'.",
        )
    db.refresh(db_cat)
    return db_cat


# --------------------- PRODUCTOS ---------------------
@app.get("/api/productos/", response_model=List[schemas.ProductoResponse], tags=["Productos"])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(models.Producto).all()

@app.post("/api/productos/", response_model=schemas.ProductoResponse, status_code=status.HTTP_201_CREATED, tags=["Productos"])
def crear_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db)):
    categoria = db.query(models.Categoria).filter(models.Categoria.id == producto.categoria_id).first()
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La categoría #{producto.categoria_id} no existe. Crea la categoría antes del producto.",
        )

    db_prod = models.Producto(**producto.model_dump())
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    return db_prod


# --------------------- SUCURSALES ---------------------
@app.get("/api/sucursales/", response_model=List[schemas.SucursalResponse], tags=["Sucursales"])
def listar_sucursales(db: Session = Depends(get_db)):
    return db.query(models.Sucursal).all()

@app.post("/api/sucursales/", response_model=schemas.SucursalResponse, status_code=status.HTTP_201_CREATED, tags=["Sucursales"])
def crear_sucursal(sucursal: schemas.SucursalCreate, db: Session = Depends(get_db)):
    db_suc = models.Sucursal(**sucursal.model_dump())
    db.add(db_suc)
    db.commit()
    db.refresh(db_suc)
    return db_suc


# --------------------- PEDIDOS (TRANSACCIONAL) ---------------------
@app.get("/api/pedidos/", response_model=List[schemas.PedidoResponse], tags=["Pedidos"])
def listar_pedidos(db: Session = Depends(get_db)):
    return db.query(models.Pedido).all()

@app.post("/api/pedidos/", response_model=schemas.PedidoResponse, status_code=status.HTTP_201_CREATED, tags=["Pedidos"])
def crear_pedido(pedido_in: schemas.PedidoCreate, db: Session = Depends(get_db)):
    # 1. Crear cabecera de la orden
    nuevo_pedido = models.Pedido(
        cliente_id=pedido_in.cliente_id,
        sucursal_id=pedido_in.sucursal_id,
        metodo_pago=pedido_in.metodo_pago,
        tipo_entrega=pedido_in.tipo_entrega,
        direccion_destino=pedido_in.direccion_destino,
        total_orden=0.00
    )
    db.add(nuevo_pedido)
    db.flush()  # Obtiene el ID del pedido sin confirmar la transacción todavía

    total_calculado = 0.0

    # 2. Procesar ítems y descontar inventario
    for item in pedido_in.detalles:
        producto = db.query(models.Producto).filter(models.Producto.id == item.producto_id).first()
        if not producto:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Producto #{item.producto_id} no existe")
        
        if producto.stock_actual < item.cantidad:
            db.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"Stock insuficiente para '{producto.nombre_producto}'. Disponible: {producto.stock_actual}"
            )

        # Descontar stock
        producto.stock_actual -= item.cantidad
        
        # Calcular subtotales
        subtotal = float(producto.precio_venta) * item.cantidad
        total_calculado += subtotal

        detalle = models.DetallePedido(
            pedido_id=nuevo_pedido.id,
            producto_id=producto.id,
            cantidad=item.cantidad,
            precio_unitario=producto.precio_venta,
            subtotal=subtotal
        )
        db.add(detalle)

    # 3. Asignar total y persistir
    nuevo_pedido.total_orden = total_calculado
    db.commit()
    db.refresh(nuevo_pedido)
    return nuevo_pedido

# ==========================================
# ROLES
# ==========================================
@app.get("/api/roles/", response_model=List[schemas.RolResponse], tags=["Roles"])
def listar_roles(db: Session = Depends(get_db)):
    return db.query(models.Rol).all()

@app.post("/api/roles/", response_model=schemas.RolResponse, status_code=status.HTTP_201_CREATED, tags=["Roles"])
def crear_rol(rol: schemas.RolCreate, db: Session = Depends(get_db)):
    db_rol = models.Rol(**rol.model_dump())
    db.add(db_rol)
    db.commit()
    db.refresh(db_rol)
    return db_rol

@app.put("/api/roles/{rol_id}", response_model=schemas.RolResponse, tags=["Roles"])
def actualizar_rol(rol_id: int, rol_in: schemas.RolUpdate, db: Session = Depends(get_db)):
    rol = db.query(models.Rol).filter(models.Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    for key, value in rol_in.model_dump(exclude_unset=True).items():
        setattr(rol, key, value)
    
    db.commit()
    db.refresh(rol)
    return rol


# ==========================================
# USUARIOS
# ==========================================
@app.get("/api/usuarios/", response_model=List[schemas.UsuarioResponse], tags=["Usuarios"])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()

@app.post("/api/usuarios/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED, tags=["Usuarios"])
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Validar que el rol exista
    rol = db.query(models.Rol).filter(models.Rol.id == usuario.rol_id).first()
    if not rol:
        raise HTTPException(status_code=400, detail="El rol_id especificado no existe")

    # Validar email o usuario repetido
    if db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    db_usuario = models.Usuario(
        rol_id=usuario.rol_id,
        nombre_usuario=usuario.nombre_usuario,
        email=usuario.email,
        password_hash=usuario.password,  # Aquí se almacena el hash
        nombre_completo=usuario.nombre_completo,
        telefono=usuario.telefono,
        direccion_entrega=usuario.direccion_entrega,
        activo=usuario.activo
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@app.put("/api/usuarios/{usuario_id}", response_model=schemas.UsuarioResponse, tags=["Usuarios"])
def actualizar_usuario(usuario_id: int, usuario_in: schemas.UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario_in.rol_id is not None:
        rol = db.query(models.Rol).filter(models.Rol.id == usuario_in.rol_id).first()
        if not rol:
            raise HTTPException(status_code=400, detail="El rol_id no existe")

    for key, value in usuario_in.model_dump(exclude_unset=True).items():
        setattr(usuario, key, value)

    db.commit()
    db.refresh(usuario)
    return usuario


# ==========================================
# ACTUALIZAR PRODUCTOS
# ==========================================
@app.put("/api/productos/{producto_id}", response_model=schemas.ProductoResponse, tags=["Productos"])
def actualizar_producto(producto_id: int, producto_in: schemas.ProductoUpdate, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for key, value in producto_in.model_dump(exclude_unset=True).items():
        setattr(producto, key, value)

    db.commit()
    db.refresh(producto)
    return producto


# ==========================================
# ACTUALIZAR ESTADO DEL PEDIDO / REPARTIDOR
# ==========================================
@app.patch("/api/pedidos/{pedido_id}/estado", response_model=schemas.PedidoResponse, tags=["Pedidos"])
def cambiar_estado_pedido(pedido_id: int, cambio: schemas.PedidoUpdateEstado, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if cambio.repartidor_id is not None:
        repartidor = db.query(models.Usuario).filter(models.Usuario.id == cambio.repartidor_id).first()
        if not repartidor:
            raise HTTPException(status_code=404, detail="El repartidor no existe")
        pedido.repartidor_id = cambio.repartidor_id

    if cambio.estado is not None:
        pedido.estado = cambio.estado

    db.commit()
    db.refresh(pedido)
    return pedido


@app.put("/api/categorias/{categoria_id}", response_model=schemas.CategoriaResponse, tags=["Categorías"])
def actualizar_categoria(categoria_id: int, cat_in: schemas.CategoriaUpdate, db: Session = Depends(get_db)):
    categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    for key, value in cat_in.model_dump(exclude_unset=True).items():
        setattr(categoria, key, value)

    db.commit()
    db.refresh(categoria)
    return categoria


@app.put("/api/sucursales/{sucursal_id}", response_model=schemas.SucursalResponse, tags=["Sucursales"])
def actualizar_sucursal(sucursal_id: int, suc_in: schemas.SucursalUpdate, db: Session = Depends(get_db)):
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.id == sucursal_id).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    for key, value in suc_in.model_dump(exclude_unset=True).items():
        setattr(sucursal, key, value)

    db.commit()
    db.refresh(sucursal)
    return sucursal