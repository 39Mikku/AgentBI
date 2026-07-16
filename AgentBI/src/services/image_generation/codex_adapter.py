from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from typing import Any

import httpx

from AgentBI.src.services.image_generation.codex_oauth import account_id_from_token
from AgentBI.src.services.image_generation.lite_adapter import ImageBinary, ImageGenerationError


CODEX_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
_SIZES = {
    "landscape": "1536x1024",
    "square": "1024x1024",
    "portrait": "1024x1536",
}


def build_codex_payload(*, prompt: str, aspect_ratio: str, quality: str) -> dict[str, Any]:
    return {
        "model": "gpt-5.5",
        "store": False,
        "instructions": (
            "You are an assistant that must fulfill image generation requests by using "
            "the image_generation tool when provided."
        ),
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        "tools": [
            {
                "type": "image_generation",
                "model": "gpt-image-2",
                "size": _SIZES.get(aspect_ratio, _SIZES["square"]),
                "quality": quality,
                "output_format": "png",
                "background": "opaque",
                "partial_images": 1,
            }
        ],
        "tool_choice": {
            "type": "allowed_tools",
            "mode": "required",
            "tools": [{"type": "image_generation"}],
        },
        "stream": True,
    }


def codex_headers(access_token: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": "codex_cli_rs/0.144.3 (AgentBI)",
        "originator": "codex_cli_rs",
    }
    account_id = account_id_from_token(access_token)
    if account_id:
        headers["ChatGPT-Account-ID"] = account_id
    return headers


def parse_sse_lines(lines: Iterable[str | bytes]):
    event_name: str | None = None
    data_lines: list[str] = []

    def flush():
        nonlocal event_name, data_lines
        raw = "\n".join(data_lines).strip()
        event = event_name
        event_name = None
        data_lines = []
        if not raw or raw == "[DONE]":
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict) and event and "type" not in payload:
            payload["type"] = event
        return payload

    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else str(raw_line)
        line = line.rstrip("\r\n")
        if not line:
            payload = flush()
            if payload is not None:
                yield payload
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    payload = flush()
    if payload is not None:
        yield payload


def extract_image_b64(value: Any) -> str | None:
    found: str | None = None
    if isinstance(value, dict):
        if value.get("type") == "image_generation_call" and isinstance(value.get("result"), str):
            found = value["result"]
        if isinstance(value.get("partial_image_b64"), str):
            found = value["partial_image_b64"]
        for child in value.values():
            nested = extract_image_b64(child)
            if nested:
                found = nested
    elif isinstance(value, list):
        for child in value:
            nested = extract_image_b64(child)
            if nested:
                found = nested
    return found


def extract_final_image_b64(value: Any) -> str | None:
    found: str | None = None
    if isinstance(value, dict):
        if value.get("type") == "image_generation_call" and isinstance(value.get("result"), str):
            found = value["result"]
        for child in value.values():
            nested = extract_final_image_b64(child)
            if nested:
                found = nested
    elif isinstance(value, list):
        for child in value:
            nested = extract_final_image_b64(child)
            if nested:
                found = nested
    return found


class CodexImageAdapter:
    async def generate(
        self,
        *,
        access_token: str,
        prompt: str,
        aspect_ratio: str,
        quality: str,
        client: httpx.AsyncClient | None = None,
    ) -> ImageBinary:
        owns_client = client is None
        http = client or httpx.AsyncClient(
            timeout=httpx.Timeout(300, connect=30, read=300, write=30, pool=30)
        )
        latest: str | None = None
        try:
            async with http.stream(
                "POST",
                CODEX_RESPONSES_URL,
                headers=codex_headers(access_token),
                json=build_codex_payload(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    quality=quality,
                ),
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")[:500]
                    if "Tool choice 'image_generation' not found" in body:
                        raise ImageGenerationError("当前 Codex 账户暂不支持 gpt-image-2 生图工具")
                    raise ImageGenerationError(f"Codex 生图请求失败（HTTP {response.status_code}）")
                pending_lines: list[str] = []
                final_received = False
                async for line in response.aiter_lines():
                    pending_lines.append(line)
                    if line.strip():
                        continue
                    for event in parse_sse_lines(pending_lines):
                        candidate = extract_image_b64(event)
                        if candidate:
                            latest = candidate
                        final = extract_final_image_b64(event)
                        if final:
                            latest = final
                            final_received = True
                            break
                    pending_lines = []
                    if final_received:
                        break
                if pending_lines and not final_received:
                    for event in parse_sse_lines(pending_lines):
                        candidate = extract_image_b64(event)
                        if candidate:
                            latest = candidate
        finally:
            if owns_client:
                await http.aclose()
        if not latest:
            raise ImageGenerationError("Codex 未返回图片结果")
        try:
            image_bytes = base64.b64decode(latest, validate=True)
        except Exception as error:
            raise ImageGenerationError("Codex 返回的图片数据无效") from error
        if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ImageGenerationError("Codex 返回的图片数据无效")
        return ImageBinary(image_bytes=image_bytes, media_type="image/png", model="gpt-image-2")
