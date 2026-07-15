from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Any, Callable

import websockets

from AgentBI.src.services.live.protocol import LiveAudio, LiveEvent, map_upstream_event


class LiveConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class LiveSessionConfig:
    model: str
    voice: str
    instructions: str


class QwenAudioRealtimeSession:
    def __init__(
        self,
        api_key: str,
        workspace_id: str,
        connector: Callable[..., Any] | None = None,
    ):
        self.api_key = api_key.strip()
        self.workspace_id = workspace_id.strip()
        if not self.api_key:
            raise LiveConfigurationError("缺少 DASHSCOPE_API_KEY")
        if not self.workspace_id:
            raise LiveConfigurationError("缺少 DASHSCOPE_WORKSPACE_ID")
        self.connector = connector or websockets.connect

    def _url(self, model: str) -> str:
        return (
            f"wss://{self.workspace_id}.cn-beijing.maas.aliyuncs.com"
            f"/api-ws/v1/realtime?model={model}"
        )

    @staticmethod
    def _session_update(config: LiveSessionConfig) -> dict[str, Any]:
        return {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": config.voice,
                "instructions": config.instructions,
                "turn_detection": {"type": "smart_turn"},
                "max_history_turns": 20,
            },
        }

    async def run(self, frontend: Any, config: LiveSessionConfig) -> None:
        async with self.connector(
            self._url(config.model),
            additional_headers={"Authorization": f"Bearer {self.api_key}"},
        ) as upstream:
            await upstream.send(json.dumps(self._session_update(config), ensure_ascii=False))
            frontend_task = asyncio.create_task(self._forward_frontend(frontend, upstream))
            upstream_task = asyncio.create_task(self._forward_upstream(frontend, upstream))
            tasks = {frontend_task, upstream_task}
            try:
                _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                for task in tasks - pending:
                    task.result()
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def _forward_frontend(frontend: Any, upstream: Any) -> None:
        while True:
            message = await frontend.receive()
            if message.get("type") == "websocket.disconnect":
                return
            pcm = message.get("bytes")
            if pcm is not None:
                await upstream.send(
                    json.dumps(
                        {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(pcm).decode("ascii"),
                        }
                    )
                )
                continue
            text = message.get("text")
            if text:
                try:
                    control = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if control.get("type") == "session.end":
                    return

    @staticmethod
    async def _forward_upstream(frontend: Any, upstream: Any) -> None:
        async for raw in upstream:
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                await frontend.send_json(
                    LiveEvent(
                        "session.error",
                        {
                            "code": "invalid_upstream_event",
                            "message": "实时语音服务返回了无法识别的事件",
                            "recoverable": True,
                        },
                    ).as_dict()
                )
                continue
            for output in map_upstream_event(event):
                if isinstance(output, LiveAudio):
                    await frontend.send_bytes(output.pcm)
                else:
                    await frontend.send_json(output.as_dict())
