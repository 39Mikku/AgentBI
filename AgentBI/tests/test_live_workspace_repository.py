import unittest


class LiveWorkspaceRepositoryTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")

    def tearDown(self):
        self.repository.close()

    def _role(self, name: str = "角色"):
        return self.repository.create_live_role(
            {
                "user_id": "alice",
                "name": name,
                "instructions": f"你是{name}",
                "voice": "longanqian",
            }
        )

    def _thread(self, role=None):
        selected = role or self._role()
        return self.repository.create_live_conversation(
            {"user_id": "alice", "role_id": selected["id"]}
        )

    def test_roles_own_independent_conversation_lists(self):
        left = self._role("A")
        right = self.repository.create_live_role(
            {
                "user_id": "alice",
                "name": "B",
                "instructions": "你是B",
                "voice": "custom-voice-id",
                "avatar_data_url": "data:image/png;base64,AA==",
                "memory_enabled": True,
            }
        )
        self.repository.create_live_conversation(
            {"user_id": "alice", "role_id": left["id"]}
        )

        self.assertEqual(len(self.repository.list_live_conversations("alice", left["id"])), 1)
        self.assertEqual(self.repository.list_live_conversations("alice", right["id"]), [])
        self.assertEqual(right["voice"], "custom-voice-id")
        self.assertEqual(right["avatar_data_url"], "data:image/png;base64,AA==")
        self.assertTrue(right["memory_enabled"])

    def test_default_role_is_unique_and_cannot_be_deleted(self):
        first = self.repository.ensure_default_live_role("alice")
        second = self.repository.ensure_default_live_role("alice")

        self.assertEqual(first["id"], second["id"])
        self.assertFalse(self.repository.delete_live_role(first["id"], "alice"))

    def test_interrupted_messages_are_visible_but_not_replayable(self):
        thread = self._thread()
        self.repository.append_live_message(
            thread["id"], "alice", thread["role_id"], "user", "问题", "u1", "complete"
        )
        self.repository.append_live_message(
            thread["id"], "alice", thread["role_id"], "assistant", "部分回答", "a1", "interrupted"
        )

        self.assertEqual(len(self.repository.list_live_messages(thread["id"], "alice")), 2)
        self.assertEqual(self.repository.list_live_replay_messages(thread["id"], "alice", 0), [])

    def test_replay_limit_keeps_latest_complete_qa_pairs_in_order(self):
        thread = self._thread()
        for index in range(3):
            self.repository.append_live_message(
                thread["id"], "alice", thread["role_id"], "user", f"Q{index}", f"u{index}", "complete"
            )
            self.repository.append_live_message(
                thread["id"], "alice", thread["role_id"], "assistant", f"A{index}", f"a{index}", "complete"
            )

        replay = self.repository.list_live_replay_messages(thread["id"], "alice", 2)

        self.assertEqual([item["content"] for item in replay], ["Q1", "A1", "Q2", "A2"])

    def test_first_user_message_keeps_default_title_and_item_ids_are_idempotent(self):
        thread = self._thread()
        first = self.repository.append_live_message(
            thread["id"], "alice", thread["role_id"], "user", "这是第一条语音消息，用来作为标题", "u1", "complete"
        )
        repeated = self.repository.append_live_message(
            thread["id"], "alice", thread["role_id"], "user", "不应覆盖", "u1", "complete"
        )

        updated = self.repository.get_live_conversation(thread["id"], "alice")
        self.assertEqual(first["id"], repeated["id"])
        self.assertEqual(updated["title"], "新语音会话")

    def test_role_memory_can_be_disabled_without_clearing_content(self):
        role = self._role()
        saved = self.repository.save_live_role_memory("alice", role["id"], "用户喜欢咖啡", "m1")
        self.repository.update_live_role(role["id"], "alice", {"memory_enabled": False})

        memory = self.repository.get_live_role_memory("alice", role["id"])
        self.assertEqual(saved["content"], "用户喜欢咖啡")
        self.assertEqual(memory["content"], "用户喜欢咖啡")
        self.assertEqual(memory["last_message_id"], "m1")


if __name__ == "__main__":
    unittest.main()
