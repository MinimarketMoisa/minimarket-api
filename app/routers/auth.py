import html
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..limiter import limiter
from ..schemas import (
    ConfirmarCambioEmailIn,
    MensajeRespuesta,
    OlvideContrasenaIn,
    ReenviarVerificacionIn,
    RegistroIn,
    RegistroOut,
    RestablecerContrasenaIn,
    SolicitarCambioEmailIn,
    TokenOut,
    UsuarioOut,
    VerificarEmailIn,
    extraer_digitos_telefono_sv,
)
from ..security import (
    DUMMY_HASH,
    create_access_token,
    create_email_change_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_email_change_token,
    decode_email_verification_token,
    decode_password_reset_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from ..services.email import (
    enviar_aviso_seguridad,
    enviar_correo_cambio_email,
    enviar_correo_reset_password,
    enviar_correo_verificacion_registro,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def usuario_out(u: m.Usuario) -> UsuarioOut:
    return UsuarioOut(
        id_usuario=u.id_usuario,
        nombre_completo=u.nombre_completo,
        email=u.email,
        telefono=u.telefono,
        rol=u.rol.nombre,
        activo=u.activo,
        email_verificado=u.email_verificado,
    )


_MINIMARKET_LOGO_HTML = """
<div class="brand">
    <div class="brand-icon" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="none">
            <path d="M9 5.5C9 3.6 10.7 2.2 12.6 2.5C12.3 4.4 10.8 5.7 9 5.5Z" fill="#16a34a"/>
            <path d="M12.5 5.2C13 3.4 14.9 2.3 16.6 3C16 4.7 14.2 5.6 12.5 5.2Z" fill="#22c55e"/>
            <path d="M3 5H5.2L7.3 14.4C7.5 15.3 8.3 16 9.3 16H17.6C18.5 16 19.3 15.4 19.6 14.5L21 8.5H6.2" stroke="#ea580c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="9.5" cy="19.5" r="1.5" fill="#ea580c"/>
            <circle cx="17.5" cy="19.5" r="1.5" fill="#ea580c"/>
        </svg>
    </div>
    <div class="brand-text">
        <div class="brand-name"><span class="mini">Mini</span><span class="market">Market</span></div>
        <div class="brand-tagline">Ahorra tiempo y dinero</div>
    </div>
</div>
"""

_MINIMARKET_PAGE_CSS = """
    * { box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background-color: #fbf8f3;
        background-image: radial-gradient(circle at 50% 0%, #fff7ed 0%, #fbf8f3 65%);
        color: #1c1917;
        margin: 0;
        padding: 24px 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
    }
    .page-wrap {
        width: 100%;
        max-width: 450px;
    }
    .card {
        background: #ffffff;
        padding: 32px 28px;
        border-radius: 20px;
        box-shadow: 0 14px 34px -10px rgba(234, 88, 12, 0.12), 0 4px 14px -2px rgba(28, 25, 23, 0.05);
        border: 1px solid #f1e5d8;
    }
    .brand {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding-bottom: 18px;
        margin-bottom: 22px;
        border-bottom: 1px solid #f5ebe0;
    }
    .brand-icon {
        width: 46px;
        height: 46px;
        border-radius: 14px;
        background: #fff7ed;
        border: 1px solid #fed7aa;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .brand-text {
        text-align: left;
    }
    .brand-name {
        font-size: 21px;
        font-weight: 800;
        letter-spacing: -0.4px;
        line-height: 1.1;
    }
    .brand-name .mini { color: #ea580c; }
    .brand-name .market { color: #3f6212; }
    .brand-tagline {
        font-size: 12px;
        font-weight: 600;
        color: #65a30d;
        margin-top: 2px;
    }
    .pill {
        display: inline-block;
        background-color: #fff7ed;
        color: #c2410c;
        border: 1px solid #fed7aa;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        padding: 4px 12px;
        border-radius: 999px;
        margin-bottom: 12px;
    }
    .center { text-align: center; }
    .icon-circle {
        width: 68px;
        height: 68px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 18px;
        font-size: 32px;
        font-weight: 700;
    }
    .icon-ok { background-color: #dcfce7; color: #16a34a; border: 2px solid #bbf7d0; }
    .icon-err { background-color: #fee2e2; color: #dc2626; border: 2px solid #fecaca; }
    h1 {
        font-size: 23px;
        color: #1c1917;
        margin: 0 0 8px;
        font-weight: 800;
        letter-spacing: -0.3px;
    }
    p.sub {
        color: #57534e;
        font-size: 14px;
        line-height: 1.55;
        margin: 0 0 22px;
    }
    .btn-primary {
        display: inline-block;
        width: 100%;
        background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
        color: #ffffff;
        border: none;
        padding: 13px 18px;
        border-radius: 12px;
        font-size: 15px;
        font-weight: 700;
        text-decoration: none;
        text-align: center;
        cursor: pointer;
        box-shadow: 0 6px 16px rgba(234, 88, 12, 0.25);
        transition: transform 0.12s ease, box-shadow 0.15s ease, background 0.15s ease;
    }
    .btn-primary:hover {
        background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
        box-shadow: 0 8px 20px rgba(234, 88, 12, 0.32);
    }
    .btn-primary:disabled {
        opacity: 0.65;
        cursor: not-allowed;
        box-shadow: none;
    }
    .note-box {
        margin-top: 18px;
        background-color: #fbf8f3;
        border: 1px solid #f1e5d8;
        color: #78716c;
        font-size: 12.5px;
        padding: 10px 14px;
        border-radius: 12px;
        line-height: 1.5;
    }
    .footer-copy {
        text-align: center;
        color: #a8a29e;
        font-size: 12px;
        margin-top: 16px;
    }
"""


def _url_tienda() -> str:
    url = (settings.frontend_reset_url or "").strip()
    if url.startswith("https://") or url.startswith("http://"):
        return html.escape(url, quote=True)
    return "https://minimarket-cliente.duckdns.org"


def _html_verificacion_exitosa(nombre: str) -> str:
    nombre_seguro = html.escape(nombre)
    tienda_url = _url_tienda()
    return (
        """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Correo Verificado - MiniMarket</title>
    <style>__CSS__</style>
</head>
<body>
    <div class="page-wrap">
        <div class="card center">
            __LOGO__
            <div class="icon-circle icon-ok">✓</div>
            <div class="pill">Cuenta Activa</div>
            <h1>¡Correo Verificado!</h1>
            <p class="sub">Hola <strong>__NOMBRE__</strong>, tu dirección de correo electrónico ha sido confirmada exitosamente. Ya puedes realizar pedidos en MiniMarket.</p>
            <a href="__TIENDA__" class="btn-primary">Ir a MiniMarket</a>
            <div class="note-box">Si usas la app móvil o el panel web, ya puedes regresar e iniciar sesión con tu correo.</div>
        </div>
        <div class="footer-copy">MiniMarket · Frescura y ahorro hasta tu puerta</div>
    </div>
</body>
</html>"""
        .replace("__CSS__", _MINIMARKET_PAGE_CSS)
        .replace("__LOGO__", _MINIMARKET_LOGO_HTML)
        .replace("__NOMBRE__", nombre_seguro)
        .replace("__TIENDA__", tienda_url)
    )


def _html_verificacion_fallida(motivo: str) -> str:
    motivo_seguro = html.escape(motivo)
    tienda_url = _url_tienda()
    return (
        """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enlace Inválido - MiniMarket</title>
    <style>__CSS__</style>
</head>
<body>
    <div class="page-wrap">
        <div class="card center">
            __LOGO__
            <div class="icon-circle icon-err">✕</div>
            <div class="pill">Enlace Expirado</div>
            <h1>Enlace No Válido</h1>
            <p class="sub">__MOTIVO__</p>
            <a href="__TIENDA__" class="btn-primary">Volver a MiniMarket</a>
            <div class="note-box">Puedes solicitar un nuevo enlace desde la tienda, la aplicación móvil o comunicarte con soporte.</div>
        </div>
        <div class="footer-copy">MiniMarket · Frescura y ahorro hasta tu puerta</div>
    </div>
</body>
</html>"""
        .replace("__CSS__", _MINIMARKET_PAGE_CSS)
        .replace("__LOGO__", _MINIMARKET_LOGO_HTML)
        .replace("__MOTIVO__", motivo_seguro)
        .replace("__TIENDA__", tienda_url)
    )


@router.post("/registro", response_model=RegistroOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def registro(
    request: Request,
    data: RegistroIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Registra un CLIENTE con estado de email no verificado y envía automáticamente
    un correo con el enlace de verificación a su Gmail.
    """
    email = str(data.email).lower()
    if db.scalar(select(m.Usuario.id_usuario).where(func.lower(m.Usuario.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")

    digitos_tel = extraer_digitos_telefono_sv(data.telefono)
    tel_existe = db.scalar(
        select(m.Usuario.id_usuario).where(
            m.Usuario.telefono.is_not(None),
            func.length(func.regexp_replace(m.Usuario.telefono, r"[^0-9]", "", "g")) >= 8,
            func.right(func.regexp_replace(m.Usuario.telefono, r"[^0-9]", "", "g"), 8) == digitos_tel,
        )
    )
    if tel_existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ese número de teléfono ya está registrado en otra cuenta",
        )

    rol = db.scalar(select(m.Rol).where(m.Rol.nombre == "CLIENTE"))
    if rol is None:
        raise HTTPException(500, "Falta el rol CLIENTE. Ejecuta: python -m app.init_db")

    usuario = m.Usuario(
        id_rol=rol.id_rol,
        nombre_completo=data.nombre_completo,
        email=email,
        password=hash_password(data.password),
        telefono=data.telefono,
        email_verificado=False,
        ultimo_correo_en=datetime.now(timezone.utc),
    )
    db.add(usuario)
    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")

    # Generar token de verificación de correo
    token = create_email_verification_token(usuario.id_usuario, usuario.email)

    # Envío en segundo plano
    background_tasks.add_task(
        enviar_correo_verificacion_registro,
        usuario.email,
        usuario.nombre_completo,
        token,
    )

    return RegistroOut(
        id_usuario=usuario.id_usuario,
        nombre_completo=usuario.nombre_completo,
        email=usuario.email,
        telefono=usuario.telefono,
        rol=rol.nombre,
        email_verificado=False,
        mensaje="Registro exitoso. Se ha enviado un correo a tu Gmail para verificar tu cuenta.",
    )


@router.get("/estado-verificacion")
@limiter.limit("30/minute")
def estado_verificacion(
    request: Request,
    email: str = Query(..., description="Correo electrónico del usuario a consultar"),
    db: Session = Depends(get_db),
):
    """
    (Web y Móvil) Permite al cliente frontend consultar si un correo electrónico ya fue verificado.
    """
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == email.lower().strip()))
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    return {
        "email": usuario.email,
        "email_verificado": usuario.email_verificado,
        "activo": usuario.activo,
    }


@router.get("/verificar-correo")
def verificar_correo_get(
    request: Request,
    token: str = Query(..., description="Token de verificación enviado por correo"),
    db: Session = Depends(get_db),
):
    """
    Endpoint para verificación mediante enlace (por ejemplo, clic directo desde Gmail).
    """
    es_navegador = "text/html" in request.headers.get("accept", "")

    payload = decode_email_verification_token(token)
    if not payload:
        if es_navegador:
            return HTMLResponse(
                content=_html_verificacion_fallida("El enlace de verificación es inválido o ha expirado."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o expirado")

    id_usuario = int(payload["sub"])
    usuario = db.get(m.Usuario, id_usuario)
    if usuario is None:
        if es_navegador:
            return HTMLResponse(
                content=_html_verificacion_fallida("Usuario no encontrado en el sistema."),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    # Verificar que el token pertenezca al correo actual del usuario
    if payload.get("email") != usuario.email.lower():
        if es_navegador:
            return HTMLResponse(
                content=_html_verificacion_fallida("El enlace no coincide con el correo actual de la cuenta."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El token no corresponde al correo actual de la cuenta")

    if not usuario.email_verificado:
        usuario.email_verificado = True
        db.commit()

    if es_navegador:
        return HTMLResponse(
            content=_html_verificacion_exitosa(usuario.nombre_completo),
            status_code=status.HTTP_200_OK,
        )

    return {
        "mensaje": "Correo verificado exitosamente",
        "verificado": True,
    }


@router.post("/verificar-correo", response_model=MensajeRespuesta)
def verificar_correo_post(
    data: VerificarEmailIn,
    db: Session = Depends(get_db),
):
    """
    Endpoint para aplicaciones móviles o frontend que envían el token en JSON.
    """
    payload = decode_email_verification_token(data.token)
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o expirado")

    id_usuario = int(payload["sub"])
    usuario = db.get(m.Usuario, id_usuario)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    if payload.get("email") != usuario.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El token no corresponde al correo actual de la cuenta")

    if not usuario.email_verificado:
        usuario.email_verificado = True
        db.commit()

    return MensajeRespuesta(mensaje="Correo verificado exitosamente", verificado=True)


def _en_cooldown(u: m.Usuario) -> bool:
    if not u.ultimo_correo_en:
        return False
    return (datetime.now(timezone.utc) - u.ultimo_correo_en).total_seconds() < 60


@router.post("/reenviar-verificacion", response_model=MensajeRespuesta)
@limiter.limit("5/hour")
def reenviar_verificacion(
    request: Request,
    data: ReenviarVerificacionIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Reenvía el correo de verificación protegido contra enumeración y con cooldown.
    """
    email = str(data.email).lower()
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == email))

    respuesta = MensajeRespuesta(
        mensaje="Si el correo está registrado y pendiente de verificación, recibirás un nuevo enlace."
    )
    if usuario is None or usuario.email_verificado or not usuario.activo or _en_cooldown(usuario):
        return respuesta

    token = create_email_verification_token(usuario.id_usuario, usuario.email)
    usuario.ultimo_correo_en = datetime.now(timezone.utc)
    db.commit()

    background_tasks.add_task(
        enviar_correo_verificacion_registro,
        usuario.email,
        usuario.nombre_completo,
        token,
    )

    return respuesta


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Inicio de sesión protegido contra fuerza bruta con tiempo constante y bloqueo tras 5 intentos.
    """
    ahora = datetime.now(timezone.utc)
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == form.username.lower()))

    ok = verify_password(form.password[:128], usuario.password if usuario else DUMMY_HASH)
    bloqueado = bool(usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora)

    if usuario is None or bloqueado or not ok:
        if usuario is not None and not bloqueado:
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= 5:
                usuario.bloqueado_hasta, usuario.intentos_fallidos = ahora + timedelta(minutes=15), 0
            db.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciales incorrectas o cuenta bloqueada temporalmente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Restablecer intentos fallidos tras inicio de sesión exitoso
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None

    if not usuario.activo:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Tu cuenta ha sido desactivada. Comunícate con el soporte.",
        )
    if not usuario.email_verificado:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Debes verificar tu correo electrónico antes de iniciar sesión. Por favor revisa tu bandeja de entrada en Gmail o solicita el reenvío del enlace de verificación.",
        )

    usuario.last_login = ahora
    db.commit()

    return TokenOut(
        access_token=create_access_token(usuario),
        id_usuario=usuario.id_usuario,
        rol=usuario.rol.nombre,
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: m.Usuario = Depends(get_current_user)):
    return usuario_out(usuario)


@router.post("/solicitar-cambio-email", response_model=MensajeRespuesta)
@limiter.limit("5/hour")
def solicitar_cambio_email(
    request: Request,
    data: SolicitarCambioEmailIn,
    background_tasks: BackgroundTasks,
    usuario: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Exige la contraseña actual para re-autenticación y envía el token por correo al nuevo email.
    NUNCA devuelve el token en la respuesta.
    """
    if not verify_password(data.password, usuario.password):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Contraseña incorrecta")

    nuevo_email = str(data.nuevo_email).lower()
    if nuevo_email == usuario.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nuevo correo debe ser diferente al actual")

    # Cooldown
    if usuario.ultimo_correo_en:
        segundos = (datetime.now(timezone.utc) - usuario.ultimo_correo_en).total_seconds()
        if segundos < 60:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Por favor espera {int(60 - segundos)} segundos antes de solicitar otro cambio.",
            )

    # Verificar si ya existe otro usuario con ese correo
    existe = db.scalar(
        select(m.Usuario.id_usuario).where(
            func.lower(m.Usuario.email) == nuevo_email,
            m.Usuario.id_usuario != usuario.id_usuario,
        )
    )
    if existe:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado por otro usuario")

    token = create_email_change_token(usuario.id_usuario, usuario.email, nuevo_email)
    usuario.ultimo_correo_en = datetime.now(timezone.utc)
    db.commit()

    background_tasks.add_task(
        enviar_correo_cambio_email,
        nuevo_email,
        usuario.nombre_completo,
        token,
    )

    return MensajeRespuesta(
        mensaje="Se ha enviado un código de confirmación a tu nuevo correo. Ingrésalo para confirmar el cambio."
    )


@router.post("/confirmar-cambio-email", response_model=UsuarioOut)
def confirmar_cambio_email(
    data: ConfirmarCambioEmailIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    payload = decode_email_change_token(data.token)
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o expirado")

    id_usuario = int(payload["sub"])
    nuevo_email = str(payload["nuevo_email"]).lower()

    usuario = db.get(m.Usuario, id_usuario, with_for_update=True)
    if usuario is None or not usuario.activo or usuario.email.lower() != payload.get("actual"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o expirado")

    existe = db.scalar(
        select(m.Usuario.id_usuario).where(
            func.lower(m.Usuario.email) == nuevo_email,
            m.Usuario.id_usuario != id_usuario,
        )
    )
    if existe:
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está en uso")

    email_antiguo = usuario.email
    usuario.email = nuevo_email
    usuario.email_verificado = True
    usuario.token_version += 1  # Revoca todas las sesiones anteriores
    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está en uso")

    # Alerta de seguridad al correo anterior
    background_tasks.add_task(
        enviar_aviso_seguridad,
        email_antiguo,
        usuario.nombre_completo,
        f"Tu dirección de correo fue cambiada exitosamente a {nuevo_email}.",
    )

    return usuario_out(usuario)


# ---- RECUPERACIÓN DE CONTRASEÑA ("OLVIDÉ MI CONTRASEÑA") ----


@router.post("/olvide-contrasena", response_model=MensajeRespuesta)
@limiter.limit("5/hour")
def olvide_contrasena(
    request: Request,
    data: OlvideContrasenaIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Solicita el restablecimiento de contraseña. Protegido contra enumeración de usuarios:
    siempre retorna un mensaje genérico idéntico exista o no la cuenta.
    """
    email = str(data.email).lower()
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == email))

    if usuario and usuario.activo:
        ahora = datetime.now(timezone.utc)
        puede_enviar = True
        if usuario.ultimo_correo_en:
            if (ahora - usuario.ultimo_correo_en).total_seconds() < 60:
                puede_enviar = False

        if puede_enviar:
            token = create_password_reset_token(usuario)
            usuario.ultimo_correo_en = ahora
            db.commit()
            background_tasks.add_task(
                enviar_correo_reset_password,
                usuario.email,
                usuario.nombre_completo,
                token,
            )

    return MensajeRespuesta(
        mensaje="Si el correo ingresado se encuentra registrado, recibirás un enlace para restablecer tu contraseña."
    )


@router.get("/restablecer-contrasena")
def formulario_restablecer_contrasena(
    request: Request,
    token: Optional[str] = Query(None, description="Token de restablecimiento"),
    db: Session = Depends(get_db),
):
    """
    Retorna el formulario HTML interactivo para ingresar la nueva contraseña desde el navegador.
    Mantiene el token oculto al usuario final y valida previamente que el enlace sea válido.
    """
    if not token or not token.strip():
        return HTMLResponse(
            content=_html_verificacion_fallida(
                "El enlace de recuperación está incompleto o es inválido. Por favor solicita uno nuevo desde la app."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    payload = decode_password_reset_token(token.strip())
    if not payload:
        return HTMLResponse(
            content=_html_verificacion_fallida(
                "Este enlace de recuperación ha expirado o es inválido. Por favor solicita uno nuevo."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    id_usuario = int(payload["sub"])
    usuario = db.get(m.Usuario, id_usuario)
    if (
        usuario is None
        or not usuario.activo
        or payload.get("ver") != usuario.token_version
        or not hmac.compare_digest(payload.get("pwd", ""), password_fingerprint(usuario.password))
    ):
        return HTMLResponse(
            content=_html_verificacion_fallida(
                "Este enlace ya fue utilizado o ya no es válido. Solicita uno nuevo si necesitas cambiar tu contraseña."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    token_val = html.escape(token.strip(), quote=True)
    nombre_seguro = html.escape(usuario.nombre_completo)
    tienda_url = _url_tienda()

    form_css = _MINIMARKET_PAGE_CSS + """
    .form-group { margin-bottom: 16px; }
    label {
        display: block;
        font-size: 13px;
        font-weight: 700;
        color: #44403c;
        margin-bottom: 6px;
    }
    .input-wrap {
        position: relative;
        display: flex;
        align-items: center;
    }
    .input-wrap input {
        width: 100%;
        padding: 12px 44px 12px 14px;
        background-color: #fdfcfa;
        border: 1.5px solid #e7ddd3;
        border-radius: 12px;
        font-size: 14.5px;
        color: #1c1917;
        transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
    }
    .input-wrap input:focus {
        outline: none;
        background-color: #ffffff;
        border-color: #f97316;
        box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.15);
    }
    .toggle-eye {
        position: absolute;
        right: 10px;
        background: transparent;
        border: none;
        padding: 6px;
        cursor: pointer;
        color: #78716c;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
    }
    .toggle-eye:hover {
        color: #ea580c;
        background-color: #fff7ed;
    }
    .hints {
        display: flex;
        flex-direction: column;
        gap: 6px;
        background-color: #fbf8f3;
        border: 1px solid #f1e5d8;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 18px;
        font-size: 12.5px;
        color: #78716c;
    }
    .hint-item {
        display: flex;
        align-items: center;
        gap: 8px;
        transition: color 0.15s ease;
    }
    .hint-dot {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background-color: #e7ddd3;
        color: #ffffff;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 800;
        flex-shrink: 0;
        transition: background-color 0.15s ease;
    }
    .hint-item.valid {
        color: #15803d;
        font-weight: 600;
    }
    .hint-item.valid .hint-dot {
        background-color: #16a34a;
    }
    .err-box {
        display: none;
        margin-top: 14px;
        padding: 12px 14px;
        border-radius: 12px;
        font-size: 13.5px;
        line-height: 1.45;
        text-align: center;
        background-color: #fef2f2;
        color: #b91c1c;
        border: 1px solid #fecaca;
    }
    .err-box.show { display: block; }
    .ok-box { display: none; text-align: center; }
    .ok-box.show { display: block; }
    """

    page_html = (
        """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nueva Contraseña - MiniMarket</title>
    <style>__CSS__</style>
</head>
<body>
    <div class="page-wrap">
        <div class="card">
            __LOGO__
            <div id="formSection">
                <div class="center">
                    <div class="pill">Seguridad de Cuenta</div>
                    <h1>Nueva Contraseña</h1>
                    <p class="sub">Hola <strong>__NOMBRE__</strong>, crea una nueva contraseña segura para tu cuenta.</p>
                </div>

                <form id="resetForm" novalidate>
                    <input type="hidden" id="token" value="__TOKEN__" />

                    <div class="form-group">
                        <label for="pwd1">Nueva Contraseña</label>
                        <div class="input-wrap">
                            <input type="password" id="pwd1" autocomplete="new-password" required minlength="8" maxlength="128" placeholder="Mínimo 8 caracteres" />
                            <button type="button" class="toggle-eye" data-target="pwd1" aria-label="Mostrar u ocultar contraseña">
                                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                    <circle cx="12" cy="12" r="3"></circle>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="pwd2">Confirmar Contraseña</label>
                        <div class="input-wrap">
                            <input type="password" id="pwd2" autocomplete="new-password" required minlength="8" maxlength="128" placeholder="Repite tu contraseña" />
                            <button type="button" class="toggle-eye" data-target="pwd2" aria-label="Mostrar u ocultar confirmación">
                                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                    <circle cx="12" cy="12" r="3"></circle>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <div class="hints">
                        <div class="hint-item" id="hintLen">
                            <span class="hint-dot">✓</span>
                            <span>Al menos 8 caracteres</span>
                        </div>
                        <div class="hint-item" id="hintMatch">
                            <span class="hint-dot">✓</span>
                            <span>Ambas contraseñas coinciden</span>
                        </div>
                    </div>

                    <button type="submit" id="btn" class="btn-primary">Guardar Nueva Contraseña</button>
                    <div id="errBox" class="err-box" role="alert"></div>
                </form>
            </div>

            <div id="okSection" class="ok-box">
                <div class="icon-circle icon-ok">✓</div>
                <div class="pill">Listo</div>
                <h1>¡Contraseña Actualizada!</h1>
                <p class="sub" id="okMsg">Tu contraseña ha sido restablecida exitosamente.</p>
                <a href="__TIENDA__" class="btn-primary">Ir a MiniMarket</a>
                <div class="note-box">Si usas la aplicación móvil o el panel administrativo, ya puedes volver e iniciar sesión.</div>
            </div>
        </div>
        <div class="footer-copy">MiniMarket · Frescura y ahorro hasta tu puerta</div>
    </div>

    <script>
        (function () {
            const p1El = document.getElementById('pwd1');
            const p2El = document.getElementById('pwd2');
            const hintLen = document.getElementById('hintLen');
            const hintMatch = document.getElementById('hintMatch');
            const errBox = document.getElementById('errBox');
            const btn = document.getElementById('btn');

            function updateHints() {
                const v1 = p1El.value;
                const v2 = p2El.value;
                hintLen.classList.toggle('valid', v1.length >= 8);
                hintMatch.classList.toggle('valid', v1.length > 0 && v1 === v2);
            }

            p1El.addEventListener('input', updateHints);
            p2El.addEventListener('input', updateHints);

            document.querySelectorAll('.toggle-eye').forEach((toggleBtn) => {
                toggleBtn.addEventListener('click', () => {
                    const input = document.getElementById(toggleBtn.dataset.target);
                    if (!input) return;
                    const isHidden = input.type === 'password';
                    input.type = isHidden ? 'text' : 'password';
                    toggleBtn.style.color = isHidden ? '#ea580c' : '#78716c';
                });
            });

            document.getElementById('resetForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                errBox.classList.remove('show');
                const token = document.getElementById('token').value.trim();
                const p1 = p1El.value;
                const p2 = p2El.value;

                if (p1.length < 8) {
                    errBox.textContent = 'La contraseña debe tener al menos 8 caracteres.';
                    errBox.classList.add('show');
                    p1El.focus();
                    return;
                }
                if (p1 !== p2) {
                    errBox.textContent = 'Las contraseñas no coinciden. Verifica e intenta de nuevo.';
                    errBox.classList.add('show');
                    p2El.focus();
                    return;
                }

                btn.disabled = true;
                btn.textContent = 'Guardando cambios...';

                try {
                    const res = await fetch('/auth/restablecer-contrasena', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ token: token, password: p1 })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        document.getElementById('formSection').style.display = 'none';
                        if (data && data.mensaje) {
                            document.getElementById('okMsg').textContent = data.mensaje;
                        }
                        document.getElementById('okSection').classList.add('show');
                    } else {
                        errBox.textContent = (data && data.detail) || 'Ocurrió un error al restablecer la contraseña.';
                        errBox.classList.add('show');
                        btn.disabled = false;
                        btn.textContent = 'Guardar Nueva Contraseña';
                    }
                } catch (err) {
                    errBox.textContent = 'Error de conexión con el servidor. Inténtalo de nuevo.';
                    errBox.classList.add('show');
                    btn.disabled = false;
                    btn.textContent = 'Guardar Nueva Contraseña';
                }
            });
        })();
    </script>
