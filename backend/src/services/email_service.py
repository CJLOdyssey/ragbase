"""Email sending abstraction with SMTP / Resend API backends and log fallback."""

import asyncio
import json
import os
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.request import Request, urlopen

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "log")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")

SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("EMAIL_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD", "")
SMTP_USE_TLS = os.environ.get("EMAIL_SMTP_TLS", "1") == "1"


class LogMailer:
    """Development mailer — prints emails to log and stdout."""

    def send(self, to: str, subject: str, html: str) -> None:
        """Log email details to the console (dev fallback)."""
        code_match = re.search(r"(\d{6})", html)
        code = code_match.group(1) if code_match else "??????"
        logger.info("[EMAIL] To=%s | Subject=%s | Code=%s", to, subject, code)
        print(
            f"╔═══════════════════════════════════════\n"
            f"║ TO: {to}\n"
            f"║ SUBJECT: {subject}\n"
            f"║ CODE: {code}\n"
            f"╚═══════════════════════════════════════"
        )


class SmtpMailer:
    """Production SMTP mailer — sends real emails."""

    async def send(self, to: str, subject: str, html: str) -> None:
        """Send an email via SMTP (runs blocking call in worker thread)."""
        await asyncio.to_thread(self._send_sync, to, subject, html)

    def _send_sync(self, to: str, subject: str, html: str) -> None:
        """Send email synchronously via SMTP in a thread pool executor."""
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_FROM or SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html", "utf-8"))

        ctx = ssl.create_default_context()
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as server:
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(msg["From"], to, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                if SMTP_USE_TLS:
                    server.starttls(context=ctx)
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(msg["From"], to, msg.as_string())

        logger.info("[SMTP] Sent to=%s | subject=%s", to, subject)


class ResendApiMailer:
    """Resend HTTP API mailer — works with onboarding@resend.dev without a domain."""

    async def send(self, to: str, subject: str, html: str) -> None:
        """Send an email via the Resend HTTP API (runs blocking call in worker thread)."""
        await asyncio.to_thread(self._send_sync, to, subject, html)

    def _send_sync(self, to: str, subject: str, html: str) -> None:
        """Send email synchronously via Resend API in a thread pool."""
        payload = json.dumps({"from": EMAIL_FROM, "to": to, "subject": subject, "html": html}).encode()
        req = Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "RagBase/1.0",
            },
        )
        resp = urlopen(req, timeout=15)  # nosec B310
        body = resp.read().decode()
        logger.info("[ResendAPI] Sent to=%s | subject=%s | response=%s", to, subject, body)


async def send_email(to: str, subject: str, html: str) -> None:
    """Send an email using the configured backend."""
    if EMAIL_BACKEND == "resend" and RESEND_API_KEY:
        try:
            await ResendApiMailer().send(to, subject, html)
            return
        except Exception:
            logger.exception("[ResendAPI] Failed to send email, falling back to log")
    elif EMAIL_BACKEND == "smtp" and SMTP_HOST:
        try:
            await SmtpMailer().send(to, subject, html)
            return
        except Exception:
            logger.exception("[SMTP] Failed to send email, falling back to log")
    LogMailer().send(to, subject, html)


def build_verification_email(code: str, ttl_minutes: int = 5) -> tuple[str, str]:
    """Build a verification email with a numeric code."""
    subject = f"【RagBase】您的验证码是 {code}"
    html = f"""<p>您好，</p>
<p>您的邮箱验证码为：</p>
<h2 style="letter-spacing:8px;font-size:32px;text-align:center;">{code}</h2>
<p>验证码 {ttl_minutes} 分钟内有效，请勿泄露给他人。</p>
<p>如果这不是您本人的操作，请忽略此邮件。</p>"""
    return subject, html


def build_reset_email(code: str, ttl_minutes: int = 15) -> tuple[str, str]:
    """Build a password reset verification email."""
    subject = "【RagBase】密码重置验证码"
    html = f"""<p>您好，</p>
<p>您的密码重置验证码为：</p>
<h2 style="letter-spacing:8px;font-size:32px;text-align:center;">{code}</h2>
<p>验证码 {ttl_minutes} 分钟内有效，请勿泄露给他人。</p>
<p>如果这不是您本人的操作，请忽略此邮件。</p>"""
    return subject, html


def build_password_changed_email() -> tuple[str, str]:
    """Build a password changed confirmation email."""
    subject = "【RagBase】您的密码已被修改"
    html = """<p>您好，</p>
<p>您的账户密码已被修改。</p>
<p>如果这不是您本人的操作，请立即重置密码或联系管理员。</p>"""
    return subject, html
