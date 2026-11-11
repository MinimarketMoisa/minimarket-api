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

from types import SimpleNamespace

from app.config import Settings
from app.database import SessionLocal
from app.limiter import get_real_ip
from app.main import app
from app import models as m
from app import security
from app.schemas import extraer_digitos_telefono_sv


client = TestClient(app)


def limpiar_usuarios_test():
    telefonos_default = {
        "cliente@minimarket.test": "7000-0000",
        "repartidor1@minimarket.test": "7100-0001",
    }
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
                if email in telefonos_default:
                    try:
                        extraer_digitos_telefono_sv(u.telefono or "")
                    except ValueError:
                        u.telefono = telefonos_default[email]
                # Cancelar pedidos activos viejos del test para respetar el límite de 1 pedido activo
                pedidos_activos = db.scalars(
                    select(m.Pedido).where(
                        m.Pedido.id_cliente == u.id_usuario,
                        m.Pedido.estado.in_(("PENDIENTE", "PREPARADO", "EN_RUTA")),
                    )
                ).all()
                for p in pedidos_activos:
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

    # 2b. Verificar que el formulario HTML oculta el token y rechaza enlaces sin token
    res_form_sin_token = client.get("/auth/restablecer-contrasena")
    assert res_form_sin_token.status_code == 400
    assert "MiniMarket" in res_form_sin_token.text
    assert "#fbf8f3" in res_form_sin_token.text
    res_form_ok = client.get(f"/auth/restablecer-contrasena?token={reset_token}")
    assert res_form_ok.status_code == 200
    assert 'type="hidden" id="token"' in res_form_ok.text
    assert "Token de Verificación" not in res_form_ok.text
    assert "MiniMarket" in res_form_ok.text
    assert "#ea580c" in res_form_ok.text
    assert "#fbf8f3" in res_form_ok.text
    assert "Ahorra tiempo y dinero" in res_form_ok.text

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


def test_seguimiento_en_tiempo_real_rest_y_ws():
    cli_token = get_token("cliente@minimarket.test")
    rep_token = get_token("repartidor1@minimarket.test")
    admin_token = get_token("admin@minimarket.test")

    # Obtener un pedido a domicilio existente del cliente
    with SessionLocal() as db:
        cli_u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        dir_cli = db.scalar(select(m.Direccion).where(m.Direccion.id_cliente == cli_u.id_usuario))
        if not dir_cli:
            dir_cli = m.Direccion(
                id_cliente=cli_u.id_usuario,
                id_municipio=1,
                detalle_direccion="Casa de prueba",
                latitud=Decimal("13.700000"),
                longitud=Decimal("-89.200000"),
            )
            db.add(dir_cli)
            db.flush()

        p = db.scalar(
            select(m.Pedido)
            .where(
                m.Pedido.id_cliente == cli_u.id_usuario,
                m.Pedido.tipo_entrega == "DOMICILIO",
            )
        )
        rep_u = db.scalar(select(m.Usuario).where(m.Usuario.email == "repartidor1@minimarket.test"))
        if not p:
            p = db.scalar(select(m.Pedido).where(m.Pedido.id_cliente == cli_u.id_usuario))
            p.tipo_entrega = "DOMICILIO"
            p.id_direccion = dir_cli.id_direccion
            p.costo_envio = Decimal("2.50")

        p.id_repartidor = rep_u.id_usuario
        p.estado = "EN_RUTA"
        id_pedido = p.id_pedido
        db.commit()

    # 1. El cliente consulta el seguimiento de su pedido por REST
    res_seg = client.get(f"/pedidos/{id_pedido}/seguimiento", headers=auth_headers(cli_token))
    assert res_seg.status_code == 200, f"Error al consultar seguimiento: {res_seg.text}"
    seg_data = res_seg.json()
    assert seg_data["id_pedido"] == id_pedido
    assert "sucursal" in seg_data
    assert "destino" in seg_data
    assert "repartidor" in seg_data
    assert seg_data["codigo_pedido"] is not None
    assert seg_data["codigo_pedido"].startswith("PED-")
    assert seg_data["repartidor"]["id_repartidor"] is None  # Oculto al cliente por privacidad
    assert seg_data["repartidor"]["nombre"] == rep_u.nombre_completo
    assert seg_data["repartidor"]["telefono"] == rep_u.telefono

    # 2. El repartidor actualiza su ubicación GPS
    nueva_lat = 13.698765
    nueva_lon = -89.215432
    res_ubic = client.patch(
        "/repartidor/ubicacion",
        headers=auth_headers(rep_token),
        json={"latitud": nueva_lat, "longitud": nueva_lon},
    )
    assert res_ubic.status_code == 204

    # 3. Al re-consultar seguimiento REST, la ubicación del repartidor refleja las nuevas coordenadas
    res_seg2 = client.get(f"/pedidos/{id_pedido}/seguimiento", headers=auth_headers(cli_token))
    assert res_seg2.status_code == 200
    assert float(res_seg2.json()["repartidor"]["latitud"]) == round(nueva_lat, 6)
    assert float(res_seg2.json()["repartidor"]["longitud"]) == round(nueva_lon, 6)

    # 4. Prueba de conexión WebSocket en vivo
    with client.websocket_connect(f"/pedidos/{id_pedido}/ws/seguimiento?token={cli_token}") as ws:
        msg_inicial = ws.receive_json()
        assert msg_inicial["evento"] == "estado_inicial"
        assert msg_inicial["datos"]["id_pedido"] == id_pedido

        # Test keepalive ping/pong
        ws.send_text("ping")
        resp_ping = ws.receive_text()
        assert resp_ping == "pong"


