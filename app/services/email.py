import html
import logging
import smtplib
import ssl
from decimal import Decimal
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger(__name__)


def _remitente() -> str:
    correo = (settings.smtp_from_email or settings.smtp_user).strip()
    return f"MiniMarket <{correo}>"


def _formatear_vigencia(minutos: int) -> str:
    if minutos >= 1440 and minutos % 1440 == 0:
        dias = minutos // 1440
        return "1 día" if dias == 1 else f"{dias} días"
    if minutos >= 60 and minutos % 60 == 0:
        horas = minutos // 60
        return "1 hora" if horas == 1 else f"{horas} horas"
    return "1 minuto" if minutos == 1 else f"{minutos} minutos"


def _envolver_email_minimarket(etiqueta: str, contenido_html: str) -> str:
    etiqueta_segura = html.escape(etiqueta)
    return f"""<!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{etiqueta_segura} - MiniMarket</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #fbf8f3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1c1917; line-height: 1.6;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fbf8f3; padding: 32px 12px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 560px; background-color: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #f1e5d8; border-top: 4px solid #ea580c;">
                        <!-- Header MiniMarket -->
                        <tr>
                            <td style="background-color: #fff7ed; padding: 22px 28px; text-align: center; border-bottom: 1px solid #f5ebe0;">
                                <div style="font-size: 25px; font-weight: 800; letter-spacing: -0.5px; line-height: 1.15;">
                                    <span style="color: #ea580c;">Mini</span><span style="color: #3f6212;">Market</span>
                                </div>
                                <div style="color: #65a30d; font-size: 12.5px; font-weight: 600; margin-top: 4px;">
                                    Ahorra tiempo y dinero
                                </div>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding: 30px 28px; text-align: left;">
                                <div style="margin-bottom: 14px;">
                                    <span style="display: inline-block; background-color: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; font-size: 11px; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase; padding: 4px 12px; border-radius: 999px;">
                                        {etiqueta_segura}
                                    </span>
                                </div>
                                {contenido_html}
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #fbf8f3; padding: 16px 28px; text-align: center; border-top: 1px solid #f5ebe0;">
                                <p style="color: #78716c; font-size: 12px; margin: 0;">
                                    MiniMarket &middot; Frescura y ahorro hasta tu puerta
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>"""


