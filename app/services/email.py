import html
import logging
import smtplib
import ssl
from decimal import Decimal
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger(__name__)


def _enviar_email(msg: EmailMessage, destinatario: str) -> bool:
    """Envía un correo electrónico utilizando el servidor SMTP SSL con verificación de certificado TLS/SSL."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "[EMAIL] No se han configurado credenciales SMTP (smtp_user o smtp_password). "
            f"No se envió correo a {destinatario}."
        )
        return False

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port, context=context, timeout=15) as smtp:
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info(f"[EMAIL] Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] No se pudo enviar el correo a {destinatario}: {e}")
        return False


def enviar_correo_verificacion_registro(destinatario: str, nombre_usuario: str, token: str) -> bool:
    """
    Envía el correo de verificación de cuenta recién registrada con enlace de un solo clic y código/token.
    """
    nombre_seguro = html.escape(nombre_usuario)
    base_url = settings.api_base_url.rstrip("/")
    enlace_verificacion = f"{base_url}/auth/verificar-correo?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Verifica tu cuenta - Minimarket"
    msg["From"] = f"Minimarket <{settings.smtp_user}>"
    msg["To"] = destinatario

    # Versión texto plano
    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"¡Gracias por unirte a Minimarket! Para activar tu cuenta, por favor verifica tu correo electrónico haciendo clic en el siguiente enlace:\n\n"
        f"{enlace_verificacion}\n\n"
        f"O si utilizas una aplicación móvil, puedes ingresar este token de verificación:\n"
        f"{token}\n\n"
        f"Este enlace expirará en 24 horas. Si no realizaste este registro, ignora este mensaje."
    )

    # Versión HTML moderna y adaptable
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verifica tu cuenta</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #2d3748; line-height: 1.6;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f6f8; padding: 40px 10px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 560px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); overflow: hidden; border: 1px solid #e2e8f0;">
                        <!-- Header -->
                        <tr>
                            <td style="background-color: #1e40af; padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.5px;">Minimarket</h1>
                                <p style="color: #bfdbfe; margin: 6px 0 0 0; font-size: 14px;">Tu supermercado al instante</p>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding: 32px 30px;">
                                <h2 style="color: #1f2937; margin-top: 0; font-size: 20px;">¡Hola, {nombre_seguro}! 👋</h2>
                                <p style="color: #4b5563; font-size: 15px; margin-bottom: 24px;">
                                    Gracias por registrarte en Minimarket. Para completar la creación de tu cuenta y empezar a realizar pedidos, por favor confirma tu dirección de correo electrónico.
                                </p>
                                
                                <!-- Botón de Verificación -->
                                <div style="text-align: center; margin: 30px 0;">
                                    <a href="{enlace_verificacion}" style="background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-size: 16px; font-weight: 600; display: inline-block; box-shadow: 0 2px 6px rgba(37,99,235,0.3);">
                                        Verificar mi Correo Electrónico
                                    </a>
                                </div>

                                <p style="color: #6b7280; font-size: 13px; margin-top: 24px; text-align: center;">
                                    Si el botón no funciona, copia y pega el siguiente enlace en tu navegador:<br>
                                    <a href="{enlace_verificacion}" style="color: #2563eb; word-break: break-all; font-size: 12px;">{enlace_verificacion}</a>
                                </p>

                                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;" />

                                <!-- Token para apps móviles / Postman -->
                                <p style="color: #4b5563; font-size: 13px; margin-bottom: 8px;">
                                    <strong>¿Usas la app móvil o API directa?</strong> También puedes ingresar o enviar este token:
                                </p>
                                <div style="background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 12px; color: #334155; word-break: break-all; text-align: center;">
                                    {token}
                                </div>

                                <p style="color: #9ca3af; font-size: 12px; margin-top: 24px; text-align: center;">
                                    Este enlace expirará en 24 horas. Si no solicitaste esta cuenta, puedes ignorar este correo de forma segura.
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f9fafb; padding: 18px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                                    &copy; Minimarket API. Todos los derechos reservados.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype="html")
    return _enviar_email(msg, destinatario)


def enviar_correo_cambio_email(destinatario: str, nombre_usuario: str, token: str) -> bool:
    """Envía el correo de confirmación de cambio de correo electrónico."""
    nombre_seguro = html.escape(nombre_usuario)
    msg = EmailMessage()
    msg["Subject"] = "Confirmación de Cambio de Correo - Minimarket"
    msg["From"] = f"Minimarket <{settings.smtp_user}>"
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Has solicitado cambiar tu correo en Minimarket.\n"
        f"Tu código/token de verificación es:\n\n{token}\n\n"
        f"Este token es válido por 15 minutos."
    )

    msg.add_alternative(
        f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #2b6cb0; text-align: center;">Minimarket</h2>
                    <hr style="border: none; border-top: 1px solid #eee;" />
                    <p>Hola, <strong>{nombre_seguro}</strong>:</p>
                    <p>Has solicitado cambiar tu dirección de correo electrónico a esta cuenta.</p>
                    <p>Copia el siguiente token en la aplicación para confirmar el cambio:</p>
                    <div style="background-color: #f7fafc; padding: 15px; text-align: center; font-size: 14px; font-weight: bold; border: 1px dashed #cbd5e0; margin: 20px 0; word-break: break-all;">
                        {token}
                    </div>
                    <p style="font-size: 12px; color: #718096;">Este código expira en 15 minutos. Si no realizaste esta solicitud, puedes ignorar este mensaje.</p>
                </div>
            </body>
        </html>
        """,
        subtype="html",
    )

    return _enviar_email(msg, destinatario)


