from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..deps import get_current_user
from ..schemas import (
    ConfirmarCambioEmailIn,
    MensajeRespuesta,
    ReenviarVerificacionIn,
    RegistroIn,
    RegistroOut,
    SolicitarCambioEmailIn,
    TokenOut,
    UsuarioOut,
    VerificarEmailIn,
)
from ..security import (
    create_access_token,
    create_email_change_token,
    create_email_verification_token,
    decode_email_change_token,
    decode_email_verification_token,
    hash_password,
    verify_password,
)
from ..services.email import (
    enviar_correo_cambio_email,
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


def _html_verificacion_exitosa(nombre: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Correo Verificado - Minimarket</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #f1f5f9;
                margin: 0;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}
            .card {{
                background: #ffffff;
                padding: 44px 32px;
                border-radius: 16px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
                max-width: 440px;
                text-align: center;
                border: 1px solid #e2e8f0;
                margin: 20px;
            }}
            .icon-circle {{
                width: 72px;
                height: 72px;
                background-color: #dcfce7;
                color: #16a34a;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 36px;
            }}
            h1 {{
                font-size: 24px;
                color: #0f172a;
                margin: 0 0 12px;
                font-weight: 700;
            }}
            p {{
                color: #64748b;
                font-size: 15px;
                line-height: 1.6;
                margin: 0 0 24px;
            }}
            .badge {{
                display: inline-block;
                background: #eff6ff;
                color: #2563eb;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                border: 1px solid #bfdbfe;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon-circle">✓</div>
            <h1>¡Correo Verificado!</h1>
            <p>Hola <strong>{nombre}</strong>, tu dirección de correo ha sido confirmada con éxito. Tu cuenta en <strong>Minimarket</strong> ya está activa.</p>
            <div class="badge">Ya puedes iniciar sesión en la aplicación</div>
        </div>
    </body>
    </html>
    """


def _html_verificacion_fallida(motivo: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error de Verificación - Minimarket</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #f1f5f9;
                margin: 0;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}
            .card {{
                background: #ffffff;
                padding: 44px 32px;
                border-radius: 16px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
                max-width: 440px;
                text-align: center;
                border: 1px solid #e2e8f0;
                margin: 20px;
            }}
            .icon-circle {{
                width: 72px;
                height: 72px;
                background-color: #fee2e2;
                color: #dc2626;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 36px;
            }}
            h1 {{
                font-size: 24px;
                color: #0f172a;
                margin: 0 0 12px;
                font-weight: 700;
            }}
            p {{
                color: #64748b;
                font-size: 15px;
                line-height: 1.6;
                margin: 0 0 24px;
            }}
            .note {{
                color: #94a3b8;
                font-size: 13px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon-circle">✕</div>
            <h1>Enlace No Válido</h1>
            <p>{motivo}</p>
            <div class="note">Puedes solicitar un nuevo enlace desde la aplicación o comunicarte con soporte.</div>
        </div>
    </body>
    </html>
    """


@router.post("/registro", response_model=RegistroOut, status_code=status.HTTP_201_CREATED)
def registro(
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
    )
    db.add(usuario)
    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")

    # Generar token de verificación de correo (validez 24 horas)
    token = create_email_verification_token(usuario.id_usuario, usuario.email)

    # Envío en segundo plano para no demorar la respuesta de la API
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


@router.get("/verificar-correo")
def verificar_correo_get(
    request: Request,
    token: str = Query(..., description="Token de verificación enviado por correo"),
    db: Session = Depends(get_db),
):
    """
    Endpoint para verificación mediante enlace (por ejemplo, clic directo desde Gmail).
    Retorna una interfaz visual en HTML si se accede desde un navegador web,
    o respuesta JSON si el cliente lo requiere explícitamente.
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

    if not usuario.email_verificado:
        usuario.email_verificado = True
        db.commit()

    return MensajeRespuesta(mensaje="Correo verificado exitosamente", verificado=True)


@router.post("/reenviar-verificacion", response_model=MensajeRespuesta)
def reenviar_verificacion(
    data: ReenviarVerificacionIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Reenvía el correo de verificación a un usuario cuyo correo aún no ha sido verificado.
    """
    email = str(data.email).lower()
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == email))

    if usuario is None:
        # Por seguridad no revelamos si existe o no el correo
        return MensajeRespuesta(
            mensaje="Si el correo ingresado se encuentra registrado y pendiente de verificación, se enviará un nuevo enlace."
        )

    if usuario.email_verificado:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Este correo electrónico ya ha sido verificado. Puedes iniciar sesión.",
        )

    token = create_email_verification_token(usuario.id_usuario, usuario.email)
    background_tasks.add_task(
        enviar_correo_verificacion_registro,
        usuario.email,
        usuario.nombre_completo,
        token,
    )

    return MensajeRespuesta(
        mensaje="Se ha enviado un nuevo enlace de verificación a tu correo de Gmail.",
        verificado=False,
    )


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """`username` es el correo electrónico."""
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == form.username.lower()))
    if usuario is None or not verify_password(form.password, usuario.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
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

    usuario.last_login = datetime.now(timezone.utc)
    db.commit()
    return TokenOut(
        access_token=create_access_token(usuario.id_usuario, usuario.rol.nombre),
        id_usuario=usuario.id_usuario, rol=usuario.rol.nombre,
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: m.Usuario = Depends(get_current_user)):
    return usuario_out(usuario)


@router.post("/solicitar-cambio-email")
def solicitar_cambio_email(
    data: SolicitarCambioEmailIn,
    background_tasks: BackgroundTasks,
    usuario: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nuevo_email = str(data.nuevo_email).lower()

    if nuevo_email == usuario.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nuevo correo debe ser diferente al actual")

    # Verificar si ya existe otro usuario con ese correo
    existe = db.scalar(
        select(m.Usuario.id_usuario).where(
            func.lower(m.Usuario.email) == nuevo_email,
            m.Usuario.id_usuario != usuario.id_usuario,
        )
    )
    if existe:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado por otro usuario")

    # Generar token JWT con validez de 15 minutos
    token = create_email_change_token(usuario.id_usuario, nuevo_email)

    # Enviar correo de confirmación al nuevo correo
    background_tasks.add_task(
        enviar_correo_cambio_email,
        nuevo_email,
        usuario.nombre_completo,
        token,
    )

    return {
        "mensaje": "Se ha enviado un código de confirmación a tu nuevo correo.",
        "token_confirmacion": token,
        "instrucciones": "Envía este token a /auth/confirmar-cambio-email para aplicar el cambio."
    }


@router.post("/confirmar-cambio-email", response_model=UsuarioOut)
def confirmar_cambio_email(
    data: ConfirmarCambioEmailIn,
    db: Session = Depends(get_db),
):
    payload = decode_email_change_token(data.token)
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido o expirado")

    id_usuario = int(payload["sub"])
    nuevo_email = str(payload["nuevo_email"]).lower()

    usuario = db.get(m.Usuario, id_usuario)
    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    # Verificar disponibilidad antes de actualizar
    existe = db.scalar(
        select(m.Usuario.id_usuario).where(
            func.lower(m.Usuario.email) == nuevo_email,
            m.Usuario.id_usuario != id_usuario,
        )
    )
    if existe:
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está en uso")

    usuario.email = nuevo_email
    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está en uso")

    return usuario_out(usuario)