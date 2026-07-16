from __future__ import annotations

import base64
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from AgentBI.src.schemas.image_generation_schema import CodexOAuthStartResponse, CodexOAuthStatus


CODEX_OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
CODEX_OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"
TOKEN_REFRESH_SKEW_SECONDS = 120


class CodexOAuthError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class PendingDeviceLogin:
    user_code: str
    device_auth_id: str
    interval: int
    authorization_url: str = "https://auth.openai.com/codex/device"
    expires_in: int = 900


async def request_device_login(client: Any) -> PendingDeviceLogin:
    try:
        response = await client.post(
            "https://auth.openai.com/api/accounts/deviceauth/usercode",
            json={"client_id": CODEX_OAUTH_CLIENT_ID},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        raise CodexOAuthError("无法启动 Codex 设备登录") from error
    user_code = str(payload.get("user_code") or "")
    device_auth_id = str(payload.get("device_auth_id") or "")
    if not user_code or not device_auth_id:
        raise CodexOAuthError("Codex 设备登录响应不完整")
    return PendingDeviceLogin(
        user_code=user_code,
        device_auth_id=device_auth_id,
        interval=max(3, int(payload.get("interval") or 5)),
    )


def decode_jwt_claims(token: str) -> dict[str, Any]:
    try:
        segment = token.split(".")[1]
        padded = segment + "=" * (-len(segment) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def account_id_from_token(token: str) -> str | None:
    auth = decode_jwt_claims(token).get("https://api.openai.com/auth")
    account_id = auth.get("chatgpt_account_id") if isinstance(auth, dict) else None
    return account_id if isinstance(account_id, str) and account_id else None


class CodexOAuthTokenStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def save_tokens(self, payload: dict[str, Any], *, now: int | None = None) -> None:
        access_token = str(payload.get("access_token") or "").strip()
        existing = self._load()
        refresh_token = str(payload.get("refresh_token") or existing.get("refresh_token") or "").strip()
        if not access_token or not refresh_token:
            raise CodexOAuthError("Codex OAuth 返回的凭据不完整")
        current = int(time.time()) if now is None else int(now)
        expires_in = max(1, int(payload.get("expires_in") or 3600))
        self._write(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": current + expires_in,
                "account_id": account_id_from_token(access_token),
                "token_type": str(payload.get("token_type") or "Bearer"),
            }
        )

    def status(self) -> CodexOAuthStatus:
        payload = self._load()
        connected = bool(payload.get("access_token") and payload.get("refresh_token"))
        return CodexOAuthStatus(
            connected=connected,
            account_id=payload.get("account_id") if connected else None,
            expires_at=int(payload["expires_at"]) if connected and payload.get("expires_at") else None,
        )

    def disconnect(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        try:
            self.path.with_suffix(self.path.suffix + ".tmp").unlink()
        except FileNotFoundError:
            pass

    async def valid_access_token(self, *, client: Any | None = None) -> str:
        payload = self._load()
        access_token = str(payload.get("access_token") or "")
        expires_at = int(payload.get("expires_at") or 0)
        if access_token and expires_at > int(time.time()) + TOKEN_REFRESH_SKEW_SECONDS:
            return access_token
        refresh_token = str(payload.get("refresh_token") or "")
        if not refresh_token:
            raise CodexOAuthError("Pro 模式尚未连接 Codex")
        owns_client = client is None
        http = client or httpx.AsyncClient(timeout=20)
        try:
            response = await http.post(
                CODEX_OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": CODEX_OAUTH_CLIENT_ID,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            refreshed = response.json()
            if not isinstance(refreshed, dict):
                raise CodexOAuthError("Codex OAuth 刷新响应无效")
            self.save_tokens(refreshed)
            return str(refreshed["access_token"])
        except CodexOAuthError:
            raise
        except Exception as error:
            raise CodexOAuthError("Codex OAuth 已失效，请重新连接") from error
        finally:
            if owns_client:
                await http.aclose()


class CodexOAuthManager:
    def __init__(self, token_store: CodexOAuthTokenStore):
        self.token_store = token_store
        self._task: asyncio.Task[None] | None = None
        self._last_error: str | None = None

    def status(self) -> CodexOAuthStatus:
        status = self.token_store.status()
        return status.model_copy(
            update={
                "pending": bool(self._task and not self._task.done()),
                "error": self._last_error,
            }
        )

    async def start(self) -> CodexOAuthStartResponse:
        if self._task and not self._task.done():
            raise CodexOAuthError("Codex 登录正在等待确认")
        async with httpx.AsyncClient(timeout=20) as client:
            pending = await request_device_login(client)
        self._last_error = None
        self._task = asyncio.create_task(self._complete(pending))
        return CodexOAuthStartResponse(
            authorization_url=pending.authorization_url,
            user_code=pending.user_code,
            expires_in=pending.expires_in,
        )

    async def _complete(self, pending: PendingDeviceLogin) -> None:
        deadline = time.monotonic() + pending.expires_in
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                exchange: dict[str, Any] | None = None
                while time.monotonic() < deadline:
                    await asyncio.sleep(pending.interval)
                    response = await client.post(
                        "https://auth.openai.com/api/accounts/deviceauth/token",
                        json={
                            "device_auth_id": pending.device_auth_id,
                            "user_code": pending.user_code,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    if response.status_code == 200:
                        exchange = response.json()
                        break
                    if response.status_code in {403, 404}:
                        continue
                    raise CodexOAuthError("Codex 设备登录确认失败")
                if not exchange:
                    raise CodexOAuthError("Codex 登录已超时，请重新连接")
                authorization_code = str(exchange.get("authorization_code") or "")
                code_verifier = str(exchange.get("code_verifier") or "")
                if not authorization_code or not code_verifier:
                    raise CodexOAuthError("Codex 设备登录确认响应不完整")
                token_response = await client.post(
                    CODEX_OAUTH_TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "code": authorization_code,
                        "redirect_uri": "https://auth.openai.com/deviceauth/callback",
                        "client_id": CODEX_OAUTH_CLIENT_ID,
                        "code_verifier": code_verifier,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_response.raise_for_status()
                self.token_store.save_tokens(token_response.json())
        except asyncio.CancelledError:
            return
        except Exception as error:
            self._last_error = str(error) if isinstance(error, CodexOAuthError) else "Codex 登录失败"

    def disconnect(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._last_error = None
        self.token_store.disconnect()

