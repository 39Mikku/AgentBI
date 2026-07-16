from __future__ import annotations

from typing import Any

import httpx

from AgentBI.src.services.video_generation.provider import VideoCreateRequest


class ArkVideoError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ArkVideoClient:
    provider_id = "volcengine"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        http_client: httpx.AsyncClient | None = None,
        download_client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key.strip()
        self._owns_http = http_client is None
        self._owns_download = download_client is None
        self.http = http_client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(60.0),
        )
        self.download_http = download_client or httpx.AsyncClient(timeout=httpx.Timeout(180.0))

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise ArkVideoError("请先在 .env 中配置 ARK_API_KEY")

    @staticmethod
    def _payload(response: httpx.Response) -> dict[str, Any]:
        try:
            value = response.json()
        except ValueError as error:
            raise ArkVideoError("火山方舟返回了无法解析的响应") from error
        if not isinstance(value, dict):
            raise ArkVideoError("火山方舟返回的数据格式无效")
        return value

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            value = response.json()
        except ValueError:
            return response.text[:300]
        if not isinstance(value, dict):
            return str(value)
        error = value.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or error)
        return str(value.get("message") or error or "")

    @classmethod
    def _raise_for_status(cls, response: httpx.Response) -> None:
        if response.is_success:
            return
        detail = cls._error_detail(response)
        suffix = f"：{detail}" if detail else ""
        raise ArkVideoError(
            f"火山方舟视频请求失败（HTTP {response.status_code}）{suffix}",
            retryable=response.status_code in {408, 409, 429, 500, 502, 503, 504},
        )

    async def create_video(self, request: VideoCreateRequest) -> dict[str, Any]:
        self._ensure_key()
        content: list[dict[str, Any]] = [{"type": "text", "text": request.prompt}]
        if request.image_data_url:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": request.image_data_url},
                }
            )
        body = {
            "model": request.model,
            "content": content,
            "ratio": request.aspect_ratio,
            "duration": request.duration_seconds,
            "resolution": request.resolution,
            "generate_audio": request.generate_audio,
            "watermark": request.watermark,
        }
        try:
            response = await self.http.post("/contents/generations/tasks", json=body)
        except httpx.HTTPError as error:
            raise ArkVideoError(f"无法连接火山方舟：{error}", retryable=True) from error
        self._raise_for_status(response)
        payload = self._payload(response)
        task_id = str(payload.get("id") or "").strip()
        if not task_id:
            raise ArkVideoError("火山方舟创建任务后未返回任务 ID")
        return {"task_id": task_id, "status": "queued", "progress": 0, "raw": payload}

    async def get_video(self, task_id: str) -> dict[str, Any]:
        self._ensure_key()
        try:
            response = await self.http.get(f"/contents/generations/tasks/{task_id}")
        except httpx.HTTPError as error:
            raise ArkVideoError(f"查询火山方舟视频任务失败：{error}", retryable=True) from error
        self._raise_for_status(response)
        payload = self._payload(response)
        provider_status = str(payload.get("status") or "running")
        status = {
            "queued": "queued",
            "running": "in_progress",
            "succeeded": "completed",
            "failed": "failed",
            "expired": "failed",
            "cancelled": "failed",
        }.get(provider_status, "in_progress")
        output = payload.get("content") if isinstance(payload.get("content"), dict) else {}
        error = payload.get("error")
        if provider_status in {"expired", "cancelled"} and not error:
            error = f"火山方舟任务状态：{provider_status}"
        return {
            "task_id": str(payload.get("id") or task_id),
            "status": status,
            "progress": 100 if status == "completed" else 0,
            "url": str(output.get("video_url") or ""),
            "error": error,
            "metadata": {
                key: payload.get(key)
                for key in (
                    "model",
                    "duration",
                    "ratio",
                    "resolution",
                    "generate_audio",
                    "service_tier",
                )
                if payload.get(key) is not None
            },
            "raw": payload,
        }

    async def download_video(self, url: str) -> bytes:
        try:
            response = await self.download_http.get(url)
        except httpx.HTTPError as error:
            raise ArkVideoError(f"下载火山方舟视频失败：{error}", retryable=True) from error
        self._raise_for_status(response)
        return response.content

    async def close(self) -> None:
        if self._owns_http:
            await self.http.aclose()
        if self._owns_download:
            await self.download_http.aclose()