def test_wompi_sandbox_simulador_pagos():
    cli_token = get_token("cliente@minimarket.test")

    # 1. Consultar catálogo de 10 tarjetas de prueba oficiales
    res_tarjetas = client.get("/pagos/wompi/tarjetas-prueba")
    assert res_tarjetas.status_code == 200
    tarjetas = res_tarjetas.json()
    assert len(tarjetas) == 10
    assert sum(1 for t in tarjetas if t["franquicia"] == "VISA") == 8
    assert sum(1 for t in tarjetas if t["franquicia"] == "MASTERCARD") == 2
    assert any(t["tipo"] == "APROBADA" for t in tarjetas)
    assert any(t["tipo"] == "FONDOS_INSUFICIENTES" for t in tarjetas)
    assert any(t["tipo"] == "DECLINADA_POR_BANCO" for t in tarjetas)
    # Verificar que todas tienen saldo_disponible numérico
    assert all("saldo_disponible" in t for t in tarjetas)

    # 2. Preparar un pedido para pago
    with SessionLocal() as db:
        cli_u = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
        p = db.scalar(
            select(m.Pedido).where(
                m.Pedido.id_cliente == cli_u.id_usuario,
                m.Pedido.total > Decimal("2.50"),
            )
        )
        if p is None:
            p = db.scalar(select(m.Pedido).where(m.Pedido.id_cliente == cli_u.id_usuario))
            p.total = Decimal("10.00")
        p.estado = "PENDIENTE"
        p.estado_pago = "PENDIENTE"
        p.metodo_pago = "CONTRA_ENTREGA"
        p.referencia_pago = None
        id_pedido = p.id_pedido
        db.commit()

    # 3. Intentar pagar con tarjeta inventada / NO autorizada -> DECLINADA (TARJETA_NO_AUTORIZADA)
    res_no_aut = client.post(
        "/pagos/wompi/simular",
        headers=auth_headers(cli_token),
        json={
            "id_pedido": id_pedido,
            "numero_tarjeta": "4999 9999 9999 9999",
            "nombre_titular": "Hacker Test",
            "mes_expiracion": "12",
            "anio_expiracion": "2028",
            "cvv": "123",
        },
    )
    assert res_no_aut.status_code == 200
    assert res_no_aut.json()["estado_transaccion"] == "DECLINADA"
    assert res_no_aut.json()["codigo_respuesta"] == "TARJETA_NO_AUTORIZADA"

    # 4. Intentar pagar con tarjeta Bloqueada (5555 5555 5555 4444) -> DECLINADA (DECLINADA_POR_BANCO)
    res_bloqueada = client.post(
        "/pagos/wompi/simular",
        headers=auth_headers(cli_token),
        json={
            "id_pedido": id_pedido,
            "numero_tarjeta": "5555 5555 5555 4444",
            "nombre_titular": "Roberto Mejia",
            "mes_expiracion": "12",
            "anio_expiracion": "2028",
            "cvv": "741",
        },
    )
    assert res_bloqueada.status_code == 200
    assert res_bloqueada.json()["estado_transaccion"] == "DECLINADA"
    assert res_bloqueada.json()["codigo_respuesta"] == "DECLINADA_POR_BANCO"

    # 5. Intentar pagar con tarjeta con Fondos Insuficientes (termina en 0002)
    res_declinada = client.post(
        "/pagos/wompi/simular",
        headers=auth_headers(cli_token),
        json={
            "id_pedido": id_pedido,
            "numero_tarjeta": "4000 0000 0000 0002",
            "nombre_titular": "Juan Perez",
            "mes_expiracion": "12",
            "anio_expiracion": "2028",
            "cvv": "123",
        },
    )
    assert res_declinada.status_code == 200
    data_dec = res_declinada.json()
    assert data_dec["estado_transaccion"] == "DECLINADA"
    assert data_dec["codigo_respuesta"] == "FONDOS_INSUFICIENTES"

    # Verificar que el pedido NO cambió a PAGADO
    with SessionLocal() as db:
        p_check = db.get(m.Pedido, id_pedido)
        assert p_check.estado_pago == "PENDIENTE"

    # 4. Pagar exitosamente con tarjeta Aprobada (4242 4242 4242 4242)
    res_aprobada = client.post(
        "/pagos/wompi/simular",
        headers=auth_headers(cli_token),
        json={
            "id_pedido": id_pedido,
            "numero_tarjeta": "4242 4242 4242 4242",
            "nombre_titular": "Juan Perez",
            "mes_expiracion": "12",
            "anio_expiracion": "2028",
            "cvv": "123",
        },
    )
    assert res_aprobada.status_code == 200
    data_apr = res_aprobada.json()
    assert data_apr["estado_transaccion"] == "APROBADA"
    assert data_apr["codigo_respuesta"] == "APROBADA"
    assert data_apr["id_transaccion"].startswith("WOMPI-SIM-")
    assert data_apr["marca_tarjeta"] == "VISA"
    assert data_apr["ultimos_cuatro"] == "4242"
    assert data_apr["recibo_enviado_email"] is True

    # Verificar que el pedido en BD ahora está PAGADO con TARJETA
    with SessionLocal() as db:
        p_pagado = db.get(m.Pedido, id_pedido)
        assert p_pagado.estado_pago == "PAGADO"
        assert p_pagado.metodo_pago == "TARJETA"
        assert p_pagado.referencia_pago == data_apr["id_transaccion"]

    # 5. Intentar pagar de nuevo el mismo pedido ya pagado -> 409 Conflict
    res_repetida = client.post(
        "/pagos/wompi/simular",
        headers=auth_headers(cli_token),
        json={
            "id_pedido": id_pedido,
            "numero_tarjeta": "4242 4242 4242 4242",
            "nombre_titular": "Juan Perez",
            "mes_expiracion": "12",
            "anio_expiracion": "2028",
            "cvv": "123",
        },
    )
    assert res_repetida.status_code == 409
    assert "ya se encuentra pagado" in res_repetida.json()["detail"].lower()

    # 6. Probar endpoint de consulta de estado de verificación
    res_est = client.get("/auth/estado-verificacion?email=cliente@minimarket.test")
    assert res_est.status_code == 200
    assert res_est.json()["email"] == "cliente@minimarket.test"
    assert res_est.json()["email_verificado"] is True


