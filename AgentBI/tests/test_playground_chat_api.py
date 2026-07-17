import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.repositories.sqlite_playground_repository import SqlitePlaygroundRepository


class PlaygroundChatApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.playground_chat import router as chat_router
        from AgentBI.src.api.playground_conversations import router as conversation_router

        self.chat = SqliteChatRepository(":memory:")
        self.playground = SqlitePlaygroundRepository.from_connection_owner(self.chat)
        app = FastAPI()
        app.state.chat_repository = self.chat
        app.state.playground_repository = self.playground
        app.include_router(conversation_router)
        app.include_router(chat_router)
        self.client = TestClient(app)
        self.profile = self.playground.create_profile(
            {
                "user_id": "user-1",
                "profile_type": "character",
                "name": "芽衣",
                "main_prompt": "扮演芽衣。",
                "opening_message": "雨还在下。",
                "settings": {},
            }
        )

    def tearDown(self):
        self.chat.close()

    def test_router_exposes_stream_and_dag_endpoints(self):
        from AgentBI.src.api.playground_chat import router as chat_router
        from AgentBI.src.api.playground_conversations import router as conversation_router

        self.assertIn("/playground/chat/stream", {route.path for route in chat_router.routes})
        paths = {route.path for route in conversation_router.routes}
        self.assertIn("/playground/conversations", paths)
        self.assertIn("/playground/conversations/{conversation_id}/branches", paths)
        self.assertIn(
            "/playground/conversations/{conversation_id}/messages/{message_id}/retry", paths
        )
        self.assertIn(
            "/playground/conversations/{conversation_id}/messages/{message_id}/edit", paths
        )

    def test_create_conversation_writes_opening_message_and_keeps_profiles_isolated(self):
        response = self.client.post(
            "/playground/conversations",
            json={
                "user_id": "user-1",
                "profile_id": self.profile["_id"],
                "profile_type": "character",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        conversation = response.json()
        messages = self.client.get(
            f"/playground/conversations/{conversation['id']}/messages",
            params={"user_id": "user-1"},
        )
        listing = self.client.get(
            "/playground/conversations",
            params={
                "user_id": "user-1",
                "profile_id": self.profile["_id"],
                "profile_type": "character",
            },
        )

        self.assertEqual(messages.status_code, 200, messages.text)
        self.assertEqual(messages.json()[0]["content"], "雨还在下。")
        self.assertEqual(messages.json()[0]["role"], "assistant")
        self.assertEqual([item["id"] for item in listing.json()], [conversation["id"]])
        self.assertEqual(
            self.client.get(
                "/playground/conversations",
                params={
                    "user_id": "user-2",
                    "profile_id": self.profile["_id"],
                    "profile_type": "character",
                },
            ).json(),
            [],
        )

    def test_branch_copies_summary_with_remapped_checkpoints(self):
        conversation = self._create_conversation()
        user = self.chat.create_user_message(conversation["id"], "user-1", "继续")
        assistant = self.chat.create_assistant_message(
            conversation["id"], "user-1", user["_id"]
        )
        assistant = self.chat.complete_assistant_message(assistant["_id"], "她点了点头。")
        self.playground.save_summary(
            conversation["id"],
            "user-1",
            {
                "content": "SUMMARY",
                "summarized_through_message_id": user["_id"],
                "last_trigger_message_id": assistant["_id"],
            },
        )

        response = self.client.post(
            f"/playground/conversations/{conversation['id']}/branches",
            json={
                "user_id": "user-1",
                "source_message_id": assistant["_id"],
                "title": "分支",
            },
        )
        branch = response.json()
        copied = self.playground.get_summary(branch["id"], "user-1")

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(copied["content"], "SUMMARY")
        self.assertNotEqual(copied["summarized_through_message_id"], user["_id"])
        self.assertNotEqual(copied["last_trigger_message_id"], assistant["_id"])

    def test_stream_persists_visible_content_and_structured_metadata_separately(self):
        from AgentBI.src.services.playground.structured_output import StructuredTailResult

        provider = self.chat.create_provider(
            {
                "name": "provider",
                "base_url": "https://example.com/v1",
                "api_key": "key",
                "default_model": "model",
            }
        )
        self.playground.save_preferences(
            "user-1", {"provider_id": provider["_id"], "model": "model"}
        )
        self.playground.update_profile(
            self.profile["_id"],
            "user-1",
            {
                "settings": {
                    "state": {
                        "enabled": True,
                        "template": "custom",
                        "variables": [{"key": "mood", "type": "text", "label": "心情"}],
                    },
                    "action_options": {"enabled": True},
                }
            },
        )
        conversation = self._create_conversation()

        async def fake_stream(*args, **kwargs):
            yield {"type": "reasoning_summary", "content": "推理摘要"}
            yield {"type": "delta", "content": "她笑了。"}
            yield {
                "type": "structured",
                "result": StructuredTailResult(
                    visible_tail="",
                    state_snapshot={"mood": "安心"},
                    action_options=[
                        {"text": "靠近"},
                        {"text": "询问"},
                        {"text": "等待"},
                        {"text": "离开"},
                    ],
                    errors=[],
                ),
            }

        with patch(
            "AgentBI.src.api.playground_chat.PlaygroundRuntime.stream",
            new=fake_stream,
        ), patch(
            "AgentBI.src.api.playground_chat.MemoryService.generate_title",
            return_value=None,
        ):
            response = self.client.post(
                "/playground/chat/stream",
                json={
                    "user_id": "user-1",
                    "conversation_id": conversation["id"],
                    "profile_id": self.profile["_id"],
                    "content": "继续",
                },
            )

        messages = self.chat.list_messages(conversation["id"], "user-1")
        assistant = messages[-1]
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("event: state_snapshot", response.text)
        self.assertIn("event: action_options", response.text)
        self.assertEqual(assistant["content"], "她笑了。")
        self.assertEqual(assistant["reasoning_summary"], "推理摘要")
        self.assertEqual(assistant["metadata"]["state_snapshot"], {"mood": "安心"})
        self.assertEqual(len(assistant["metadata"]["action_options"]), 4)

    def _create_conversation(self):
        response = self.client.post(
            "/playground/conversations",
            json={
                "user_id": "user-1",
                "profile_id": self.profile["_id"],
                "profile_type": "character",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()


class _FakeStream:
    def __init__(self, chunks):
        self.chunks = chunks

    def __aiter__(self):
        self.iterator = iter(self.chunks)
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration as error:
            raise StopAsyncIteration from error


class _FakeCompletions:
    def __init__(self, calls):
        self.calls = calls

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        chunks = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(delta=SimpleNamespace(content="她笑了。", reasoning_content=None))
                ]
            )
        ]
        return _FakeStream(chunks)


class PlaygroundRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_never_sends_tools(self):
        from AgentBI.src.services.playground.runtime import PlaygroundRuntime

        calls = []
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions(calls)))
        with patch(
            "AgentBI.src.services.playground.runtime.create_openai_compatible_client",
            return_value=fake_client,
        ):
            events = [
                event
                async for event in PlaygroundRuntime().stream(
                    messages=[{"role": "user", "content": "继续"}],
                    provider={"api_key": "key", "base_url": "https://example.com/v1"},
                    model="model",
                    temperature=1.0,
                    thinking_level="medium",
                    expect_state=False,
                    expect_options=False,
                )
            ]

        self.assertNotIn("tools", calls[0])
        self.assertEqual(events[0], {"type": "delta", "content": "她笑了。"})
        self.assertEqual(events[-1]["type"], "structured")


if __name__ == "__main__":
    unittest.main()
