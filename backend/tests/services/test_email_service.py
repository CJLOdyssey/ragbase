import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["EMAIL_BACKEND"] = "log"
os.environ["EMAIL_FROM"] = "test@example.com"
os.environ["EMAIL_SMTP_HOST"] = "smtp.test.com"
os.environ["EMAIL_SMTP_PORT"] = "587"
os.environ["EMAIL_SMTP_USER"] = "user"
os.environ["EMAIL_SMTP_PASSWORD"] = "pass"
os.environ["EMAIL_SMTP_TLS"] = "1"
os.environ["RESEND_API_KEY"] = "re_test_key"

import pytest
from services.email_service import (
    LogMailer,
    ResendApiMailer,
    SmtpMailer,
    build_password_changed_email,
    build_reset_email,
    build_verification_email,
    send_email,
)


class TestBuildEmail:

    def test_build_verification_email(self):
        subject, html = build_verification_email("123456")
        assert "123456" in subject
        assert "123456" in html
        assert "验证码" in html

    def test_build_reset_email(self):
        subject, html = build_reset_email("654321")
        assert "654321" in html
        assert "密码重置" in subject
        assert "验证码" in html

    def test_build_password_changed_email(self):
        subject, html = build_password_changed_email()
        assert "密码已被修改" in subject
        assert "密码已被修改" in html

    def test_build_verification_email_ttl(self):
        subject, html = build_verification_email("000000", ttl_minutes=10)
        assert "000000" in html
        assert "10 分钟" in html

    def test_build_reset_email_ttl(self):
        subject, html = build_reset_email("111111", ttl_minutes=30)
        assert "111111" in html
        assert "30 分钟" in html


class TestLogMailer:

    def test_log_mailer_send(self):
        mailer = LogMailer()
        mailer.send("test@example.com", "Test Subject", "<p>Your code is 123456</p>")

    def test_log_mailer_no_code(self):
        mailer = LogMailer()
        mailer.send("test@example.com", "No Code", "<p>No digits here</p>")


class TestSmtpMailer:

    @pytest.mark.asyncio
    async def test_send_email_calls_smtp(self):
        mailer = SmtpMailer()
        with patch("services.email_service.SMTP_HOST", "smtp.test.com"), \
             patch("services.email_service.SMTP_USER", "user"), \
             patch("services.email_service.SMTP_PASSWORD", "pass"), \
             patch("services.email_service.smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value.__enter__.return_value
            await mailer.send("to@test.com", "Subj", "<p>Body</p>")
            instance.sendmail.assert_called_once()
            instance.starttls.assert_called_once()
            instance.login.assert_called_once_with("user", "pass")

    @pytest.mark.asyncio
    async def test_send_email_port_465(self):
        mailer = SmtpMailer()
        with patch("services.email_service.SMTP_PORT", 465), \
             patch("services.email_service.SMTP_HOST", "smtp.test.com"), \
             patch("services.email_service.SMTP_USER", "user"), \
             patch("services.email_service.SMTP_PASSWORD", "pass"), \
             patch("services.email_service.smtplib.SMTP_SSL") as mock_smtp_ssl:
            instance = mock_smtp_ssl.return_value.__enter__.return_value
            await mailer.send("to@test.com", "Subj", "<p>Body</p>")
            instance.sendmail.assert_called_once()


class TestResendApiMailer:

    @pytest.mark.asyncio
    async def test_send_via_resend(self):
        mailer = ResendApiMailer()
        with patch("services.email_service.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"id": "test-id"}'
            mock_urlopen.return_value = mock_resp
            await mailer.send("to@test.com", "Subj", "<p>Body</p>")
            mock_urlopen.assert_called_once()


class TestSendEmailTopLevel:

    @pytest.mark.asyncio
    async def test_send_email_log_backend(self):
        with patch("services.email_service.LogMailer.send", new_callable=MagicMock) as mock_send:
            await send_email("to@test.com", "Subj", "<p>Body</p>")
            mock_send.assert_called_once_with("to@test.com", "Subj", "<p>Body</p>")

    @pytest.mark.asyncio
    async def test_send_email_smtp_backend(self):
        with patch("services.email_service.EMAIL_BACKEND", "smtp"), \
             patch("services.email_service.SMTP_HOST", "smtp.test.com"):
            with patch("services.email_service.SmtpMailer.send", new_callable=AsyncMock) as mock_send:
                await send_email("to@test.com", "Subj", "<p>Body</p>")
                mock_send.assert_awaited_once_with("to@test.com", "Subj", "<p>Body</p>")

    @pytest.mark.asyncio
    async def test_send_email_resend_backend(self):
        with patch("services.email_service.EMAIL_BACKEND", "resend"), \
             patch("services.email_service.RESEND_API_KEY", "re_test"):
            with patch("services.email_service.ResendApiMailer.send", new_callable=AsyncMock) as mock_send:
                await send_email("to@test.com", "Subj", "<p>Body</p>")
                mock_send.assert_awaited_once_with("to@test.com", "Subj", "<p>Body</p>")

    @pytest.mark.asyncio
    async def test_send_email_smtp_fallback_on_error(self):
        with patch("services.email_service.EMAIL_BACKEND", "smtp"), \
             patch("services.email_service.SMTP_HOST", "smtp.test.com"):
            with patch("services.email_service.SmtpMailer.send", new_callable=AsyncMock) as mock_smtp:
                mock_smtp.side_effect = Exception("SMTP error")
                with patch("services.email_service.LogMailer.send", new_callable=MagicMock) as mock_log:
                    await send_email("to@test.com", "Subj", "<p>Body</p>")
                    mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_resend_fallback_on_error(self):
        with patch("services.email_service.EMAIL_BACKEND", "resend"), \
             patch("services.email_service.RESEND_API_KEY", "re_test"):
            with patch("services.email_service.ResendApiMailer.send", new_callable=AsyncMock) as mock_resend:
                mock_resend.side_effect = Exception("Resend error")
                with patch("services.email_service.LogMailer.send", new_callable=MagicMock) as mock_log:
                    await send_email("to@test.com", "Subj", "<p>Body</p>")
                    mock_log.assert_called_once()
