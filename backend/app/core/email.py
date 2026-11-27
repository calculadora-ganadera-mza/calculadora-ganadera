import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

from app.core.config import settings


class EmailSender(Protocol):
    """Lo que necesita la app para mandar un correo, sin importar el medio."""

    def send(self, to: str, subject: str, text: str) -> None: ...


class SmtpEmailSender:
    """Manda correos por SMTP con los datos del entorno."""

    def send(self, to: str, subject: str, text: str) -> None:
        message = EmailMessage()
        message["From"] = settings.mail_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text)
        # Sin límite de espera, un servidor que no responde deja la tarea colgada.
        with smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=10) as smtp:
            if settings.mail_starttls:
                # Sin contexto, Python no verifica el certificado del servidor.
                smtp.starttls(context=ssl.create_default_context())
            if settings.mail_username:
                smtp.login(settings.mail_username, settings.mail_password)
            smtp.send_message(message)


def get_email_sender() -> EmailSender:
    """Medio de envío que usan las rutas. Las pruebas lo reemplazan."""
    return SmtpEmailSender()
