import re
import secrets
from collections.abc import Callable
from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.tools.send_email_tool import send_email_message

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class LoginService:
    """Deterministic local email-code login without model orchestration or Redis."""

    def __init__(
        self,
        repository: SqliteChatRepository,
        sender: Callable[[str, str, str], str] = send_email_message,
        code_factory: Callable[[], str] | None = None,
    ):
        self.repository = repository
        self.sender = sender
        self.code_factory = code_factory or (lambda: f"{secrets.randbelow(1_000_000):06d}")

    def send_code(self, identity: str) -> dict[str, str]:
        identity = identity.strip()
        existing = self.repository.find_user(identity)
        target_email = existing["email"] if existing else identity.lower()
        if not EMAIL_RE.fullmatch(target_email):
            raise ValueError("请输入已注册的用户名，或使用有效邮箱首次登录")
        code = self.code_factory()
        self.repository.create_login_code(identity, code, target_email)
        self.sender(target_email, "AgentBI 登录验证码", f"你的 AgentBI 登录验证码是：{code}\n\n验证码将在 5 分钟后失效。")
        return {"target_email": target_email}

    def login(self, identity: str, code: str) -> dict[str, Any] | None:
        record = self.repository.consume_login_code(identity.strip(), code.strip())
        if not record:
            return None
        return self.repository.find_user(record["target_email"]) or self.repository.create_user(record["target_email"])