def _enviar_email(msg: EmailMessage, destinatario: str) -> bool:
    """Envía un correo electrónico utilizando SMTP (SSL en puerto 465 o STARTTLS en puerto 587)."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "[EMAIL] No se han configurado credenciales SMTP (smtp_user o smtp_password). "
            f"No se envió correo a {destinatario}."
        )
        return False

    try:
        # Intentar con certifi si está disponible para evitar fallos de certificados raíz en Windows Server
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            context = ssl.create_default_context()

        def _conectar(ssl_ctx):
            if settings.smtp_port == 587:
                srv = smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=15)
                srv.ehlo()
                srv.starttls(context=ssl_ctx)
                srv.ehlo()
                return srv
            return smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port, context=ssl_ctx, timeout=15)

        try:
            smtp = _conectar(context)
        except ssl.SSLCertVerificationError:
            # Fallback en Windows Server cuando el almacén de CA local no está presente
            context_fallback = ssl.create_default_context()
            context_fallback.check_hostname = False
            context_fallback.verify_mode = ssl.CERT_NONE
            smtp = _conectar(context_fallback)

        with smtp:
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info(f"[EMAIL] Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] No se pudo enviar el correo a {destinatario}: {e}")
        return False


def enviar_correo_verificacion_registro(destinatario: str, nombre_usuario: str, token: str) -> bool:
    """
    Envía el correo de verificación de cuenta recién registrada con enlace de un solo clic.
    """
    nombre_seguro = html.escape(nombre_usuario)
    base_url = settings.api_base_url.rstrip("/")
    enlace_verificacion = f"{base_url}/auth/verificar-correo?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Verifica tu cuenta - MiniMarket"
    msg["From"] = _remitente()
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"¡Gracias por unirte a MiniMarket! Para activar tu cuenta, por favor verifica tu correo electrónico haciendo clic en el siguiente enlace:\n\n"
        f"{enlace_verificacion}\n\n"
        f"Este enlace expirará en {settings.email_verification_token_expire_hours} horas. Si no realizaste este registro, ignora este mensaje."
    )

    body_html = f"""
        <h2 style="color: #1c1917; margin: 0 0 12px 0; font-size: 21px; font-weight: 800;">¡Hola, {nombre_seguro}!</h2>
        <p style="color: #57534e; font-size: 15px; margin: 0 0 24px 0;">
            Gracias por registrarte en <strong>MiniMarket</strong>. Para completar la creación de tu cuenta y empezar a realizar pedidos, confirma tu dirección de correo electrónico:
        </p>

        <div style="text-align: center; margin: 28px 0;">
            <a href="{enlace_verificacion}" style="background-color: #ea580c; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-size: 15px; font-weight: 700; display: inline-block;">
                Verificar mi Correo Electrónico
            </a>
        </div>

        <div style="background-color: #fbf8f3; border: 1px solid #f1e5d8; border-radius: 10px; padding: 12px 14px; margin-top: 22px; text-align: center;">
            <p style="color: #78716c; font-size: 12px; margin: 0 0 6px 0;">
                Si el botón no funciona, copia y pega este enlace en tu navegador:
            </p>
            <a href="{enlace_verificacion}" style="color: #c2410c; word-break: break-all; font-size: 11px; text-decoration: underline;">{enlace_verificacion}</a>
        </div>

        <p style="color: #78716c; font-size: 12px; margin: 20px 0 0 0; text-align: center;">
            Este enlace expirará en {settings.email_verification_token_expire_hours} horas. Si no solicitaste esta cuenta, puedes ignorar este correo de forma segura.
        </p>
    """
    msg.add_alternative(_envolver_email_minimarket("Verificación de Cuenta", body_html), subtype="html")
    return _enviar_email(msg, destinatario)


def enviar_correo_cambio_email(destinatario: str, nombre_usuario: str, token: str) -> bool:
    """Envía el correo de confirmación de cambio de correo electrónico."""
    nombre_seguro = html.escape(nombre_usuario)
    msg = EmailMessage()
    msg["Subject"] = "Confirmación de Cambio de Correo - MiniMarket"
    msg["From"] = _remitente()
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Has solicitado cambiar tu correo en MiniMarket.\n"
        f"Tu código de verificación es:\n\n{token}\n\n"
        f"Este código es válido por 15 minutos."
    )

    body_html = f"""
        <h2 style="color: #1c1917; margin: 0 0 12px 0; font-size: 20px; font-weight: 800;">Confirmación de Nuevo Correo</h2>
        <p style="color: #57534e; font-size: 15px; margin: 0 0 14px 0;">Hola, <strong>{nombre_seguro}</strong>:</p>
        <p style="color: #57534e; font-size: 15px; margin: 0 0 18px 0;">
            Has solicitado asociar esta dirección de correo a tu cuenta de <strong>MiniMarket</strong>. Ingresa el siguiente código en la aplicación para confirmar el cambio:
        </p>
        <div style="background-color: #fff7ed; padding: 14px; text-align: center; font-family: monospace; font-size: 13px; font-weight: 700; color: #9a3412; border: 1px dashed #fdba74; border-radius: 10px; margin: 18px 0; word-break: break-all;">
            {html.escape(token)}
        </div>
        <p style="font-size: 12px; color: #78716c; margin: 16px 0 0 0; text-align: center;">
            Este código expira en 15 minutos. Si no realizaste esta solicitud, puedes ignorar este mensaje.
        </p>
    """
    msg.add_alternative(_envolver_email_minimarket("Cambio de Correo", body_html), subtype="html")
    return _enviar_email(msg, destinatario)


def enviar_correo_reset_password(destinatario: str, nombre_usuario: str, token: str) -> bool:
    """Envía el correo con enlace seguro para restablecer la contraseña olvidada."""
    nombre_seguro = html.escape(nombre_usuario)
    base_url = settings.api_base_url.rstrip("/")
    enlace_reset = f"{base_url}/auth/restablecer-contrasena?token={token}"
    vigencia_texto = _formatear_vigencia(settings.password_reset_token_expire_minutes)

    msg = EmailMessage()
    msg["Subject"] = "Restablece tu contraseña - MiniMarket"
    msg["From"] = _remitente()
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña en MiniMarket.\n"
        f"Haz clic en el siguiente enlace para crear una nueva contraseña:\n\n"
        f"{enlace_reset}\n\n"
        f"Este enlace expira en {vigencia_texto}.\n"
        f"Si no solicitaste este cambio, puedes ignorar este correo de forma segura."
    )

    body_html = f"""
        <h2 style="color: #1c1917; margin: 0 0 12px 0; font-size: 21px; font-weight: 800;">Recuperación de Contraseña</h2>
        <p style="color: #57534e; font-size: 15px; margin: 0 0 10px 0;">Hola, <strong>{nombre_seguro}</strong>:</p>
        <p style="color: #57534e; font-size: 15px; margin: 0 0 24px 0;">
            Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>MiniMarket</strong>. Haz clic en el botón de abajo para definir una nueva:
        </p>

        <div style="text-align: center; margin: 28px 0;">
            <a href="{enlace_reset}" style="background-color: #ea580c; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-size: 15px; font-weight: 700; display: inline-block;">
                Restablecer mi Contraseña
            </a>
        </div>

        <div style="background-color: #fbf8f3; border: 1px solid #f1e5d8; border-radius: 10px; padding: 12px 14px; margin-top: 22px; text-align: center;">
            <p style="color: #78716c; font-size: 12px; margin: 0 0 6px 0;">
                ¿El botón no responde? Copia y pega este enlace en tu navegador:
            </p>
            <a href="{enlace_reset}" style="color: #c2410c; word-break: break-all; font-size: 11px; text-decoration: underline;">{enlace_reset}</a>
        </div>

        <p style="color: #78716c; font-size: 12px; margin: 20px 0 0 0; text-align: center;">
            Este enlace expirará en <strong>{vigencia_texto}</strong>. Si no fuiste tú, tu cuenta sigue segura y no necesitas hacer nada.
        </p>
    """
    msg.add_alternative(_envolver_email_minimarket("Seguridad de Cuenta", body_html), subtype="html")
    return _enviar_email(msg, destinatario)


def enviar_aviso_seguridad(destinatario: str, nombre_usuario: str, accion: str) -> bool:
    """Notifica al usuario sobre una acción de seguridad relevante en su cuenta."""
    nombre_seguro = html.escape(nombre_usuario)
    accion_segura = html.escape(accion)

    msg = EmailMessage()
    msg["Subject"] = "Alerta de Seguridad - MiniMarket"
    msg["From"] = _remitente()
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Te informamos de una acción reciente en tu cuenta de MiniMarket: {accion}\n\n"
        f"Si reconoces esta actividad, no necesitas hacer nada.\n"
        f"Si NO fuiste tú, por favor ponte en contacto con soporte de inmediato."
    )

    body_html = f"""
        <h2 style="color: #b91c1c; margin: 0 0 12px 0; font-size: 20px; font-weight: 800;">Aviso de Seguridad</h2>
        <p style="color: #57534e; font-size: 15px; margin: 0 0 10px 0;">Hola, <strong>{nombre_seguro}</strong>:</p>
        <p style="color: #57534e; font-size: 15px; margin: 0 0 16px 0;">Se ha registrado la siguiente actividad en tu cuenta:</p>
        <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; border-radius: 6px; padding: 14px; margin: 16px 0; color: #991b1b; font-weight: 600; font-size: 14px;">
            {accion_segura}
        </div>
        <p style="font-size: 13px; color: #78716c; margin: 18px 0 0 0;">
            Si realizaste esta acción, puedes ignorar este mensaje.<br/>
            Si no reconoces esta actividad, por favor comunícate de inmediato con nuestro soporte.
        </p>
    """
    msg.add_alternative(_envolver_email_minimarket("Alerta de Seguridad", body_html), subtype="html")
    return _enviar_email(msg, destinatario)


def enviar_factura_pedido(destinatario: str, nombre_usuario: str, datos: dict) -> bool:
    """Envía un ticket / factura detallada con el desglose completo del pedido a partir de un diccionario desacoplado."""
    nombre_seguro = html.escape(nombre_usuario)
    id_pedido = datos.get("id_pedido", 0)
    ticket_num = f"#PED-{id_pedido:06d}"

    fecha_val = datos.get("fecha")
    fecha_str = fecha_val.strftime("%d/%m/%Y %H:%M") if hasattr(fecha_val, "strftime") else str(fecha_val or "Hoy")
    metodo_pago = html.escape(str(datos.get("metodo_pago", "")))
    estado_pago = html.escape(str(datos.get("estado_pago", "")))
    tipo_entrega = html.escape(str(datos.get("tipo_entrega", "")))
    envio = Decimal(str(datos.get("costo_envio") or "0.00"))
    total_guardado = Decimal(str(datos.get("total") or "0.00"))

    filas_html = ""
    filas_texto = ""
    subtotal_prod = Decimal("0.00")

    for nom, cant, p_unit in datos.get("lineas", []):
        nom_prod = html.escape(str(nom))
        cantidad = int(cant)
        precio_u = Decimal(str(p_unit))
        sub = cantidad * precio_u
        subtotal_prod += sub

        filas_html += f"""
        <tr style="border-bottom: 1px solid #f5ebe0;">
            <td style="padding: 10px 8px; font-size: 13.5px; color: #1c1917;">{nom_prod}</td>
            <td style="padding: 10px 8px; font-size: 13.5px; text-align: center; color: #57534e;">{cantidad}</td>
            <td style="padding: 10px 8px; font-size: 13.5px; text-align: right; color: #57534e;">${precio_u:.2f}</td>
            <td style="padding: 10px 8px; font-size: 13.5px; text-align: right; font-weight: 700; color: #1c1917;">${sub:.2f}</td>
        </tr>
        """
        filas_texto += f"- {nom_prod} x{cantidad} @ ${precio_u:.2f} = ${sub:.2f}\n"

    total = total_guardado if total_guardado > Decimal("0.00") else (subtotal_prod + envio)

    msg = EmailMessage()
    msg["Subject"] = f"Comprobante de Compra {ticket_num} - MiniMarket"
    msg["From"] = _remitente()
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Gracias por tu compra en MiniMarket.\n\n"
        f"Comprobante: {ticket_num}\n"
        f"Fecha: {fecha_str}\n"
        f"Método de Pago: {metodo_pago} ({estado_pago})\n\n"
        f"DETALLE DE PRODUCTOS:\n"
        f"{filas_texto}\n"
        f"Subtotal: ${subtotal_prod:.2f}\n"
        f"Costo de Envío: ${envio:.2f}\n"
        f"TOTAL: ${total:.2f}\n\n"
        f"Si tienes alguna duda o tu pedido presenta inconvenientes, comunícate con nosotros."
    )

    body_html = f"""
        <h2 style="color: #1c1917; margin: 0 0 6px 0; font-size: 20px; font-weight: 800;">Comprobante de Compra</h2>
        <p style="color: #57534e; font-size: 13.5px; margin: 0 0 18px 0;">Gracias por comprar en MiniMarket, <strong>{nombre_seguro}</strong>.</p>

        <table width="100%" style="margin-bottom: 18px; font-size: 13px; color: #57534e; background-color: #fbf8f3; border: 1px solid #f1e5d8; border-radius: 10px; padding: 10px 14px;">
            <tr>
                <td style="padding: 3px 0;"><strong>N.º de Orden:</strong> <span style="color: #ea580c; font-weight: 700;">{ticket_num}</span></td>
                <td style="padding: 3px 0; text-align: right;"><strong>Fecha:</strong> {fecha_str}</td>
            </tr>
            <tr>
                <td style="padding: 3px 0;"><strong>Entrega:</strong> {tipo_entrega}</td>
                <td style="padding: 3px 0; text-align: right;"><strong>Pago:</strong> {metodo_pago}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding: 3px 0;"><strong>Estado del Pago:</strong> <span style="color: #15803d; font-weight: 700;">{estado_pago}</span></td>
            </tr>
        </table>

        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 18px; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #fff7ed; text-transform: uppercase; font-size: 11px; color: #c2410c; letter-spacing: 0.5px;">
                    <th style="padding: 9px 8px; text-align: left;">Producto</th>
                    <th style="padding: 9px 8px; text-align: center;">Cant.</th>
                    <th style="padding: 9px 8px; text-align: right;">Precio</th>
                    <th style="padding: 9px 8px; text-align: right;">Subtotal</th>
                </tr>
            </thead>
            <tbody>
                {filas_html}
            </tbody>
        </table>

        <div style="background-color: #fbf8f3; border: 1px solid #f1e5d8; border-radius: 10px; padding: 14px 16px; margin-bottom: 16px;">
            <table width="100%" style="font-size: 14px; color: #44403c;">
                <tr>
                    <td style="padding: 2px 0;">Subtotal Productos:</td>
                    <td style="padding: 2px 0; text-align: right;">${subtotal_prod:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 2px 0;">Costo de Envío:</td>
                    <td style="padding: 2px 0; text-align: right;">${envio:.2f}</td>
                </tr>
                <tr style="font-size: 17px; font-weight: 800; color: #1c1917; border-top: 1px solid #e7ddd3;">
                    <td style="padding-top: 10px;">TOTAL:</td>
                    <td style="padding-top: 10px; text-align: right; color: #ea580c;">${total:.2f}</td>
                </tr>
            </table>
        </div>

        <p style="color: #78716c; font-size: 12px; text-align: center; margin: 0;">
            Conserva este comprobante para cualquier seguimiento de tu entrega.
        </p>
    """
    msg.add_alternative(_envolver_email_minimarket("Ticket de Compra", body_html), subtype="html")
    return _enviar_email(msg, destinatario)
