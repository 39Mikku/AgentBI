import unittest


class LiveConversationPreparationTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")
        self.role = self.repository.ensure_default_live_role("alice")
        self.repository.update_live_role(
            self.role["id"], "alice", {"memory_enabled": True}
        )
        self.repository.save_live_role_memory(
            "alice", self.role["id"], "用户喜欢咖啡"
        )
        self.thread = self.repository.create_live_conversation(
            {"user_id": "alice", "role_id": self.role["id"]}
        )
        for index in range(2):
            self.repository.append_live_message(
                self.thread["id"], "alice", self.role["id"], "user", f"Q{index}", f"u{index}"
            )
            self.repository.append_live_message(
                self.thread["id"], "alice", self.role["id"], "assistant", f"A{index}", f"a{index}"
            )

    def tearDown(self):
        self.repository.close()

    def test_existing_conversation_injects_memory_then_limited_history(self):
        from AgentBI.src.services.live.conversation_service import LiveConversationService

        self.repository.save_live_preferences("alice", {"history_context_turns": 1})
        prepared = LiveConversationService(self.repository).prepare(
            "alice", self.role["id"], self.thread["id"]
        )

        self.assertIn("<role_memory>\n用户喜欢咖啡", prepared.config.instructions)
        self.assertIn("用户：Q1\n助手：A1", prepared.config.instructions)
        self.assertNotIn("用户：Q0", prepared.config.instructions)

    def test_new_empty_conversation_does_not_inject_history(self):
        from AgentBI.src.services.live.conversation_service import LiveConversationService

        empty = self.repository.create_live_conversation(
            {"user_id": "alice", "role_id": self.role["id"]}
        )
        prepared = LiveConversationService(self.repository).prepare(
            "alice", self.role["id"], empty["id"]
        )

        self.assertIn("<role_memory>", prepared.config.instructions)

    def test_disabled_memory_is_not_injected_but_remains_stored(self):
        from AgentBI.src.services.live.conversation_service import LiveConversationService

        self.repository.update_live_role(self.role["id"], "alice", {"memory_enabled": False})
        prepared = LiveConversationService(self.repository).prepare(
            "alice", self.role["id"], self.thread["id"]
        )

        self.assertNotIn("<role_memory>", prepared.config.instructions)
        self.assertEqual(
            self.repository.get_live_role_memory("alice", self.role["id"])["content"],
            "用户喜欢咖啡",
        )

    def test_foreign_or_mismatched_conversation_is_rejected(self):
        from AgentBI.src.services.live.conversation_service import (
            LiveConversationService,
            LiveWorkspaceError,
        )

        other = self.repository.create_live_role(
            {"user_id": "alice", "name": "Other", "instructions": "Other", "voice": "longanqian"}
        )

        with self.assertRaises(LiveWorkspaceError):
            LiveConversationService(self.repository).prepare(
                "bob", self.role["id"], self.thread["id"]
            )
        with self.assertRaises(LiveWorkspaceError):
            LiveConversationService(self.repository).prepare(
                "alice", other["id"], self.thread["id"]
            )

    def test_registered_live_voice_must_match_current_realtime_model(self):
        from AgentBI.src.services.live.conversation_service import (
            LiveConversationService,
            LiveWorkspaceError,
        )

        remote_id = "qwen-audio-3.0-realtime-plus-livevoice-001"
        self.repository.create_toolbox_tts_voice({
            "user_id": "alice",
            "provider": "bailian",
            "display_name": "Plus narrator",
            "external_voice_id": remote_id,
            "voice_kind": "cloned",
            "bound_model": "qwen-audio-3.0-realtime-plus",
            "provider_metadata": {"usage": "live"},
        })
        self.repository.update_live_role(self.role["id"], "alice", {"voice": remote_id})

        self.repository.save_live_preferences(
            "alice", {"model": "qwen-audio-3.0-realtime-plus"}
        )
        prepared = LiveConversationService(self.repository).prepare(
            "alice", self.role["id"], self.thread["id"]
        )
        self.assertEqual(prepared.config.voice, remote_id)

        self.repository.save_live_preferences(
            "alice", {"model": "qwen-audio-3.0-realtime-flash"}
        )
        with self.assertRaisesRegex(LiveWorkspaceError, "voice.*model"):
            LiveConversationService(self.repository).prepare(
                "alice", self.role["id"], self.thread["id"]
            )

    def test_unregistered_manual_voice_id_remains_supported(self):
        from AgentBI.src.services.live.conversation_service import LiveConversationService

        self.repository.update_live_role(
            self.role["id"], "alice", {"voice": "manually-created-voice-id"}
        )
        prepared = LiveConversationService(self.repository).prepare(
            "alice", self.role["id"], self.thread["id"]
        )
        self.assertEqual(prepared.config.voice, "manually-created-voice-id")


class LiveCallRecorderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
        from AgentBI.src.services.live.conversation_service import LiveConversationService

        self.repository = SqliteChatRepository(":memory:")
        self.role = self.repository.ensure_default_live_role("alice")
        self.thread = self.repository.create_live_conversation(
            {"user_id": "alice", "role_id": self.role["id"]}
        )
        prepared = LiveConversationService(self.repository).prepare(
            "alice", self.role["id"], self.thread["id"]
        )
        self.recorder = prepared.recorder

    async def asyncTearDown(self):
        self.repository.close()

    async def test_deltas_do_not_persist_and_final_events_are_idempotent(self):
        from AgentBI.src.services.live.protocol import LiveEvent

        await self.recorder.handle(
            LiveEvent("user.transcript.delta", {"item_id": "u1", "text": "你"})
        )
        first = await self.recorder.handle(
            LiveEvent("user.transcript.final", {"item_id": "u1", "transcript": "你好"})
        )
        repeated = await self.recorder.handle(
            LiveEvent("user.transcript.final", {"item_id": "u1", "transcript": "你好"})
        )

        messages = self.repository.list_live_messages(self.thread["id"], "alice")
        self.assertEqual(len(messages), 1)
        self.assertEqual(first.payload["message_id"], repeated.payload["message_id"])
        self.assertEqual(first.payload["conversation_id"], self.thread["id"])

    async def test_interruption_persists_current_assistant_buffer_but_not_as_complete(self):
        from AgentBI.src.services.live.protocol import LiveEvent

        await self.recorder.handle(
            LiveEvent("assistant.transcript.delta", {"item_id": "a1", "delta": "部分"})
        )
        interrupted = await self.recorder.handle(LiveEvent("response.interrupted"))

        messages = self.repository.list_live_messages(self.thread["id"], "alice")
        self.assertEqual(messages[0]["content"], "部分")
        self.assertEqual(messages[0]["status"], "interrupted")
        self.assertEqual(interrupted.payload["message_id"], messages[0]["id"])
        self.assertFalse(self.recorder.has_new_complete_messages)

    async def test_assistant_final_replaces_buffer_and_marks_call_for_memory(self):
        from AgentBI.src.services.live.protocol import LiveEvent

        await self.recorder.handle(
            LiveEvent("assistant.transcript.delta", {"item_id": "a1", "delta": "你"})
        )
        final = await self.recorder.handle(
            LiveEvent("assistant.transcript.final", {"item_id": "a1", "transcript": "你好"})
        )

        self.assertTrue(self.recorder.has_new_complete_messages)
        self.assertEqual(self.recorder.last_complete_message_id, final.payload["message_id"])


if __name__ == "__main__":
    unittest.main()