def enviar_correo_reset_password(destinatario: str, nombre_usuario: str, token: str) -> bool:
    """Envía el correo con enlace y token para restablecer la contraseña olvidada."""
    nombre_seguro = html.escape(nombre_usuario)
    base_url = settings.api_base_url.rstrip("/")
    enlace_reset = f"{base_url}/auth/restablecer-contrasena?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Restablece tu contraseña - Minimarket"
    msg["From"] = f"Minimarket <{settings.smtp_user}>"
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña en Minimarket.\n"
        f"Haz clic en el siguiente enlace para crear una nueva contraseña:\n\n"
        f"{enlace_reset}\n\n"
        f"O ingresa el siguiente token en la app:\n{token}\n\n"
        f"Este enlace expira en {settings.password_reset_token_expire_minutes} minutos.\n"
        f"Si no solicitaste este cambio, puedes ignorar este correo de forma segura."
    )

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Restablecer Contraseña</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 30px 10px;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="center">
                    <div style="max-width: 520px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.04); text-align: left;">
                        <h2 style="color: #1e3a8a; margin-top: 0;">Minimarket</h2>
                        <h3 style="color: #0f172a; margin-top: 10px;">Recuperación de Contraseña</h3>
                        <p style="color: #475569; font-size: 15px;">Hola, <strong>{nombre_seguro}</strong>:</p>
                        <p style="color: #475569; font-size: 15px;">
                            Recibimos una solicitud para restablecer la contraseña de tu cuenta. Haz clic en el botón de abajo para definir una nueva:
                        </p>
                        <div style="text-align: center; margin: 28px 0;">
                            <a href="{enlace_reset}" style="background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; display: inline-block;">
                                Restablecer mi Contraseña
                            </a>
                        </div>
                        <p style="color: #64748b; font-size: 13px; text-align: center;">
                            O copia este enlace: <br/>
                            <a href="{enlace_reset}" style="color: #2563eb; word-break: break-all; font-size: 12px;">{enlace_reset}</a>
                        </p>
                        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
                        <p style="color: #475569; font-size: 13px;"><strong>¿Usas la app móvil?</strong> Token de un solo uso:</p>
                        <div style="background-color: #f1f5f9; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 12px; text-align: center; word-break: break-all; color: #1e293b;">
                            {token}
                        </div>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 24px; text-align: center;">
                            Este enlace expirará en {settings.password_reset_token_expire_minutes} minutos. Si no fuiste tú, tu cuenta sigue segura y no necesitas hacer nada.
                        </p>
                    </div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype="html")
    return _enviar_email(msg, destinatario)


