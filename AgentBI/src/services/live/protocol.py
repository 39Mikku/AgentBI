from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"type": self.type, **self.payload}


@dataclass(frozen=True)
class LiveAudio:
    pcm: bytes


LiveOutput = LiveEvent | LiveAudio


def _payload(event: dict[str, Any], *names: str) -> dict[str, Any]:
    return {name: event.get(name) for name in names if event.get(name) is not None}


def map_upstream_event(event: dict[str, Any]) -> list[LiveOutput]:
    event_type = event.get("type")

    if event_type == "session.updated":
        return []
    if event_type == "input_audio_buffer.speech_started":
        return [LiveEvent("state.listening", _payload(event, "item_id"))]
    if event_type == "input_audio_buffer.committed":
        return [LiveEvent("state.thinking", _payload(event, "item_id"))]
    if event_type == "conversation.item.input_audio_transcription.delta":
        return [
            LiveEvent(
                "user.transcript.delta",
                _payload(event, "item_id", "text", "stash"),
            )
        ]
    if event_type == "conversation.item.input_audio_transcription.completed":
        return [
            LiveEvent(
                "user.transcript.final",
                _payload(event, "item_id", "transcript"),
            )
        ]
    if event_type == "response.audio_transcript.delta":
        return [
            LiveEvent("state.speaking"),
            LiveEvent(
                "assistant.transcript.delta",
                _payload(event, "item_id", "delta"),
            ),
        ]
    if event_type == "response.audio_transcript.done":
        return [
            LiveEvent(
                "assistant.transcript.final",
                _payload(event, "item_id", "transcript"),
            )
        ]
    if event_type == "response.audio.delta":
        try:
            pcm = base64.b64decode(event.get("delta", ""), validate=True)
        except (ValueError, TypeError):
            return [
                LiveEvent(
                    "session.error",
                    {
                        "code": "invalid_audio_frame",
                        "message": "实时语音服务返回了无法播放的音频片段",
                        "recoverable": True,
                    },
                )
            ]
        return [LiveEvent("state.speaking"), LiveAudio(pcm)]
    if event_type == "response.done":
        status = (event.get("response") or {}).get("status")
        if status == "cancelled":
            return [LiveEvent("response.interrupted")]
        if status == "completed":
            return [LiveEvent("response.completed")]
        return []
    if event_type == "error":
        error = event.get("error") or {}
        recoverable = error.get("type") == "server_error"
        return [
            LiveEvent(
                "session.error",
                {
                    "code": error.get("code") or error.get("type") or "upstream_error",
                    "message": (
                        "实时语音服务暂时不可用，请结束后重新开始"
                        if recoverable
                        else "实时语音请求参数无效，请结束通话后检查设置"
                    ),
                    "recoverable": recoverable,
                },
            )
        ]
    return []
