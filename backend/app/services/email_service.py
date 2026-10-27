import smtplib
import ssl
from email.message import EmailMessage

import certifi

from ..core.config import settings


class EmailService:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.smtp_host and settings.smtp_from_email)

    @staticmethod
    def send_password_reset_code(recipient: str, code: str) -> None:
        if not EmailService.is_configured():
            raise RuntimeError("SMTP email delivery is not configured")

        message = EmailMessage()
        message["Subject"] = "Your NutriDay password reset code"
        message["From"] = settings.smtp_from_email
        message["To"] = recipient
        message.set_content(
            "Use this code to reset your NutriDay password: "
            f"{code}\n\nThe code expires in 10 minutes. If you did not request it, ignore this email."
        )

        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=15,
                context=ssl.create_default_context(cafile=certifi.where()),
            ) as server:
                EmailService._deliver(server, message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_use_tls:
                    server.starttls(
                        context=ssl.create_default_context(cafile=certifi.where())
                    )
                EmailService._deliver(server, message)

    @staticmethod
    def _deliver(server: smtplib.SMTP, message: EmailMessage) -> None:
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
