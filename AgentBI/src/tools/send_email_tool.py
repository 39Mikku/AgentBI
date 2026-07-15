import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool

from AgentBI.src.schemas.email_schema import EmailSchema

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_smtp_environment() -> None:
    """Load the backend-local SMTP configuration even if the launcher exports empty values."""
    load_dotenv(ENV_PATH, override=True)


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


def send_email_message(to: str, subject: str, content: str) -> str:
    """Send one SMTP message without involving an LLM or LangChain tool wrapper."""
    try:
        host, port, sender, password = smtp_settings()
        message = MIMEText(content)
        message["To"] = to
        message["From"] = sender
        message["Subject"] = subject
        with smtplib.SMTP_SSL(host, port=port, timeout=20) as smtp:
            smtp.login(sender, password)
            smtp.sendmail(sender, to, message.as_string())
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
