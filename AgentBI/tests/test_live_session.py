import asyncio
import base64
import json
import unittest
from types import SimpleNamespace
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
    def __init__(self, response_events):
        self.response_events = list(response_events)
        self.pending_events = []
        self.sent = []
        self.audio_received = asyncio.Event()
        self.event_available = asyncio.Event()

    async def send(self, payload):
        decoded = json.loads(payload)
        self.sent.append(decoded)
        event_type = decoded.get("type")
        if event_type == "session.update":
            self.pending_events.append({"type": "session.updated"})
            self.event_available.set()
        elif event_type == "conversation.item.create":
            self.pending_events.append(
                {"type": "conversation.item.created", "event_id": decoded.get("event_id")}
            )
            self.event_available.set()
        elif event_type == "input_audio_buffer.append":
            self.pending_events.extend(self.response_events)
            self.response_events.clear()
            self.audio_received.set()
            self.event_available.set()

    async def recv(self):
        return await self.__anext__()

    def __aiter__(self):
        return self

    async def __anext__(self):
        while not self.pending_events:
            if self.audio_received.is_set():
                raise StopAsyncIteration
            self.event_available.clear()
            await self.event_available.wait()
        event = self.pending_events.pop(0)
        if not self.pending_events:
            self.event_available.clear()
        return json.dumps(event)


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
    async def test_session_uses_composed_instructions_before_forwarding_binary_pcm(self):
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
                max_history_turns=37,
            ),
        )

        self.assertEqual(
            connector.url,
            "wss://workspace-1.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime?model=qwen-audio-3.0-realtime-flash",
        )
        self.assertEqual(connector.headers, {"Authorization": "Bearer secret-key"})
        self.assertEqual(upstream.sent[0]["session"]["max_history_turns"], 37)
        self.assertEqual([item["type"] for item in upstream.sent[:2]], ["session.update", "input_audio_buffer.append"])
        self.assertEqual(base64.b64decode(upstream.sent[1]["audio"]), b"\x01\x02")
        self.assertEqual(frontend.sent_json[0], {"type": "session.ready"})
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
    def __init__(self, payload, repository=None):
        self.payload = payload
        self.accepted = False
        self.sent_json = []
        self.closed_with = None
        self.app = SimpleNamespace(state=SimpleNamespace(chat_repository=repository))

    async def accept(self):
        self.accepted = True

    async def receive_json(self):
        return self.payload

    async def send_json(self, payload):
        self.sent_json.append(payload)

    async def close(self, code=1000):
        self.closed_with = code


class LiveWebSocketRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_maintenance_schedules_title_even_when_memory_is_disabled(self):
        from AgentBI.src.api.live import _schedule_live_maintenance
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
        from AgentBI.src.services.live.conversation_service import LiveConversationService
        from AgentBI.src.services.live.protocol import LiveEvent

        repository = SqliteChatRepository(":memory:")
        role = repository.ensure_default_live_role("alice")
        conversation = repository.create_live_conversation(
            {"user_id": "alice", "role_id": role["id"]}
        )
        prepared = LiveConversationService(repository).prepare(
            "alice", role["id"], conversation["id"]
        )
        await prepared.recorder.handle(
            LiveEvent("user.transcript.final", {"item_id": "u1", "transcript": "你好"})
        )
        title = AsyncMock(return_value=None)
        with patch(
            "AgentBI.src.api.live.LiveTitleService.generate_after_call", title
        ):
            _schedule_live_maintenance(repository, prepared)
            await asyncio.sleep(0)

        title.assert_awaited_once_with("alice", role["id"], conversation["id"])
        repository.close()

    async def test_websocket_resolves_role_and_public_preferences(self):
        from AgentBI.src.api.live import live_websocket
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        repository = SqliteChatRepository(":memory:")
        role = repository.ensure_default_live_role("alice")
        role = repository.update_live_role(role["id"], "alice", {"memory_enabled": True})
        repository.save_live_role_memory("alice", role["id"], "用户偏好简短回答")
        conversation = repository.create_live_conversation(
            {"user_id": "alice", "role_id": role["id"]}
        )
        repository.save_live_preferences(
            "alice",
            {"model": "qwen-audio-3.0-realtime-plus", "max_history_turns": 33},
        )
        websocket = _FakeHandshakeWebSocket(
            {
                "type": "session.start",
                "role_id": role["id"],
                "conversation_id": conversation["id"],
            },
            repository,
        )
        session = AsyncMock()
        with (
            patch.dict(
                "os.environ",
                {"DASHSCOPE_API_KEY": "key", "DASHSCOPE_WORKSPACE_ID": "workspace"},
            ),
            patch("AgentBI.src.api.live.QwenAudioRealtimeSession", return_value=session) as session_class,
        ):
            await live_websocket(websocket, "alice")

        self.assertTrue(websocket.accepted)
        session_class.assert_called_once_with(api_key="key", workspace_id="workspace")
        session.run.assert_awaited_once()
        config = session.run.await_args.args[1]
        self.assertEqual(config.model, "qwen-audio-3.0-realtime-plus")
        self.assertEqual(config.voice, "longanqian")
        self.assertEqual(config.max_history_turns, 33)
        self.assertIn("<role_memory>", config.instructions)
        self.assertTrue(callable(session.run.await_args.kwargs["event_handler"]))
        self.assertEqual(websocket.sent_json[-1], {"type": "session.closed"})
        self.assertEqual(websocket.closed_with, 1000)
        repository.close()

    async def test_websocket_rejects_an_invalid_start_frame_without_connecting(self):
        from AgentBI.src.api.live import live_websocket

        websocket = _FakeHandshakeWebSocket(
            {"type": "session.start", "conversation_id": None}
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
