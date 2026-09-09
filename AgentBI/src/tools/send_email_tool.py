import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import dotenv_values
from langchain_core.tools import tool

from AgentBI.src.schemas.email_schema import EmailSchema

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_smtp_environment() -> None:
    """Load the backend-local SMTP configuration even if the launcher exports empty values."""
    values = dotenv_values(ENV_PATH)
    for key in ("EMAIL_HOST", "EMAIL_FROM", "EMAIL_PASSWORD", "EMAIL_PORT"):
        if values.get(key) is not None:
            os.environ[key] = values[key]


load_smtp_environment()


def smtp_settings() -> tuple[str, int, str, str]:
    """Return validated SMTP settings before creating a network client."""
    host = (os.getenv("EMAIL_HOST") or "").strip()
    sender = (os.getenv("EMAIL_FROM") or "").strip()
    password = os.getenv("EMAIL_PASSWORD") or ""
    if not host:
        raise RuntimeError("SMTP 配置缺少 EMAIL_HOST")
    if not sender:
        raise RuntimeError("SMTP 配置缺少 EMAIL_FROM")
    if not password:
        raise RuntimeError("SMTP 配置缺少 EMAIL_PASSWORD")
    try:
        port = int(os.getenv("EMAIL_PORT", "465"))
    except ValueError as error:
        raise RuntimeError("SMTP 配置中的 EMAIL_PORT 无效") from error
    return host, port, sender, password


def build_email_message(
    to: str,
    subject: str,
    content: str,
    *,
    sender: str,
    html_content: str | None = None,
) -> EmailMessage:
    """Build a standards-compatible message with an optional HTML alternative."""
    message = EmailMessage()
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(content)
    if html_content:
        message.add_alternative(html_content, subtype="html")
    return message


def send_email_message(
    to: str,
    subject: str,
    content: str,
    *,
    html_content: str | None = None,
) -> str:
    """Send one SMTP message without involving an LLM or LangChain tool wrapper."""
    try:
        host, port, sender, password = smtp_settings()
        message = build_email_message(to, subject, content, sender=sender, html_content=html_content)
        with smtplib.SMTP_SSL(host, port=port, timeout=20) as smtp:
            smtp.login(sender, password)
            smtp.send_message(message, from_addr=sender, to_addrs=[to])
        return "邮件发送成功"
    except Exception as error:
        raise RuntimeError(f"邮件发送失败: {error}") from error


@tool("send_email", args_schema=EmailSchema)
def send_email(to: str, subject: str, content: str) -> str:
    """Send an email composed by the email subagent."""
    try:
        return send_email_message(to, subject, content)
    except RuntimeError as error:
        return str(error)
