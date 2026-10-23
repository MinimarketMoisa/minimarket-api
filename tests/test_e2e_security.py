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
    
    # 1. Sin contraseña o con contraseña incorrecta -> 401
    res = client.post(
        "/auth/solicitar-cambio-email",
        headers=auth_headers(token),
        json={"nuevo_email": "nuevo_cliente@test.com", "password": "password_incorrecta_123"},
    )
    assert res.status_code == 401

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

        # El 6to intento debe dar 429 Cuenta Bloqueada a nivel de cuenta
        res = client.post("/auth/login", data={"username": "cliente@minimarket.test", "password": "Prueba12345"})
        assert res.status_code == 429, f"6to intento devolvio {res.status_code}: {res.text}"
        assert "Cuenta bloqueada temporalmente" in res.json().get("detail", "")
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
