import unittest


class _ModelTasks:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def complete(self, *args):
        self.calls.append(args)
        return self.result


class LiveTitleServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")
        self.role = self.repository.ensure_default_live_role("alice")
        self.thread = self.repository.create_live_conversation(
            {"user_id": "alice", "role_id": self.role["id"]}
        )
        for index in range(2):
            self.repository.append_live_message(
                self.thread["id"], "alice", self.role["id"], "user", f"问题{index}", f"u{index}"
            )
            self.repository.append_live_message(
                self.thread["id"], "alice", self.role["id"], "assistant", f"回答{index}", f"a{index}"
            )
        self.repository.update_live_conversation(
            self.thread["id"], "alice", {"title": "新语音会话"}
        )

    async def asyncTearDown(self):
        self.repository.close()

    async def test_generates_sanitized_title_from_first_complete_pair(self):
        from AgentBI.src.services.live.title_service import LiveTitleService

        model_tasks = _ModelTasks("《旅行计划。》")
        updated = await LiveTitleService(self.repository, model_tasks).generate_after_call(
            "alice", self.role["id"], self.thread["id"]
        )

        self.assertEqual(updated["title"], "旅行计划")
        self.assertEqual(model_tasks.calls[0][1], "title")
        self.assertIn("问题0", model_tasks.calls[0][3])
        self.assertIn("回答0", model_tasks.calls[0][3])
        self.assertNotIn("问题1", model_tasks.calls[0][3])

    async def test_keeps_default_title_when_title_model_is_unavailable(self):
        from AgentBI.src.services.live.title_service import LiveTitleService

        updated = await LiveTitleService(
            self.repository, _ModelTasks(None)
        ).generate_after_call("alice", self.role["id"], self.thread["id"])

        self.assertIsNone(updated)
        self.assertEqual(
            self.repository.get_live_conversation(self.thread["id"], "alice")["title"],
            "新语音会话",
        )

    async def test_does_not_regenerate_a_user_renamed_title(self):
        from AgentBI.src.services.live.title_service import LiveTitleService

        self.repository.update_live_conversation(
            self.thread["id"], "alice", {"title": "我的标题"}
        )
        model_tasks = _ModelTasks("不应调用")

        updated = await LiveTitleService(self.repository, model_tasks).generate_after_call(
            "alice", self.role["id"], self.thread["id"]
        )

        self.assertIsNone(updated)
        self.assertEqual(model_tasks.calls, [])


if __name__ == "__main__":
    unittest.main()