def enviar_aviso_seguridad(destinatario: str, nombre_usuario: str, accion: str) -> bool:
    """Notifica al usuario sobre una acción de seguridad relevante en su cuenta."""
    nombre_seguro = html.escape(nombre_usuario)
    accion_segura = html.escape(accion)

    msg = EmailMessage()
    msg["Subject"] = "Alerta de Seguridad - Minimarket"
    msg["From"] = f"Minimarket <{settings.smtp_user}>"
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Te informamos de una acción reciente en tu cuenta de Minimarket: {accion}\n\n"
        f"Si reconoces esta actividad, no necesitas hacer nada.\n"
        f"Si NO fuiste tú, por favor ponte en contacto con soporte de inmediato."
    )

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; border: 1px solid #cbd5e1; border-radius: 8px; padding: 24px;">
                <h3 style="color: #b91c1c; margin-top: 0;">⚠️ Aviso de Seguridad</h3>
                <p>Hola, <strong>{nombre_seguro}</strong>:</p>
                <p>Se ha registrado la siguiente actividad en tu cuenta:</p>
                <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 16px 0; color: #991b1b; font-weight: 500;">
                    {accion_segura}
                </div>
                <p style="font-size: 13px; color: #64748b;">
                    Si realizaste esta acción, puedes ignorar este mensaje.<br/>
                    Si no reconoces esta actividad, por favor comunícate de inmediato con nuestro soporte.
                </p>
            </div>
        </body>
    </html>
    """
    msg.add_alternative(html_content, subtype="html")
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

    # Construir filas de la tabla de productos
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
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 8px; font-size: 14px; color: #1e293b;">{nom_prod}</td>
            <td style="padding: 10px 8px; font-size: 14px; text-align: center; color: #475569;">{cantidad}</td>
            <td style="padding: 10px 8px; font-size: 14px; text-align: right; color: #475569;">${precio_u:.2f}</td>
            <td style="padding: 10px 8px; font-size: 14px; text-align: right; font-weight: 600; color: #0f172a;">${sub:.2f}</td>
        </tr>
        """
        filas_texto += f"- {nom_prod} x{cantidad} @ ${precio_u:.2f} = ${sub:.2f}\n"

    total = total_guardado if total_guardado > Decimal("0.00") else (subtotal_prod + envio)

    msg = EmailMessage()
    msg["Subject"] = f"Comprobante de Compra {ticket_num} - Minimarket"
    msg["From"] = f"Minimarket <{settings.smtp_user}>"
    msg["To"] = destinatario

    msg.set_content(
        f"Hola {nombre_usuario},\n\n"
        f"Gracias por tu compra en Minimarket.\n\n"
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

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Comprobante de Compra {ticket_num}</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px 10px;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="center">
                    <div style="max-width: 540px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); text-align: left;">
                        <!-- Encabezado -->
                        <div style="border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 20px;">
                            <h2 style="color: #1e40af; margin: 0; font-size: 22px;">Minimarket</h2>
                            <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px;">Comprobante de Compra / Ticket</p>
                        </div>

                        <!-- Metadatos -->
                        <table width="100%" style="margin-bottom: 20px; font-size: 13px; color: #475569;">
                            <tr>
                                <td><strong>N.º de Orden:</strong> {ticket_num}</td>
                                <td style="text-align: right;"><strong>Fecha:</strong> {fecha_str}</td>
                            </tr>
                            <tr>
                                <td><strong>Cliente:</strong> {nombre_seguro}</td>
                                <td style="text-align: right;"><strong>Pago:</strong> {metodo_pago}</td>
                            </tr>
                            <tr>
                                <td><strong>Tipo:</strong> {tipo_entrega}</td>
                                <td style="text-align: right;"><strong>Estado Pago:</strong> {estado_pago}</td>
                            </tr>
                        </table>

                        <!-- Tabla de productos -->
                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; border-collapse: collapse;">
                            <thead>
                                <tr style="background-color: #f1f5f9; text-transform: uppercase; font-size: 11px; color: #475569; letter-spacing: 0.5px;">
                                    <th style="padding: 8px; text-align: left;">Producto</th>
                                    <th style="padding: 8px; text-align: center;">Cant.</th>
                                    <th style="padding: 8px; text-align: right;">Precio</th>
                                    <th style="padding: 8px; text-align: right;">Subtotal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filas_html}
                            </tbody>
                        </table>

                        <!-- Totales -->
                        <div style="background-color: #f8fafc; border-radius: 8px; padding: 14px 16px; margin-bottom: 20px;">
                            <table width="100%" style="font-size: 14px; color: #334155;">
                                <tr>
                                    <td>Subtotal Productos:</td>
                                    <td style="text-align: right;">${subtotal_prod:.2f}</td>
                                </tr>
                                <tr>
                                    <td>Costo de Envío:</td>
                                    <td style="text-align: right;">${envio:.2f}</td>
                                </tr>
                                <tr style="font-size: 17px; font-weight: 700; color: #0f172a; border-top: 1px solid #e2e8f0;">
                                    <td style="padding-top: 8px;">TOTAL:</td>
                                    <td style="padding-top: 8px; text-align: right; color: #2563eb;">${total:.2f}</td>
                                </tr>
                            </table>
                        </div>

                        <!-- Pie de página -->
                        <p style="color: #94a3b8; font-size: 12px; text-align: center; margin: 0;">
                            ¡Gracias por comprar en Minimarket! Conserva este comprobante para cualquier reclamo o seguimiento de tu entrega.
                        </p>
                    </div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype="html")
    return _enviar_email(msg, destinatario)
    msg.add_alternative(html_content, subtype="html")
    return _enviar_email(msg, destinatario)