</body>
</html>"""
        .replace("__CSS__", form_css)
        .replace("__LOGO__", _MINIMARKET_LOGO_HTML)
        .replace("__NOMBRE__", nombre_seguro)
        .replace("__TOKEN__", token_val)
        .replace("__TIENDA__", tienda_url)
    )
    return HTMLResponse(content=page_html)


@router.post("/restablecer-contrasena", response_model=MensajeRespuesta)
@limiter.limit("5/hour")
def restablecer_contrasena(
    request: Request,
    data: RestablecerContrasenaIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Aplica la nueva contraseña utilizando el token de restablecimiento de un solo uso.
    Invalida todas las sesiones activas incrementando token_version.
    """
    payload = decode_password_reset_token(data.token)
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token de restablecimiento inválido o expirado")

    id_usuario = int(payload["sub"])
    usuario = db.get(m.Usuario, id_usuario, with_for_update=True)
    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado o inactivo")

    # Validar que el token no haya sido usado ya (compara token_version y password_fingerprint)
    if payload.get("ver") != usuario.token_version:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Este enlace de restablecimiento ya fue utilizado")

    if not hmac.compare_digest(payload.get("pwd", ""), password_fingerprint(usuario.password)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace de restablecimiento ya no es válido")

    # Actualizar contraseña y revocar todas las sesiones
    usuario.password = hash_password(data.password)
    usuario.token_version += 1
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.commit()

    # Enviar notificación de seguridad
    background_tasks.add_task(
        enviar_aviso_seguridad,
        usuario.email,
        usuario.nombre_completo,
        "La contraseña de tu cuenta ha sido restablecida exitosamente.",
    )

    return MensajeRespuesta(
        mensaje="Tu contraseña ha sido restablecida exitosamente. Ya puedes iniciar sesión con tu nueva contraseña."
    )
