from app.database import SessionLocal
from app import models
from decimal import Decimal

def seed():
    db = SessionLocal()
    try:
        print("🌱 Verificando datos iniciales...")

        # 1. ROLES OFICIALES (Requerimiento Sprint 1)
        roles_data = [
            {"nombre": "ADMIN", "descripcion": "Administrador del minimarket y catalogo"},
            {"nombre": "CLIENTE", "descripcion": "Usuario de compras en la app movil"},
            {"nombre": "REPARTIDOR", "descripcion": "Encargado de entregas y despacho"},
        ]
        for r in roles_data:
            if not db.query(models.Rol).filter_by(nombre=r["nombre"]).first():
                db.add(models.Rol(**r))
        db.commit()

        # 2. SUCURSAL BASE
        if not db.query(models.Sucursal).first():
            sucursal = models.Sucursal(
                nombre="Minimarket Central",
                direccion="Av. Roosevelt Sur, San Miguel",
                telefono="26601234",
                correo_contacto="contacto@minimarket.com",
                activa=True
            )
            db.add(sucursal)
            db.commit()

        # 3. CATEGORÍAS PILOTO
        categorias = {
            "Bebidas": "Gaseosas, jugos y aguas purificadas",
            "Snacks": "Bocadillos, galletas y frituras",
            "Lácteos": "Leche, quesos y derivados lácteos",
            "Abarrotes": "Granos básicos, aceites y enlatados"
        }
        cat_map = {}
        for nombre, desc in categorias.items():
            cat = db.query(models.Categoria).filter_by(nombre=nombre).first()
            if not cat:
                cat = models.Categoria(nombre=nombre, descripcion=desc, activa=True)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_map[nombre] = cat.id

        # 4. PRODUCTOS PILOTO (Con precios positivos y stock real)
        productos = [
            ("Coca-Cola 2.5L", cat_map["Bebidas"], "Bebida gaseosa retornable", Decimal("2.25"), 40),
            ("Agua Cristal 1.5L", cat_map["Bebidas"], "Agua purificada", Decimal("0.85"), 60),
            ("Jugo Del Valle Naranja 1L", cat_map["Bebidas"], "Jugo de naranja pasteurizado", Decimal("1.35"), 30),
            ("Papas Diana Jalapeño", cat_map["Snacks"], "Frituras clásicas", Decimal("0.35"), 100),
            ("Galletas Oreo 6 unidades", cat_map["Snacks"], "Galletas de chocolate con crema", Decimal("0.60"), 50),
            ("Leche Salud Entera 1L", cat_map["Lácteos"], "Leche fluida pasteurizada", Decimal("1.45"), 25),
            ("Arroz Blanco San Francisco 1lb", cat_map["Abarrotes"], "Arroz grano entero", Decimal("0.65"), 80),
            ("Frijol Rojo de Seda 1lb", cat_map["Abarrotes"], "Frijol nacional seleccionado", Decimal("1.15"), 90),
        ]

        for nombre, cat_id, desc, precio, stock in productos:
            if not db.query(models.Producto).filter_by(nombre_producto=nombre).first():
                db.add(models.Producto(
                    categoria_id=cat_id,
                    nombre_producto=nombre,
                    descripcion_producto=desc,
                    precio_venta=precio,
                    stock_actual=stock,
                    imagen="https://via.placeholder.com/200",
                    disponible=True
                ))
        db.commit()
        print("✅ Base de datos poblada con éxito.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()