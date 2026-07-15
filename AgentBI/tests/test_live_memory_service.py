import unittest


class _FakeModelTasks:
    def __init__(self, result="更新后的长期记忆"):
        self.result = result
        self.calls = []

    async def complete(self, user_id, role, system, prompt):
        self.calls.append(
            {"user_id": user_id, "role": role, "system": system, "prompt": prompt}
        )
        return self.result


class LiveMemoryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")
        self.role = self.repository.ensure_default_live_role("alice")
        self.repository.update_live_role(
            self.role["id"], "alice", {"memory_enabled": True}
        )
        self.thread = self.repository.create_live_conversation(
            {"user_id": "alice", "role_id": self.role["id"]}
        )
        self.user_message = self.repository.append_live_message(
            self.thread["id"], "alice", self.role["id"], "user", "我喜欢咖啡", "u1"
        )
        self.assistant_message = self.repository.append_live_message(
            self.thread["id"], "alice", self.role["id"], "assistant", "记住了", "a1"
        )

    async def asyncTearDown(self):
        self.repository.close()

    async def test_one_call_makes_at_most_one_memory_completion(self):
        from AgentBI.src.services.live.memory_service import LiveMemoryService

        model = _FakeModelTasks()
        service = LiveMemoryService(self.repository, model)

        first = await service.update_after_call(
            "alice", self.role["id"], self.assistant_message["id"]
        )
        second = await service.update_after_call(
            "alice", self.role["id"], self.assistant_message["id"]
        )

        self.assertEqual(len(model.calls), 1)
        self.assertEqual(first["content"], "更新后的长期记忆")
        self.assertEqual(second["last_message_id"], self.assistant_message["id"])

    async def test_disabled_memory_is_neither_updated_nor_cleared(self):
        from AgentBI.src.services.live.memory_service import LiveMemoryService

        self.repository.save_live_role_memory(
            "alice", self.role["id"], "保留内容", self.user_message["id"]
        )
        self.repository.update_live_role(
            self.role["id"], "alice", {"memory_enabled": False}
        )
        model = _FakeModelTasks()

        result = await LiveMemoryService(self.repository, model).update_after_call(
            "alice", self.role["id"], self.assistant_message["id"]
        )

        self.assertIsNone(result)
        self.assertEqual(model.calls, [])
        self.assertEqual(
            self.repository.get_live_role_memory("alice", self.role["id"])["content"],
            "保留内容",
        )

    async def test_missing_model_or_empty_result_preserves_marker_and_memory(self):
        from AgentBI.src.services.live.memory_service import LiveMemoryService

        existing = self.repository.save_live_role_memory(
            "alice", self.role["id"], "旧记忆", self.user_message["id"]
        )

        result = await LiveMemoryService(
            self.repository, _FakeModelTasks(result=None)
        ).update_after_call("alice", self.role["id"], self.assistant_message["id"])

        current = self.repository.get_live_role_memory("alice", self.role["id"])
        self.assertIsNone(result)
        self.assertEqual(current["content"], existing["content"])
        self.assertEqual(current["last_message_id"], existing["last_message_id"])

    async def test_refresh_reprocesses_all_complete_role_messages(self):
        from AgentBI.src.services.live.memory_service import LiveMemoryService

        self.repository.save_live_role_memory(
            "alice", self.role["id"], "旧记忆", self.assistant_message["id"]
        )
        model = _FakeModelTasks("重新提炼")

        refreshed = await LiveMemoryService(self.repository, model).refresh(
            "alice", self.role["id"]
        )

        self.assertEqual(len(model.calls), 1)
        self.assertIn("我喜欢咖啡", model.calls[0]["prompt"])
        self.assertEqual(refreshed["content"], "重新提炼")


if __name__ == "__main__":
    unittest.main()
