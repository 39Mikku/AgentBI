from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import websockets

from AgentBI.src.services.live.protocol import LiveAudio, LiveEvent, map_upstream_event


class LiveConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class LiveSessionConfig:
    model: str
    voice: str
    instructions: str
    max_history_turns: int = 20


LiveEventHandler = Callable[[LiveEvent], Awaitable[LiveEvent | None]]


class LiveSessionPreparationError(RuntimeError):
    def __init__(self, event: LiveEvent):
        super().__init__(event.payload.get("message", "Live session preparation failed"))
        self.event = event


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
                "max_history_turns": config.max_history_turns,
            },
        }

    async def run(
        self,
        frontend: Any,
        config: LiveSessionConfig,
        event_handler: LiveEventHandler | None = None,
    ) -> None:
        async with self.connector(
            self._url(config.model),
            additional_headers={"Authorization": f"Bearer {self.api_key}"},
        ) as upstream:
            try:
                await self._prepare(frontend, upstream, config)
            except LiveSessionPreparationError as error:
                await frontend.send_json(error.event.as_dict())
                return
            frontend_task = asyncio.create_task(self._forward_frontend(frontend, upstream))
            upstream_task = asyncio.create_task(
                self._forward_upstream(frontend, upstream, event_handler)
            )
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

    async def _prepare(
        self,
        frontend: Any,
        upstream: Any,
        config: LiveSessionConfig,
    ) -> None:
        await upstream.send(json.dumps(self._session_update(config), ensure_ascii=False))
        await self._wait_for_ack(upstream, "session.updated")
        await frontend.send_json({"type": "session.ready"})

    @staticmethod
    async def _wait_for_ack(upstream: Any, expected_type: str) -> dict[str, Any]:
        while True:
            raw = await upstream.recv()
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raise LiveSessionPreparationError(
                    LiveEvent(
                        "session.error",
                        {
                            "code": "invalid_upstream_event",
                            "message": "实时语音服务返回了无法识别的准备事件",
                            "recoverable": True,
                        },
                    )
                )
            if event.get("type") == expected_type:
                return event
            if event.get("type") == "error":
                mapped = map_upstream_event(event)
                error = next(
                    (item for item in mapped if isinstance(item, LiveEvent)),
                    LiveEvent(
                        "session.error",
                        {
                            "code": "upstream_error",
                            "message": "实时语音会话准备失败",
                            "recoverable": False,
                        },
                    ),
                )
                raise LiveSessionPreparationError(error)

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
    async def _forward_upstream(
        frontend: Any,
        upstream: Any,
        event_handler: LiveEventHandler | None = None,
    ) -> None:
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
                    handled = await event_handler(output) if event_handler else output
                    if handled is not None:
                        await frontend.send_json(handled.as_dict())
