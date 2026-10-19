import logging
import smtplib
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger(__name__)


def _enviar_email(msg: EmailMessage, destinatario: str) -> bool:
    """Envía un correo electrónico utilizando el servidor SMTP SSL configurado."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "[EMAIL] No se han configurado credenciales SMTP (smtp_user o smtp_password). "
            f"No se envió correo a {destinatario}."
        )
        return False

    try:
        with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port, timeout=15) as smtp:
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
                                <h2 style="color: #1f2937; margin-top: 0; font-size: 20px;">¡Hola, {nombre_usuario}! 👋</h2>
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
                    <p>Hola, <strong>{nombre_usuario}</strong>:</p>
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
        subtype="html"
    )

    return _enviar_email(msg, destinatario)