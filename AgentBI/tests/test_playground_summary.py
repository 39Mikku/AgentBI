import unittest
from types import SimpleNamespace
from unittest.mock import patch

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.repositories.sqlite_playground_repository import SqlitePlaygroundRepository


def message(identifier: str, role: str = "user"):
    return {"_id": identifier, "role": role, "content": f"message {identifier}", "status": "complete"}


class PlaygroundSummaryCheckpointTests(unittest.TestCase):
    def test_retained_messages_do_not_immediately_retrigger_summary(self):
        from AgentBI.src.services.playground.summarizer import count_messages_after_trigger

        path = [message(str(index)) for index in range(30)]
        summary = {
            "summarized_through_message_id": "21",
            "last_trigger_message_id": "29",
            "trigger_new_message_count": 6,
        }

        self.assertEqual(count_messages_after_trigger(path, summary), 0)

    def test_summary_becomes_stale_when_active_path_changes_at_absorbed_boundary(self):
        from AgentBI.src.services.playground.summarizer import summary_is_stale

        path = [message("0"), message("1"), message("replacement")]
        summary = {"summarized_through_message_id": "2", "last_trigger_message_id": "2"}

        self.assertTrue(summary_is_stale(path, summary))


class _FakeCompletions:
    def __init__(self, calls):
        self.calls = calls

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="## 关键事件时间线\n- 更新"))]
        )


class _FakeClient:
    def __init__(self, calls):
        self.chat = SimpleNamespace(completions=_FakeCompletions(calls))


class PlaygroundSummarizerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from AgentBI.src.services.playground.summarizer import PlaygroundSummarizer

        self.chat = SqliteChatRepository(":memory:")
        self.repository = SqlitePlaygroundRepository.from_connection_owner(self.chat)
        self.provider = self.chat.create_provider(
            {
                "name": "provider",
                "base_url": "https://example.com/v1",
                "api_key": "key",
                "default_model": "chat-model",
            }
        )
        self.profile = self.repository.create_profile(
            {
                "user_id": "user-1",
                "profile_type": "character",
                "name": "角色",
                "settings": {
                    "summary": {
                        "enabled": True,
                        "trigger_new_message_count": 4,
                        "retain_recent_message_count": 2,
                    }
                },
            }
        )
        self.thread = self.chat.create_conversation(
            {
                "user_id": "user-1",
                "title": "长会话",
                "workspace_type": "playground",
                "owner_type": "character",
                "owner_id": self.profile["_id"],
            }
        )
        last_user = None
        for index in range(4):
            if index % 2 == 0:
                last_user = self.chat.create_user_message(
                    self.thread["_id"], "user-1", f"user {index}"
                )
            else:
                pending = self.chat.create_assistant_message(
                    self.thread["_id"], "user-1", last_user["_id"]
                )
                self.chat.complete_assistant_message(pending["_id"], f"assistant {index}")
        self.preferences = {
            "provider_id": self.provider["_id"],
            "model": "chat-model",
            "summary_provider_id": None,
            "summary_model": None,
            "summary_trigger_messages": 24,
            "summary_retain_messages": 8,
        }
        self.calls = []
        self.summarizer = PlaygroundSummarizer(self.chat, self.repository)

    async def asyncTearDown(self):
        self.chat.close()

    async def test_maintenance_updates_one_summary_and_both_checkpoints(self):
        with patch(
            "AgentBI.src.services.playground.summarizer.create_openai_compatible_client",
            return_value=_FakeClient(self.calls),
        ):
            result = await self.summarizer.maintain_after_reply(
                self.thread,
                self.profile,
                self.preferences,
            )

        path = self.chat.get_active_path(self.thread["_id"], "user-1")
        visible = [item for item in path if item.get("role") in {"user", "assistant"}]
        self.assertEqual(result["status"], "idle")
        self.assertEqual(result["summarized_through_message_id"], visible[-3]["_id"])
        self.assertEqual(result["last_trigger_message_id"], visible[-1]["_id"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["temperature"], 1.0)

    async def test_background_failure_preserves_last_valid_content_and_checkpoints(self):
        current = self.repository.save_summary(
            self.thread["_id"],
            "user-1",
            {
                "content": "VALID",
                "summarized_through_message_id": "old-boundary",
                "last_trigger_message_id": "old-trigger",
                "trigger_new_message_count": 4,
                "retain_recent_message_count": 2,
            },
        )

        with patch.object(self.summarizer, "_generate", side_effect=RuntimeError("offline")):
            result = await self.summarizer.maintain_after_reply(
                self.thread,
                self.profile,
                self.preferences,
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["content"], current["content"])
        self.assertEqual(
            result["summarized_through_message_id"], current["summarized_through_message_id"]
        )


if __name__ == "__main__":
    unittest.main()
