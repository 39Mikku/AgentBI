import asyncio
import base64
import json
import unittest
from unittest.mock import AsyncMock, patch


class _FakeFrontend:
    def __init__(self, frames):
        self.frames = list(frames)
        self.sent_json = []
        self.sent_bytes = []

    async def receive(self):
        if self.frames:
            return self.frames.pop(0)
        await asyncio.Future()

    async def send_json(self, payload):
        self.sent_json.append(payload)

    async def send_bytes(self, payload):
        self.sent_bytes.append(payload)


class _FakeUpstream:
    def __init__(self, events):
        self.events = list(events)
        self.sent = []
        self.audio_received = asyncio.Event()

    async def send(self, payload):
        decoded = json.loads(payload)
        self.sent.append(decoded)
        if decoded.get("type") == "input_audio_buffer.append":
            self.audio_received.set()

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.audio_received.wait()
        if not self.events:
            raise StopAsyncIteration
        return json.dumps(self.events.pop(0))


class _FakeConnection:
    def __init__(self, upstream):
        self.upstream = upstream
        self.closed = False

    async def __aenter__(self):
        return self.upstream

    async def __aexit__(self, exc_type, exc, traceback):
        self.closed = True


class _FakeConnector:
    def __init__(self, connection):
        self.connection = connection
        self.url = ""
        self.headers = {}

    def __call__(self, url, *, additional_headers):
        self.url = url
        self.headers = additional_headers
        return self.connection


class LiveSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_configures_upstream_and_forwards_binary_pcm_both_ways(self):
        from AgentBI.src.services.live.qwen_audio_realtime import (
            LiveSessionConfig,
            QwenAudioRealtimeSession,
        )

        output_pcm = b"\x10\x20\x30\x40"
        frontend = _FakeFrontend(
            [{"type": "websocket.receive", "bytes": b"\x01\x02", "text": None}]
        )
        upstream = _FakeUpstream(
            [
                {"type": "session.updated"},
                {
                    "type": "response.audio.delta",
                    "delta": base64.b64encode(output_pcm).decode(),
                },
            ]
        )
        connection = _FakeConnection(upstream)
        connector = _FakeConnector(connection)
        session = QwenAudioRealtimeSession(
            api_key="secret-key",
            workspace_id="workspace-1",
            connector=connector,
        )

        await session.run(
            frontend,
            LiveSessionConfig(
                model="qwen-audio-3.0-realtime-flash",
                voice="longanlingxi",
                instructions="保持口语化。",
            ),
        )

        self.assertEqual(
            connector.url,
            "wss://workspace-1.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime?model=qwen-audio-3.0-realtime-flash",
        )
        self.assertEqual(connector.headers, {"Authorization": "Bearer secret-key"})
        self.assertEqual(
            upstream.sent[0],
            {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "voice": "longanlingxi",
                    "instructions": "保持口语化。",
                    "turn_detection": {"type": "smart_turn"},
                    "max_history_turns": 20,
                },
            },
        )
        self.assertEqual(
            base64.b64decode(upstream.sent[1]["audio"]),
            b"\x01\x02",
        )
        self.assertIn({"type": "session.ready"}, frontend.sent_json)
        self.assertEqual(frontend.sent_bytes, [output_pcm])
        self.assertTrue(connection.closed)

    async def test_missing_credentials_fail_before_connecting(self):
        from AgentBI.src.services.live.qwen_audio_realtime import (
            LiveConfigurationError,
            QwenAudioRealtimeSession,
        )

        with self.assertRaises(LiveConfigurationError):
            QwenAudioRealtimeSession(api_key="", workspace_id="workspace-1")
        with self.assertRaises(LiveConfigurationError):
            QwenAudioRealtimeSession(api_key="secret", workspace_id="")


class _FakeHandshakeWebSocket:
    def __init__(self, payload):
        self.payload = payload
        self.accepted = False
        self.sent_json = []
        self.closed_with = None

    async def accept(self):
        self.accepted = True

    async def receive_json(self):
        return self.payload

    async def send_json(self, payload):
        self.sent_json.append(payload)

    async def close(self, code=1000):
        self.closed_with = code


class LiveWebSocketRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_websocket_validates_start_frame_and_runs_qwen_session(self):
        from AgentBI.src.api.live import live_websocket

        websocket = _FakeHandshakeWebSocket(
            {
                "type": "session.start",
                "model": "qwen-audio-3.0-realtime-plus",
                "voice": "longanlingxin",
                "instructions": "保持自然口语。",
            }
        )
        session = AsyncMock()
        with (
            patch.dict(
                "os.environ",
                {
                    "DASHSCOPE_API_KEY": "key",
                    "DASHSCOPE_WORKSPACE_ID": "workspace",
                },
            ),
            patch(
                "AgentBI.src.api.live.QwenAudioRealtimeSession",
                return_value=session,
            ) as session_class,
        ):
            await live_websocket(websocket, "alice")

        self.assertTrue(websocket.accepted)
        session_class.assert_called_once_with(api_key="key", workspace_id="workspace")
        session.run.assert_awaited_once()
        config = session.run.await_args.args[1]
        self.assertEqual(config.model, "qwen-audio-3.0-realtime-plus")
        self.assertEqual(config.voice, "longanlingxin")
        self.assertEqual(websocket.sent_json[-1], {"type": "session.closed"})
        self.assertEqual(websocket.closed_with, 1000)

    async def test_websocket_rejects_an_invalid_start_frame_without_connecting(self):
        from AgentBI.src.api.live import live_websocket

        websocket = _FakeHandshakeWebSocket(
            {
                "type": "session.start",
                "model": "unknown",
                "voice": "longanqian",
                "instructions": "hello",
            }
        )
        with patch("AgentBI.src.api.live.QwenAudioRealtimeSession") as session_class:
            await live_websocket(websocket, "alice")

        session_class.assert_not_called()
        self.assertEqual(websocket.sent_json[0]["type"], "session.error")
        self.assertEqual(websocket.sent_json[0]["code"], "invalid_session_start")
        self.assertFalse(websocket.sent_json[0]["recoverable"])
        self.assertEqual(websocket.closed_with, 1008)


if __name__ == "__main__":
    unittest.main()
