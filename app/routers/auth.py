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


def _html_verificacion_exitosa(nombre: str) -> str:
    nombre_seguro = html.escape(nombre)
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
                color: #475569;
                font-size: 15px;
                line-height: 1.6;
                margin: 0 0 24px;
            }}
            .badge {{
                display: inline-block;
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                color: #334155;
                font-size: 13px;
                padding: 6px 14px;
                border-radius: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon-circle">✓</div>
            <h1>¡Correo Verificado!</h1>
            <p>Hola <strong>{nombre_seguro}</strong>, tu dirección de correo electrónico ha sido confirmada exitosamente. Tu cuenta ya está activa para realizar pedidos.</p>
            <div class="badge">Ya puedes iniciar sesión desde tu aplicación</div>
        </div>
    </body>
    </html>
    """


def _html_verificacion_fallida(motivo: str) -> str:
    motivo_seguro = html.escape(motivo)
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enlace Inválido - Minimarket</title>
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
            <p>{motivo_seguro}</p>
            <div class="note">Puedes solicitar un nuevo enlace desde la aplicación o comunicarte con soporte.</div>
        </div>
    </body>
    </html>
    """


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


@router.post("/reenviar-verificacion", response_model=MensajeRespuesta)
@limiter.limit("5/hour")
def reenviar_verificacion(
    request: Request,
    data: ReenviarVerificacionIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Reenvía el correo de verificación con límite de frecuencia (cooldown) y protección contra enumeración.
    """
    email = str(data.email).lower()
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == email))

    if usuario is None:
        return MensajeRespuesta(
            mensaje="Si el correo ingresado se encuentra registrado y pendiente de verificación, se enviará un nuevo enlace."
        )

    if usuario.email_verificado:
        return MensajeRespuesta(
            mensaje="Este correo electrónico ya ha sido verificado. Puedes iniciar sesión.",
            verificado=True,
        )

    # Cooldown anti-spam (mínimo 60 segundos entre reenvíos)
    if usuario.ultimo_correo_en:
        segundos = (datetime.now(timezone.utc) - usuario.ultimo_correo_en).total_seconds()
        if segundos < 60:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Por favor espera {int(60 - segundos)} segundos antes de solicitar otro correo.",
            )

    token = create_email_verification_token(usuario.id_usuario, usuario.email)
    usuario.ultimo_correo_en = datetime.now(timezone.utc)
    db.commit()

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
@limiter.limit("10/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Inicio de sesión protegido contra fuerza bruta con bloqueo temporal (15 min tras 5 intentos)
    y mitigación de ataques de tiempo para usuarios inexistentes.
    """
    ahora = datetime.now(timezone.utc)
    usuario = db.scalar(select(m.Usuario).where(func.lower(m.Usuario.email) == form.username.lower()))

    # Protección contra fuerza bruta: verificar si la cuenta está bloqueada temporalmente
    if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
        restantes = int((usuario.bloqueado_hasta - ahora).total_seconds() / 60) + 1
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Cuenta bloqueada temporalmente por demasiados intentos fallidos. Intenta nuevamente en {restantes} minutos.",
        )

    # Si el usuario no existe, ejecutamos verify_password con DUMMY_HASH para mantener tiempo constante
    if usuario is None:
        verify_password(form.password, DUMMY_HASH)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificación de credenciales
    if not verify_password(form.password, usuario.password):
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= 5:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=15)
            usuario.intentos_fallidos = 0
        db.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciales incorrectas",
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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Contraseña incorrecta")

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

    token = create_email_change_token(usuario.id_usuario, nuevo_email)
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

    usuario = db.get(m.Usuario, id_usuario)
    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

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
):
    """
    Retorna el formulario HTML interactivo para ingresar la nueva contraseña desde el navegador.
    """
    token_val = html.escape(token or "")
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Restablecer Contraseña - Minimarket</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f1f5f9;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }}
                .card {{
                    background: #ffffff;
                    padding: 36px 30px;
                    border-radius: 14px;
                    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
                    max-width: 420px;
                    width: 100%;
                    border: 1px solid #e2e8f0;
                }}
                h1 {{
                    font-size: 22px;
                    color: #0f172a;
                    margin: 0 0 8px;
                    text-align: center;
                }}
                p.sub {{
                    color: #64748b;
                    font-size: 14px;
                    margin: 0 0 24px;
                    text-align: center;
                }}
                label {{
                    display: block;
                    font-size: 13px;
                    font-weight: 600;
                    color: #334155;
                    margin-bottom: 6px;
                }}
                input[type="password"], input[type="text"] {{
                    width: 100%;
                    padding: 10px 12px;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    font-size: 14px;
                    box-sizing: border-box;
                    margin-bottom: 16px;
                }}
                input:focus {{
                    outline: none;
                    border-color: #2563eb;
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
                }}
                button {{
                    width: 100%;
                    background-color: #2563eb;
                    color: white;
                    border: none;
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 8px;
                }}
                button:hover {{
                    background-color: #1d4ed8;
                }}
                #msg {{
                    margin-top: 16px;
                    font-size: 13px;
                    text-align: center;
                    padding: 10px;
                    border-radius: 6px;
                    display: none;
                }}
                .success {{ background: #dcfce7; color: #15803d; display: block !important; }}
                .error {{ background: #fee2e2; color: #b91c1c; display: block !important; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Nueva Contraseña</h1>
                <p class="sub">Ingresa tu nueva contraseña para acceder a Minimarket.</p>
                <form id="resetForm">
                    <label>Token de Verificación</label>
                    <input type="text" id="token" value="{token_val}" required placeholder="Pega el token recibido por correo" />

                    <label>Nueva Contraseña (mínimo 8 caracteres)</label>
                    <input type="password" id="pwd1" required minlength="8" maxlength="128" placeholder="••••••••" />

                    <label>Confirmar Contraseña</label>
                    <input type="password" id="pwd2" required minlength="8" maxlength="128" placeholder="••••••••" />

                    <button type="submit" id="btn">Guardar Contraseña</button>
                    <div id="msg"></div>
                </form>
            </div>
            <script>
                document.getElementById('resetForm').addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    const token = document.getElementById('token').value.trim();
                    const p1 = document.getElementById('pwd1').value;
                    const p2 = document.getElementById('pwd2').value;
                    const msg = document.getElementById('msg');
                    const btn = document.getElementById('btn');

                    if (p1 !== p2) {{
                        msg.className = 'error';
                        msg.innerText = 'Las contraseñas no coinciden.';
                        return;
                    }}

                    btn.disabled = true;
                    btn.innerText = 'Guardando...';

                    try {{
                        const res = await fetch('/auth/restablecer-contrasena', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ token: token, password: p1 }})
                        }});
                        const data = await res.json();
                        if (res.ok) {{
                            msg.className = 'success';
                            msg.innerText = data.mensaje || '¡Contraseña actualizada con éxito!';
                            document.getElementById('resetForm').reset();
                        }} else {{
                            msg.className = 'error';
                            msg.innerText = data.detail || 'Ocurrió un error al restablecer la contraseña.';
                        }}
                    }} catch (err) {{
                        msg.className = 'error';
                        msg.innerText = 'Error de conexión con el servidor.';
                    }} finally {{
                        btn.disabled = false;
                        btn.innerText = 'Guardar Contraseña';
                    }}
                }});
            </script>
        </body>
        </html>
        """
    )


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
    usuario = db.get(m.Usuario, id_usuario)
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