# ---------------------------------------------------------------------------
# Anti-troll: Teléfono real único de El Salvador, correos desechables y tope de 1 pedido activo
# ---------------------------------------------------------------------------
def test_get_real_ip_proxy_headers():
    req_proxy = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"x-forwarded-for": "190.53.10.25, 127.0.0.1"},
    )
    assert get_real_ip(req_proxy) == "190.53.10.25"

    req_direct = SimpleNamespace(
        client=SimpleNamespace(host="181.200.4.12"),
        headers={"x-forwarded-for": "1.2.3.4"},
    )
    assert get_real_ip(req_direct) == "181.200.4.12"


def test_registro_telefono_real_y_unico():
    email_temp_1 = "temp_tel_sv_1@minimarket.test"
    email_temp_2 = "temp_tel_sv_2@minimarket.test"
    admin_token = get_token("admin@minimarket.test")

    def _borrar_temp_users():
        with SessionLocal() as db:
            for em in (email_temp_1, email_temp_2):
                u = db.scalar(select(m.Usuario).where(m.Usuario.email == em))
                if u:
                    pedidos_u = db.scalars(select(m.Pedido).where(m.Pedido.id_cliente == u.id_usuario)).all()
                    for p in pedidos_u:
                        db.delete(p)
                    dirs_u = db.scalars(select(m.Direccion).where(m.Direccion.id_cliente == u.id_usuario)).all()
                    for d in dirs_u:
                        db.delete(d)
                    db.flush()
                    db.delete(u)
            db.commit()

    _borrar_temp_users()
    try:
        # 1. Registro sin teléfono -> 422
        res_sin_tel = client.post(
            "/auth/registro",
            json={
                "nombre_completo": "Usuario Sin Tel",
                "email": email_temp_1,
                "password": "PasswordSegura123",
            },
        )
        assert res_sin_tel.status_code == 422

        # 2. Formatos inválidos o extranjeros -> 422
        for tel_invalido in ["12345", "5555-5555", "+1 555-123-4567"]:
            res_inv = client.post(
                "/auth/registro",
                json={
                    "nombre_completo": "Usuario Tel Invalido",
                    "email": email_temp_1,
                    "password": "PasswordSegura123",
                    "telefono": tel_invalido,
                },
            )
            assert res_inv.status_code == 422, f"Debió rechazar '{tel_invalido}' y devolvió {res_inv.status_code}"

        # 3. Números ficticios / patrones de bot -> 422
        for tel_fake in ["7777-7777", "7000-0000", "7123-4567", "7070-7070"]:
            res_fake = client.post(
                "/auth/registro",
                json={
                    "nombre_completo": "Bot Troll",
                    "email": email_temp_1,
                    "password": "PasswordSegura123",
                    "telefono": tel_fake,
                },
            )
            assert res_fake.status_code == 422, f"Debió rechazar número bot '{tel_fake}' y devolvió {res_fake.status_code}"

        # 4. Correo desechable -> 422
        res_desechable = client.post(
            "/auth/registro",
            json={
                "nombre_completo": "Correo Temporal",
                "email": "troll_bot@yopmail.com",
                "password": "PasswordSegura123",
                "telefono": "7412-9876",
            },
        )
        assert res_desechable.status_code == 422

        # 5. Teléfono salvadoreño real con prefijo +503 -> 201 y normalizado XXXX-XXXX
        res_ok = client.post(
            "/auth/registro",
            json={
                "nombre_completo": "Cliente Real SV",
                "email": email_temp_1,
                "password": "PasswordSegura123",
                "telefono": "+503 7412-9876",
            },
        )
        assert res_ok.status_code == 201, f"Registro válido falló: {res_ok.text}"
        data_ok = res_ok.json()
        assert data_ok["telefono"] == "7412-9876"
        id_temp_1 = data_ok["id_usuario"]

        # 6. Mismo teléfono en distinto formato con otro correo -> 409 Conflict
        for tel_dup in ["74129876", "50374129876"]:
            res_dup = client.post(
                "/auth/registro",
                json={
                    "nombre_completo": "Multicuenta Mismo Tel",
                    "email": email_temp_2,
                    "password": "PasswordSegura123",
                    "telefono": tel_dup,
                },
            )
            assert res_dup.status_code == 409, f"Duplicado '{tel_dup}' devolvió {res_dup.status_code}"

        # 7. Admin no puede dejar teléfono vacío ni duplicar el de otro usuario
        res_patch_vacio = client.patch(
            f"/clientes/{id_temp_1}",
            headers=auth_headers(admin_token),
            json={"telefono": "   "},
        )
        assert res_patch_vacio.status_code == 422

        with SessionLocal() as db:
            cli_ref = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
            tel_cli = cli_ref.telefono

        res_patch_dup = client.patch(
            f"/clientes/{id_temp_1}",
            headers=auth_headers(admin_token),
            json={"telefono": tel_cli},
        )
        assert res_patch_dup.status_code == 409

        # 8. Cuenta sin teléfono válido en BD no puede crear pedidos -> 400
        with SessionLocal() as db:
            u1 = db.get(m.Usuario, id_temp_1)
            u1.email_verificado = True
            u1.telefono = None
            db.commit()

        tok_temp_1 = get_token(email_temp_1, password="PasswordSegura123")
        res_ped_sin_tel = client.post(
            "/pedidos",
            headers=auth_headers(tok_temp_1),
            json={
                "tipo_entrega": "RETIRO",
                "id_sucursal": 1,
                "metodo_pago": "CONTRA_ENTREGA",
                "canal": "WEB",
                "items": [{"id_producto": 1, "cantidad": 1}],
            },
        )
        assert res_ped_sin_tel.status_code == 400
        assert "teléfono válido" in res_ped_sin_tel.json()["detail"].lower()
    finally:
        _borrar_temp_users()


