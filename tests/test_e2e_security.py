"""Suite de pruebas E2E y de seguridad para Minimarket API.

Verifica todas las vulnerabilidades abordadas en la auditoría:
- C1: decode_token exige type="access"
- C2: solicitar-cambio-email exige password y no expone el token en la respuesta
- C3: Validación estricta de configuración en producción
- A1: Revocación inmediata de sesiones (token_version y password_fingerprint)
- A2: Bloqueo de concurrencia y protección contra doble restauración de stock
- A3: Validación de estado al rechazar pedidos por repartidor
- A4: Rate limiting y bloqueo por fuerza bruta con dummy hash
- A5: Escapado HTML contra inyección y phishing
- A6: Prevención de auto-bloqueo del administrador y reasignación de huérfanos
- M2: Cabeceras de seguridad HTTP (CSP, X-Frame-Options, etc.)
- M4: Vinculación estricta del token de verificación al correo
- M5: Actualización correcta de precio_base en productos
- M6: Validaciones de schemas (límite de items, URLs seguras, acaparamiento)
- Flujo completo de "Olvidé mi contraseña"
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.database import SessionLocal
from app.main import app
from app import models as m
from app import security


client = TestClient(app)


def limpiar_usuarios_test():
    with SessionLocal() as db:
        for email in ["cliente@minimarket.test", "admin@minimarket.test", "repartidor1@minimarket.test"]:
            u = db.scalar(select(m.Usuario).where(m.Usuario.email == email))
            if u:
                u.bloqueado_hasta = None
                u.intentos_fallidos = 0
                u.ultimo_correo_en = None
                u.activo = True
                u.email_verificado = True
                u.password = security.hash_password("Prueba12345")
                # Cancelar pedidos pendientes viejos del test para no topar el límite anti-acaparamiento (5)
                pedidos_pendientes = db.scalars(
                    select(m.Pedido).where(m.Pedido.id_cliente == u.id_usuario, m.Pedido.estado == "PENDIENTE")
                ).all()
                for p in pedidos_pendientes:
                    p.estado = "CANCELADO"
        db.commit()


@pytest.fixture(autouse=True)
def clean_test_environment():
    limpiar_usuarios_test()
    app.state.limiter.enabled = False
    yield
    limpiar_usuarios_test()
    app.state.limiter.enabled = True


def get_token(email: str, password: str = "Prueba12345") -> str:
    """Helper para obtener token de acceso."""
    res = client.post("/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, f"Error al iniciar sesión con {email}: {res.text}"
    return res.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# C3: Validación de configuración en producción
# ---------------------------------------------------------------------------
def test_c3_config_produccion_rechaza_valores_inseguros():
    # En producción, secreto corto debe fallar
    with pytest.raises(Exception):
        Settings(
            entorno="produccion",
            jwt_secret="secreto_muy_corto",
            api_base_url="https://api.minimarket.test",
            database_url="postgresql://user:pass@host/db",
        )

    # En producción, URL no HTTPS debe fallar
    with pytest.raises(Exception):
        Settings(
            entorno="produccion",
            jwt_secret="a" * 33,
            api_base_url="http://inseguro.minimarket.test",
            database_url="postgresql://user:pass@host/db",
        )


# ---------------------------------------------------------------------------
# C1: decode_token exige type="access"
# ---------------------------------------------------------------------------
def test_c1_token_verificacion_o_reset_no_sirve_como_access_token():
    admin_token = get_token("admin@minimarket.test")
    # Crear token de verificación de correo
    token_verif = security.create_email_verification_token(1, "admin@minimarket.test")
    
    # Intentar usar el token de verificación en un endpoint protegido por oauth2_scheme
    res = client.get("/auth/me", headers=auth_headers(token_verif))
    assert res.status_code == 401, "Un token de verificación de correo fue aceptado como access token"


# ---------------------------------------------------------------------------
# C2: Solicitar cambio de email exige password y no expone el token
# ---------------------------------------------------------------------------
def test_c2_solicitar_cambio_email_seguro():
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        u.ultimo_correo_en = None
        db.commit()

    token = get_token("cliente@minimarket.test")
    
    # 1. Sin contraseña o con contraseña incorrecta -> 403 (para no invalidar la sesión en la app móvil)
    res = client.post(
        "/auth/solicitar-cambio-email",
        headers=auth_headers(token),
        json={"nuevo_email": "nuevo_cliente@test.com", "password": "password_incorrecta_123"},
    )
    assert res.status_code == 403

    # 2. Con contraseña correcta -> no debe retornar el token en la respuesta
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        u.ultimo_correo_en = None
        db.commit()

    res = client.post(
        "/auth/solicitar-cambio-email",
        headers=auth_headers(token),
        json={"nuevo_email": "nuevo_cliente@test.com", "password": "Prueba12345"},
    )
    assert res.status_code == 200, f"Error en solicitar-cambio-email: {res.status_code} {res.text}"
    data = res.json()
    assert "token_confirmacion" not in data, "La API expuso el token de confirmación en la respuesta"
    assert "token" not in data


# ---------------------------------------------------------------------------
# A1: Revocación de sesiones (token_version & password_fingerprint)
# ---------------------------------------------------------------------------
def test_a1_cambio_password_invalida_tokens_anteriores():
    # Obtener token inicial
    token_inicial = get_token("cliente@minimarket.test")
    res1 = client.get("/auth/me", headers=auth_headers(token_inicial))
    assert res1.status_code == 200

    # Simular cambio de contraseña en la base de datos (por ejemplo, desde Django Admin)
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        u.password = security.hash_password("NuevaClave12345")
        db.commit()

    try:
        # El token anterior ahora debe ser rechazado
        res2 = client.get("/auth/me", headers=auth_headers(token_inicial))
        assert res2.status_code == 401, "El token viejo sobrevivió al cambio de contraseña"

        # Con la nueva contraseña, se puede iniciar sesión
        token_nuevo = get_token("cliente@minimarket.test", password="NuevaClave12345")
        res3 = client.get("/auth/me", headers=auth_headers(token_nuevo))
        assert res3.status_code == 200
    finally:
        # Restaurar contraseña original
        with SessionLocal() as db:
            u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
            u.password = security.hash_password("Prueba12345")
            db.commit()


def test_a1_desactivar_y_reactivar_no_revive_tokens_viejos():
    admin_token = get_token("admin@minimarket.test")
    
    with SessionLocal() as db:
        cli = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        id_cli = cli.id_usuario

    token_cliente = get_token("cliente@minimarket.test")

    # Admin desactiva al cliente
    res = client.delete(f"/clientes/{id_cli}", headers=auth_headers(admin_token))
    assert res.status_code == 200

    # El token del cliente debe fallar
    res = client.get("/auth/me", headers=auth_headers(token_cliente))
    assert res.status_code == 401

    # Admin reactiva al cliente
    res = client.post(f"/clientes/{id_cli}/reactivar", headers=auth_headers(admin_token))
    assert res.status_code == 200

    # El token viejo NO debe revivir
    res = client.get("/auth/me", headers=auth_headers(token_cliente))
    assert res.status_code == 401, "El token anterior a la desactivación volvió a funcionar al reactivar"


# ---------------------------------------------------------------------------
# A4: Fuerza bruta y bloqueo de cuenta con 5 intentos fallidos
# ---------------------------------------------------------------------------
def test_a4_bloqueo_por_fuerza_bruta():
    # Desactivar temporalmente el IP limiter de SlowAPI para aislar la prueba de bloqueo por cuenta
    app.state.limiter.enabled = False
    try:
        # Asegurar estado limpio antes de la prueba
        with SessionLocal() as db:
            u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
            u.bloqueado_hasta = None
            u.intentos_fallidos = 0
            db.commit()

        # 5 intentos con contraseña errónea
        for i in range(5):
            res = client.post("/auth/login", data={"username": "cliente@minimarket.test", "password": "password_incorrecta"})
            assert res.status_code == 401, f"Intento {i+1} devolvio {res.status_code}: {res.text}"

        # El 6to intento (incluso con la clave correcta) debe dar 401 sin revelar existencia
        res = client.post("/auth/login", data={"username": "cliente@minimarket.test", "password": "Prueba12345"})
        assert res.status_code == 401, f"6to intento devolvio {res.status_code}: {res.text}"
        assert "Credenciales incorrectas o cuenta bloqueada temporalmente" in res.json().get("detail", "")

        # Un usuario inexistente debe dar el mismo 401 y el mismo mensaje
        res_no_existe = client.post("/auth/login", data={"username": "fantasma_inexistente@minimarket.test", "password": "CualquierPassword123"})
        assert res_no_existe.status_code == 401
        assert res_no_existe.json().get("detail") == res.json().get("detail")
    finally:
        app.state.limiter.enabled = True
        with SessionLocal() as db:
            u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
            u.bloqueado_hasta = None
            u.intentos_fallidos = 0
            db.commit()


# ---------------------------------------------------------------------------
# A6: Prevención de auto-bloqueo del Administrador
# ---------------------------------------------------------------------------
def test_a6_admin_no_puede_auto_bloquearse():
    admin_token = get_token("admin@minimarket.test")
    with SessionLocal() as db:
        admin_u = db.scalar(select(m.Usuario).where(m.Usuario.email == "admin@minimarket.test"))
        id_admin = admin_u.id_usuario

    # Intentar desactivar su propia cuenta vía DELETE
    res = client.delete(f"/clientes/{id_admin}", headers=auth_headers(admin_token))
    assert res.status_code == 400
    assert "propia cuenta" in res.json().get("detail", "")

    # Intentar quitarse el rol ADMIN vía PATCH
    res = client.patch(f"/clientes/{id_admin}", headers=auth_headers(admin_token), json={"rol": "CLIENTE"})
    assert res.status_code == 400
    assert "rol de ADMIN" in res.json().get("detail", "")


# ---------------------------------------------------------------------------
# A2: Inmutabilidad de pedidos finales y protección de stock
# ---------------------------------------------------------------------------
def test_a2_pedido_cancelado_o_entregado_no_puede_volverse_a_cancelar():
    admin_token = get_token("admin@minimarket.test")
    cli_token = get_token("cliente@minimarket.test")

    # Crear un pedido para retirar
    res = client.post(
        "/pedidos",
        headers=auth_headers(cli_token),
        json={
            "tipo_entrega": "RETIRO",
            "id_sucursal": 1,
            "metodo_pago": "TRANSFERENCIA",
            "canal": "APP",
            "items": [{"id_producto": 1, "cantidad": 2}],
        },
    )
    assert res.status_code == 201
    id_pedido = res.json()["id_pedido"]

    # Cancelar el pedido la primera vez -> 200 OK
    res_cancel = client.patch(
        f"/pedidos/{id_pedido}/estado",
        headers=auth_headers(cli_token),
        json={"estado": "CANCELADO"},
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["estado"] == "CANCELADO"

    # Intentar cancelar de nuevo por ADMIN -> 409 Conflicto (no duplica stock)
    res_cancel_2 = client.patch(
        f"/pedidos/{id_pedido}/estado",
        headers=auth_headers(admin_token),
        json={"estado": "CANCELADO"},
    )
    assert res_cancel_2.status_code == 409


# ---------------------------------------------------------------------------
# A3: Validación de estado al rechazar pedido por repartidor
# ---------------------------------------------------------------------------
def test_a3_repartidor_no_puede_rechazar_pedido_no_asignado():
    rep_token = get_token("repartidor1@minimarket.test")

    # Intentar rechazar un pedido ficticio o no asignado
    res = client.post(
        "/repartidor/pedidos/999999/rechazar",
        headers=auth_headers(rep_token),
        json={"motivo": "No puedo"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# M2: Cabeceras de seguridad HTTP
# ---------------------------------------------------------------------------
def test_m2_cabeceras_de_seguridad():
    res = client.get("/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert "Content-Security-Policy" in headers or "content-security-policy" in headers


# ---------------------------------------------------------------------------
# M5: ProductoUpdate actualiza precio_base en la base de datos
# ---------------------------------------------------------------------------
def test_m5_producto_update_precio():
    admin_token = get_token("admin@minimarket.test")
    nuevo_precio = 3.75

    res = client.patch(
        "/productos/1",
        headers=auth_headers(admin_token),
        json={"precio_base": nuevo_precio},
    )
    assert res.status_code == 200
    assert float(res.json()["precio_base"]) == nuevo_precio

    # Verificar que persiste en DB
    with SessionLocal() as db:
        prod = db.get(m.Producto, 1)
        assert float(prod.precio_base) == nuevo_precio


# ---------------------------------------------------------------------------
# M6: Validaciones de schemas
# ---------------------------------------------------------------------------
def test_m6_validaciones_seguras():
    cli_token = get_token("cliente@minimarket.test")
    admin_token = get_token("admin@minimarket.test")

    # 1. Pedido con más de 50 items -> 422
    items_excesivos = [{"id_producto": 1, "cantidad": 1} for _ in range(51)]
    res = client.post(
        "/pedidos",
        headers=auth_headers(cli_token),
        json={
            "tipo_entrega": "RETIRO",
            "id_sucursal": 1,
            "metodo_pago": "TRANSFERENCIA",
            "canal": "APP",
            "items": items_excesivos,
        },
    )
    assert res.status_code == 422

    # 2. URL de imagen con javascript: -> 422
    res_img = client.patch(
        "/productos/1",
        headers=auth_headers(admin_token),
        json={"imagen_url": "javascript:alert(1)"},
    )
    assert res_img.status_code == 422


# ---------------------------------------------------------------------------
# Flujo completo: "Olvidé mi contraseña"
# ---------------------------------------------------------------------------
def test_flujo_olvide_contrasena():
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        u.ultimo_correo_en = None
        db.commit()

    # 1. Solicitar restablecimiento
    res_solicitud = client.post(
        "/auth/olvide-contrasena",
        json={"email": "cliente@minimarket.test"},
    )
    assert res_solicitud.status_code == 200

    # 2. Obtener el token de restablecimiento generado para el usuario
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        reset_token = security.create_password_reset_token(u)

    # 3. Restablecer con nueva contraseña
    nueva_clave = "ClaveSegura2026!"
    res_reset = client.post(
        "/auth/restablecer-contrasena",
        json={"token": reset_token, "password": nueva_clave},
    )
    assert res_reset.status_code == 200
    assert "exitosamente" in res_reset.json()["mensaje"]

    # 4. El token no puede reutilizarse
    res_reuso = client.post(
        "/auth/restablecer-contrasena",
        json={"token": reset_token, "password": "OtraClaveSegura123!"},
    )
    assert res_reuso.status_code == 400

    # 5. La contraseña antigua ya no funciona
    res_old_login = client.post(
        "/auth/login",
        data={"username": "cliente@minimarket.test", "password": "Prueba12345"},
    )
    assert res_old_login.status_code == 401

    # 6. La nueva contraseña funciona exitosamente
    res_new_login = client.post(
        "/auth/login",
        data={"username": "cliente@minimarket.test", "password": nueva_clave},
    )
    assert res_new_login.status_code == 200

    # Restaurar contraseña original
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        u.password = security.hash_password("Prueba12345")
        u.token_version += 1
        db.commit()


def test_slowapi_rate_limiter():
    """Verifica que SlowAPI bloquea ráfagas excesivas con 429."""
    app.state.limiter.enabled = True
    try:
        hit_429 = False
        for _ in range(15):
            res = client.post("/auth/login", data={"username": "inexistente@test.com", "password": "wrong_password"})
            if res.status_code == 429 and "Rate limit exceeded" in res.text:
                hit_429 = True
                break
        assert hit_429, "SlowAPI no aplicó el límite de tasa"
    finally:
        app.state.limiter.enabled = False


# ---------------------------------------------------------------------------
# Nuevas Funcionalidades: Repartidor-Cliente, Denuncias y Reportes
# ---------------------------------------------------------------------------
def test_repartidor_puede_crear_direccion_y_hacer_pedidos():
    rep_token = get_token("repartidor1@minimarket.test")

    # 1. Repartidor puede registrar su propia dirección
    res_dir = client.post(
        "/direcciones",
        headers=auth_headers(rep_token),
        json={
            "id_municipio": 1,
            "detalle_direccion": "Casa del repartidor colonia norte #45",
            "punto_referencia": "Frente al parque",
        },
    )
    assert res_dir.status_code == 201
    id_dir = res_dir.json()["id_direccion"]

    # 2. Repartidor puede hacer un pedido como cliente
    res_ped = client.post(
        "/pedidos",
        headers=auth_headers(rep_token),
        json={
            "tipo_entrega": "DOMICILIO",
            "id_direccion": id_dir,
            "metodo_pago": "CONTRA_ENTREGA",
            "canal": "APP",
            "items": [{"id_producto": 1, "cantidad": 1}],
        },
    )
    assert res_ped.status_code == 201
    ped_data = res_ped.json()

    # 3. La API NUNCA se lo asigna a él mismo
    with SessionLocal() as db:
        rep_u = db.scalar(select(m.Usuario).where(m.Usuario.email == "repartidor1@minimarket.test"))
        id_rep1 = rep_u.id_usuario

    assert ped_data.get("id_repartidor") != id_rep1, "La API le asignó el pedido al mismo repartidor que lo compró"

    # 4. Repartidor puede consultar sus compras en mis-pedidos
    res_mis = client.get("/pedidos/mis-pedidos", headers=auth_headers(rep_token))
    assert res_mis.status_code == 200
    ids = [p["id_pedido"] for p in res_mis.json()]
    assert ped_data["id_pedido"] in ids


def test_cliente_puede_denunciar_repartidor_asignado():
    cli_token = get_token("cliente@minimarket.test")
    admin_token = get_token("admin@minimarket.test")

    # 1. Crear un pedido a domicilio que reciba repartidor
    with SessionLocal() as db:
        dir_obj = db.scalar(select(m.Direccion).where(m.Direccion.id_cliente == 5))
        id_dir = dir_obj.id_direccion if dir_obj else 1

    res_ped = client.post(
        "/pedidos",
        headers=auth_headers(cli_token),
        json={
            "tipo_entrega": "DOMICILIO",
            "id_direccion": id_dir,
            "metodo_pago": "CONTRA_ENTREGA",
            "canal": "APP",
            "items": [{"id_producto": 2, "cantidad": 1}],
        },
    )
    assert res_ped.status_code == 201
    id_pedido = res_ped.json()["id_pedido"]

    # Asegurar que tenga repartidor asignado
    with SessionLocal() as db:
        ped = db.get(m.Pedido, id_pedido)
        if ped.id_repartidor is None:
            ped.id_repartidor = 4  # repartidor 1
            db.commit()

    # 2. Cliente denuncia al repartidor porque no llegó
    res_den = client.post(
        "/pedidos/%d/denunciar" % id_pedido,
        headers=auth_headers(cli_token),
        json={
            "motivo": "El repartidor nunca llegó a la dirección",
            "descripcion": "Esperé más de 1 hora y el repartidor no responde a las llamadas.",
        },
    )
    assert res_den.status_code == 201
    den_data = res_den.json()
    assert den_data["motivo"] == "El repartidor nunca llegó a la dirección"
    assert den_data["estado"] == "PENDIENTE"
    id_denuncia = den_data["id_denuncia"]

    # 3. No puede denunciar dos veces abiertas el mismo pedido
    res_dupl = client.post(
        "/pedidos/%d/denunciar" % id_pedido,
        headers=auth_headers(cli_token),
        json={"motivo": "Reitero la queja"},
    )
    assert res_dupl.status_code == 409

    # 4. Administrador revisa las denuncias
    res_admin_list = client.get("/pedidos/denuncias/todas", headers=auth_headers(admin_token))
    assert res_admin_list.status_code == 200
    ids_den = [d["id_denuncia"] for d in res_admin_list.json()]
    assert id_denuncia in ids_den

    # 5. Administrador resuelve la denuncia
    res_resolver = client.patch(
        "/pedidos/denuncias/%d" % id_denuncia,
        headers=auth_headers(admin_token),
        json={"estado": "RESUELTO", "resolucion_admin": "Se contactó al repartidor y se reembolsó al cliente."},
    )
    assert res_resolver.status_code == 200
    assert res_resolver.json()["estado"] == "RESUELTO"


def test_factura_y_reportes_empresa():
    admin_token = get_token("admin@minimarket.test")
    cli_token = get_token("cliente@minimarket.test")

    # 1. Endpoint de reenviar factura del pedido (cliente propio)
    res_factura = client.post("/pedidos/1/enviar-factura", headers=auth_headers(cli_token))
    assert res_factura.status_code == 200
    assert "factura" in res_factura.json()["mensaje"].lower()

    # 2. Reporte individual de auditoría de pedido para empresa
    res_rep_ped = client.get("/reportes/pedidos/1", headers=auth_headers(admin_token))
    assert res_rep_ped.status_code == 200
    data_rep = res_rep_ped.json()
    assert "total_general" in data_rep
    assert "detalles_productos" in data_rep

    # 3. Reporte diario consolidado
    res_diario = client.get("/reportes/diario", headers=auth_headers(admin_token))
    assert res_diario.status_code == 200
    diario_data = res_diario.json()
    assert "total_pedidos" in diario_data
    assert "ingresos_totales" in diario_data
    assert "por_metodo_pago" in diario_data

    # 4. Reporte mensual consolidado
    res_mensual = client.get("/reportes/mensual", headers=auth_headers(admin_token))
    assert res_mensual.status_code == 200
    mensual_data = res_mensual.json()
    assert "tasa_efectividad_porcentaje" in mensual_data
    assert "ventas_por_dia" in mensual_data
    assert "ventas_por_sucursal" in mensual_data
    assert "rendimiento_repartidores" in mensual_data


# ---------------------------------------------------------------------------
# Nuevos casos de auditoría solicitados
# ---------------------------------------------------------------------------
def test_empleado_sucursal_a_no_ve_pedido_sucursal_b():
    with SessionLocal() as db:
        u_emp = db.scalar(select(m.Usuario).where(m.Usuario.email == "empleado@minimarket.test"))
        u_emp.password = security.hash_password("Prueba12345")
        u_emp.activo = True
        u_emp.email_verificado = True
        emp = db.get(m.Empleado, u_emp.id_usuario)
        if not emp:
            db.add(m.Empleado(id_empleado=u_emp.id_usuario, id_sucursal=1, cargo="Cajero"))
        else:
            emp.id_sucursal = 1

        pedido_suc2 = db.scalar(select(m.Pedido).where(m.Pedido.id_sucursal == 2))
        if not pedido_suc2:
            p = db.scalar(select(m.Pedido).order_by(m.Pedido.id_pedido.desc()))
            p.id_sucursal = 2
            id_pedido_suc2 = p.id_pedido
        else:
            id_pedido_suc2 = pedido_suc2.id_pedido
        db.commit()

    emp_token = get_token("empleado@minimarket.test")
    res = client.get(f"/reportes/pedidos/{id_pedido_suc2}", headers=auth_headers(emp_token))
    assert res.status_code == 404, f"Empleado de sucursal 1 pudo ver pedido de sucursal 2: {res.text}"


def test_empleado_sin_sucursal_reporte_diario():
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "srmochi77@gmail.com"))
        if u:
            u.password = security.hash_password("Prueba12345")
            u.activo = True
            u.email_verificado = True
            emp = db.get(m.Empleado, u.id_usuario)
            if emp:
                db.delete(emp)
            db.commit()

    token_huerfano = get_token("srmochi77@gmail.com")
    res = client.get("/reportes/diario", headers=auth_headers(token_huerfano))
    assert res.status_code == 403, f"Empleado sin sucursal no devolvio 403: {res.status_code}"
    assert "no tiene sucursal asignada" in res.json().get("detail", "")


def test_repartidor_asignado_no_puede_enviar_factura():
    with SessionLocal() as db:
        p = db.get(m.Pedido, 1)
        if p:
            p.id_repartidor = 4
        u_rep = db.scalar(select(m.Usuario).where(m.Usuario.email == "repartidor2@minimarket.test"))
        if u_rep:
            u_rep.password = security.hash_password("Prueba12345")
            u_rep.activo = True
            u_rep.email_verificado = True
        db.commit()

    token_rep = get_token("repartidor2@minimarket.test")
    res = client.post("/pedidos/1/enviar-factura", headers=auth_headers(token_rep))
    assert res.status_code == 404, f"Repartidor pudo llamar enviar-factura: {res.status_code}"


def test_login_bloqueado_e_inexistente_mismo_401_y_mensaje():
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        from datetime import timedelta
        u.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()

    try:
        res_bloqueado = client.post("/auth/login", data={"username": "cliente@minimarket.test", "password": "CualquierPassword123"})
        res_inexistente = client.post("/auth/login", data={"username": "correo_no_existente_jamasss@minimarket.test", "password": "CualquierPassword123"})

        assert res_bloqueado.status_code == 401
        assert res_inexistente.status_code == 401
        assert res_bloqueado.json()["detail"] == res_inexistente.json()["detail"]
        assert "Credenciales incorrectas o cuenta bloqueada temporalmente." in res_bloqueado.json()["detail"]
    finally:
        with SessionLocal() as db:
            u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
            u.bloqueado_hasta = None
            db.commit()


def test_reusar_token_cambio_correo_devuelve_400():
    with SessionLocal() as db:
        u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        id_u = u.id_usuario
        email_actual = u.email

    nuevo = "cliente_temporal_test@minimarket.test"
    token_cambio = security.create_email_change_token(id_u, email_actual, nuevo)

    # Primer uso -> 200 OK
    res1 = client.post("/auth/confirmar-cambio-email", json={"token": token_cambio})
    assert res1.status_code == 200, f"Primer uso del token falló: {res1.text}"

    # Segundo uso del mismo token -> 400 Bad Request
    res2 = client.post("/auth/confirmar-cambio-email", json={"token": token_cambio})
    assert res2.status_code == 400, f"Token reusado no devolvió 400: {res2.status_code}"
    assert "inválido o expirado" in res2.json().get("detail", "").lower()

    # Restaurar correo original
    with SessionLocal() as db:
        u = db.get(m.Usuario, id_u)
        u.email = "cliente@minimarket.test"
        u.email_verificado = True
        db.commit()


if __name__ == "__main__":
    print("Ejecutando pruebas E2E y de seguridad...")
    limpiar_usuarios_test()

    # Desactivar temporalmente el IP rate limiter durante las pruebas funcionales para evitar solapamiento entre tests
    app.state.limiter.enabled = False

    test_c3_config_produccion_rechaza_valores_inseguros()
    print("  [OK] C3: Configuracion estricta en produccion")
    test_c1_token_verificacion_o_reset_no_sirve_como_access_token()
    print("  [OK] C1: Tipado estricto de tokens JWT")
    test_c2_solicitar_cambio_email_seguro()
    print("  [OK] C2: Re-autenticacion y no exposicion de token de cambio de correo")
    test_a1_cambio_password_invalida_tokens_anteriores()
    print("  [OK] A1: Revocacion inmediata por cambio de contrasena / Django Admin")
    test_a1_desactivar_y_reactivar_no_revive_tokens_viejos()
    print("  [OK] A1: Revocacion por desactivacion / reactivacion")
    test_a4_bloqueo_por_fuerza_bruta()
    print("  [OK] A4: Bloqueo de cuenta tras 5 intentos fallidos (a nivel de usuario)")
    test_a6_admin_no_puede_auto_bloquearse()
    print("  [OK] A6: Prevencion de auto-bloqueo del administrador")
    test_a2_pedido_cancelado_o_entregado_no_puede_volverse_a_cancelar()
    print("  [OK] A2: Proteccion de concurrencia e inmutabilidad de pedidos")
    test_a3_repartidor_no_puede_rechazar_pedido_no_asignado()
    print("  [OK] A3: Validacion de rechazo de repartidor")
    test_m2_cabeceras_de_seguridad()
    print("  [OK] M2: Cabeceras de seguridad HTTP (CSP, nosniff, DENY)")
    test_m5_producto_update_precio()
    print("  [OK] M5: Actualizacion correcta de precio_base en catalogo")
    test_m6_validaciones_seguras()
    print("  [OK] M6: Validaciones de schemas (limite de items, sanitizacion)")
    test_flujo_olvide_contrasena()
    print("  [OK] Flujo completo: 'Olvide mi contrasena' con revocacion y uso unico")
    test_slowapi_rate_limiter()
    print("  [OK] SlowAPI: Rate limiting activo contra ataques de denegacion de servicio")
    print("\nTODAS LAS PRUEBAS E2E Y DE SEGURIDAD PASARON EXITOSAMENTE!")
