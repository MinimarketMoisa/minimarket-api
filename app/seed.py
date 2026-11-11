
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from . import models as m
from .database import SessionLocal
from .init_db import init
from .security import hash_password

CLAVE = "Prueba12345"


def D(x) -> Decimal:
    return Decimal(str(x))


def run() -> None:
    init()
    with SessionLocal() as db:
        if db.scalar(select(m.Usuario.id_usuario).where(m.Usuario.email == "admin@minimarket.test")):
            print("Los datos de ejemplo ya existen.")
            return
        roles = {r.nombre: r.id_rol for r in db.scalars(select(m.Rol))}

        municipios = [m.Municipio(nombre=n) for n in ("San Miguel", "Quelepa", "Moncagua", "Chinameca")]
        db.add_all(municipios)
        db.flush()
        sm = municipios[0]

        coords = [(13.4833, -88.1833), (13.4890, -88.1760), (13.4770, -88.1900),
                  (13.4950, -88.1850), (13.4700, -88.1700)]
        sucursales = [
            m.Sucursal(id_municipio=sm.id_municipio, nombre=f"Minimarket San Miguel {i + 1}",
                       direccion=f"Dirección de ejemplo {i + 1}", telefono=f"2600-000{i + 1}",
                       latitud=D(lat), longitud=D(lon))
            for i, (lat, lon) in enumerate(coords)
        ]
        db.add_all(sucursales)

        categorias = {n: m.Categoria(nombre=n) for n in ("Hogar", "Comida", "Baño", "Limpieza")}
        db.add_all(categorias.values())
        db.flush()

        catalogo = [
            ("Arroz 1 lb", "Comida", "0.65", "https://walmartsv.vteximg.com.br/arquivos/ids/894752/M-5_walmartsv_NEDMdLbClp_124672_01.jpg"),
            ("Frijoles 1 lb", "Comida", "0.85", "https://walmartsv.vteximg.com.br/arquivos/ids/738824/63468_01.jpg"),
            ("Aceite 1 L", "Comida", "2.10", "https://walmartsv.vteximg.com.br/arquivos/ids/751028/47494_01.jpg"),
            ("Jabón de baño", "Baño", "0.75", "https://walmartsv.vteximg.com.br/arquivos/ids/865846/jabon-protex-omega-3-3-pack-660-g-0099176922780.webp"),
            ("Papel higiénico x4", "Baño", "1.90", "https://walmartsv.vteximg.com.br/arquivos/ids/904090/papel-higienico-scott-balance-32-ea-2-p-7441008104988.webp"),
            ("Detergente 1 kg", "Limpieza", "2.80", "https://walmartsv.vteximg.com.br/arquivos/ids/885202/M-5_walmartsv_MODVqOzupG_120250_01.jpg"),
            ("Cloro 1 galón", "Limpieza", "2.25", "https://walmartsv.vteximg.com.br/arquivos/ids/882994/cloro-great-value-bt-3785-ml-galon-7441078231140.webp"),
            ("Escoba", "Hogar", "3.50", "https://walmartsv.vteximg.com.br/arquivos/ids/921183/M-5_walmartsv_XpbvCIAKTl_51839_01.jpg"),
            ("Vasos plásticos x50", "Hogar", "1.40", "https://walmartsv.vteximg.com.br/arquivos/ids/771059/46419_01.jpg"),
        ]
        productos = [
            m.Producto(
                id_categoria=categorias[c].id_categoria,
                nombre=n,
                precio_base=D(p),
                imagen_url=img,
                activo=True,
            )
            for n, c, p, img in catalogo
        ]
        db.add_all(productos)
        db.flush()

        # Todas las sucursales tienen todo, salvo la escoba: solo las dos primeras
        for s_idx, s in enumerate(sucursales):
            for p in productos:
                if p.nombre == "Escoba" and s_idx > 1:
                    continue
                db.add(m.Inventario(id_sucursal=s.id_sucursal, id_producto=p.id_producto, stock_disponible=20))

        def usuario(nombre, email, rol, **extra):
            u = m.Usuario(id_rol=roles[rol], nombre_completo=nombre, email=email,
                          password=hash_password(CLAVE), email_verificado=True, **extra)
            db.add(u)
            db.flush()
            return u

        usuario("Administrador", "admin@minimarket.test", "ADMIN", is_staff=True, is_superuser=True)
        emp = usuario("Empleado Sucursal 1", "empleado@minimarket.test", "EMPLEADO", is_staff=True)
        db.add(m.Empleado(id_empleado=emp.id_usuario, id_sucursal=sucursales[0].id_sucursal, cargo="Cajero"))

        for i, (lat, lon) in enumerate([(13.4840, -88.1840), (13.4960, -88.1700)], start=1):
            r = usuario(f"Repartidor {i}", f"repartidor{i}@minimarket.test", "REPARTIDOR")
            db.add(m.PerfilRepartidor(
                id_repartidor=r.id_usuario, estado_operativo="LIBRE", placa_vehiculo=f"M-00{i}",
                latitud_actual=D(lat), longitud_actual=D(lon), ultima_actualizacion=datetime.now(timezone.utc),
            ))

        cli = usuario("Cliente de Prueba", "cliente@minimarket.test", "CLIENTE", telefono="7000-0000")
        db.add(m.Direccion(id_cliente=cli.id_usuario, id_municipio=sm.id_municipio,
                           detalle_direccion="Colonia de ejemplo, casa 12", punto_referencia="Frente a la iglesia"))
        db.commit()

    print("Datos de ejemplo creados. Usuarios (clave para todos: %s):" % CLAVE)
    for e in ("admin", "empleado", "repartidor1", "repartidor2", "cliente"):
        print(f"  {e}@minimarket.test")


if __name__ == "__main__":
    run()