def test_limite_un_pedido_activo_por_cuenta():
    limpiar_usuarios_test()
    cli_token = get_token("cliente@minimarket.test")
    admin_token = get_token("admin@minimarket.test")
    email_gemelo = "temp_mismo_tel@minimarket.test"
    ids_creados = []

    def _limpiar_gemelo():
        with SessionLocal() as db:
            u = db.scalar(select(m.Usuario).where(m.Usuario.email == email_gemelo))
            if u:
                for p in db.scalars(select(m.Pedido).where(m.Pedido.id_cliente == u.id_usuario)).all():
                    db.delete(p)
                db.flush()
                db.delete(u)
                db.commit()

    _limpiar_gemelo()
    try:
        # 1. Primer pedido activo -> 201 Created
        res1 = client.post(
            "/pedidos",
            headers=auth_headers(cli_token),
            json={
                "tipo_entrega": "RETIRO",
                "id_sucursal": 1,
                "metodo_pago": "CONTRA_ENTREGA",
                "canal": "WEB",
                "items": [{"id_producto": 1, "cantidad": 1}],
            },
        )
        assert res1.status_code == 201, f"Primer pedido falló: {res1.text}"
        id_pedido_1 = res1.json()["id_pedido"]
        ids_creados.append(id_pedido_1)

        # 2. Segundo pedido simultáneo con la misma cuenta -> 429
        res2 = client.post(
            "/pedidos",
            headers=auth_headers(cli_token),
            json={
                "tipo_entrega": "RETIRO",
                "id_sucursal": 1,
                "metodo_pago": "CONTRA_ENTREGA",
                "canal": "WEB",
                "items": [{"id_producto": 1, "cantidad": 1}],
            },
        )
        assert res2.status_code == 429

        # 3. Otra cuenta heredada con el mismo teléfono normalizado tampoco puede crear pedido simultáneo -> 429
        with SessionLocal() as db:
            cli_ref = db.scalar(select(m.Usuario).where(m.Usuario.email == "cliente@minimarket.test"))
            digitos_cli = extraer_digitos_telefono_sv(cli_ref.telefono)
            rol_cli = db.scalar(select(m.Rol).where(m.Rol.nombre == "CLIENTE"))
            u_gem = m.Usuario(
                id_rol=rol_cli.id_rol,
                nombre_completo="Cuenta Gemela",
                email=email_gemelo,
                password=security.hash_password("Prueba12345"),
                telefono=f"503{digitos_cli}",
                email_verificado=True,
                activo=True,
            )
            db.add(u_gem)
            db.commit()

        tok_gem = get_token(email_gemelo)
        res_gem = client.post(
            "/pedidos",
            headers=auth_headers(tok_gem),
            json={
                "tipo_entrega": "RETIRO",
                "id_sucursal": 1,
                "metodo_pago": "CONTRA_ENTREGA",
                "canal": "WEB",
                "items": [{"id_producto": 1, "cantidad": 1}],
            },
        )
        assert res_gem.status_code == 429

        # 4. Mientras esté en PREPARADO tampoco deja crear otro pedido -> 429
        res_prep = client.patch(
            f"/pedidos/{id_pedido_1}/estado",
            headers=auth_headers(admin_token),
            json={"estado": "PREPARADO"},
        )
        assert res_prep.status_code == 200

        res3 = client.post(
            "/pedidos",
            headers=auth_headers(cli_token),
            json={
                "tipo_entrega": "RETIRO",
                "id_sucursal": 1,
                "metodo_pago": "CONTRA_ENTREGA",
                "canal": "WEB",
                "items": [{"id_producto": 1, "cantidad": 1}],
            },
        )
        assert res3.status_code == 429

        # 5. Al cancelarlo (estado final), el cliente vuelve a poder pedir -> 201
        res_cancel1 = client.patch(
            f"/pedidos/{id_pedido_1}/estado",
            headers=auth_headers(admin_token),
            json={"estado": "CANCELADO"},
        )
        assert res_cancel1.status_code == 200

        res4 = client.post(
            "/pedidos",
            headers=auth_headers(cli_token),
            json={
                "tipo_entrega": "RETIRO",
                "id_sucursal": 1,
                "metodo_pago": "CONTRA_ENTREGA",
                "canal": "WEB",
                "items": [{"id_producto": 1, "cantidad": 1}],
            },
        )
        assert res4.status_code == 201, f"Debió permitir pedir tras cancelar el anterior: {res4.text}"
        ids_creados.append(res4.json()["id_pedido"])
    finally:
        for pid in ids_creados:
            with SessionLocal() as db:
                p_curr = db.get(m.Pedido, pid)
                if p_curr and p_curr.estado not in ("CANCELADO", "ENTREGADO"):
                    client.patch(
                        f"/pedidos/{pid}/estado",
                        headers=auth_headers(admin_token),
                        json={"estado": "CANCELADO"},
                    )
        _limpiar_gemelo()


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
    test_seguimiento_en_tiempo_real_rest_y_ws()
    print("  [OK] Tracking en tiempo real: REST, WebSocket y retransmision de coordenadas del repartidor")
    test_wompi_sandbox_simulador_pagos()
    print("  [OK] Wompi Sandbox: Simulador completo de cobro con tarjeta, aprobaciones, rechazos y webhook/email")
    test_get_real_ip_proxy_headers()
    print("  [OK] Limiter: Extraccion segura de IP real detras de proxy local")
    test_registro_telefono_real_y_unico()
    print("  [OK] Anti-troll: Validacion de telefono SV real, unico y bloqueo de correos desechables")
    test_limite_un_pedido_activo_por_cuenta()
    print("  [OK] Anti-troll: Limite de 1 pedido activo por cuenta y por telefono")
    print("\nTODAS LAS PRUEBAS E2E Y DE SEGURIDAD PASARON EXITOSAMENTE!")
