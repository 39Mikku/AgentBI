import unittest


class LiveContextTests(unittest.TestCase):
    def test_memory_and_chronological_history_are_appended_to_instructions(self):
        from AgentBI.src.services.live.context import compose_live_instructions

        instructions = compose_live_instructions(
            "你是温柔的旅行搭档。",
            "用户喜欢咖啡",
            [
                {"role": "user", "content": "继续昨天的话题"},
                {"role": "assistant", "content": "可以"},
            ],
        )

        self.assertTrue(instructions.startswith("你是温柔的旅行搭档。"))
        self.assertIn("<role_memory>\n用户喜欢咖啡\n</role_memory>", instructions)
        self.assertIn("用户：继续昨天的话题\n助手：可以", instructions)
        self.assertLess(instructions.index("<role_memory>"), instructions.index("<conversation_history>"))

    def test_empty_context_keeps_role_instructions_unchanged(self):
        from AgentBI.src.services.live.context import compose_live_instructions

        self.assertEqual(compose_live_instructions("保持简洁。", "", []), "保持简洁。")


if __name__ == "__main__":
    unittest.main()
