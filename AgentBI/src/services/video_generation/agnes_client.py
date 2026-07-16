from __future__ import annotations

from typing import Any

import httpx


class AgnesVideoError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class AgnesVideoClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://apihub.agnes-ai.com",
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
            raise AgnesVideoError("请先在 .env 中配置 AGNES_API_KEY")

    @staticmethod
    def _payload(response: httpx.Response) -> dict[str, Any]:
        try:
            value = response.json()
        except ValueError as error:
            raise AgnesVideoError("Agnes 返回了无法解析的响应") from error
        if not isinstance(value, dict):
            raise AgnesVideoError("Agnes 返回的数据格式无效")
        return value

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        detail = ""
        try:
            value = response.json()
            if isinstance(value, dict):
                detail = str(value.get("message") or value.get("error") or "")
        except ValueError:
            detail = response.text[:300]
        suffix = f"：{detail}" if detail else ""
        raise AgnesVideoError(
            f"Agnes 请求失败（HTTP {response.status_code}）{suffix}",
            retryable=response.status_code in {429, 500, 502, 503, 504},
        )

    async def create_video(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        num_frames: int,
    ) -> dict[str, Any]:
        self._ensure_key()
        try:
            response = await self.http.post(
                "/v1/videos",
                json={
                    "model": "agnes-video-v2.0",
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_frames": num_frames,
                    "frame_rate": 24,
                },
            )
        except httpx.HTTPError as error:
            raise AgnesVideoError(f"无法连接 Agnes：{error}", retryable=True) from error
        self._raise_for_status(response)
        payload = self._payload(response)
        if not payload.get("video_id"):
            raise AgnesVideoError("Agnes 创建任务后未返回 video_id")
        return payload

    async def get_video(self, video_id: str) -> dict[str, Any]:
        self._ensure_key()
        try:
            response = await self.http.get("/agnesapi", params={"video_id": video_id})
        except httpx.HTTPError as error:
            raise AgnesVideoError(f"查询 Agnes 任务失败：{error}", retryable=True) from error
        self._raise_for_status(response)
        return self._payload(response)

    async def download_video(self, url: str) -> bytes:
        try:
            response = await self.download_http.get(url)
        except httpx.HTTPError as error:
            raise AgnesVideoError(f"下载 Agnes 视频失败：{error}", retryable=True) from error
        self._raise_for_status(response)
        return response.content

    async def close(self) -> None:
        if self._owns_http:
            await self.http.aclose()
        if self._owns_download:
            await self.download_http.aclose()

