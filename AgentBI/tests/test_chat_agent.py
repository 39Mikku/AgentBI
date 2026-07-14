import unittest


class ChatAgentTests(unittest.TestCase):
    def test_chat_agent_exposes_only_email_delegation(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        names = {tool["function"]["name"] for tool in ChatAgent.tool_definitions()}
        self.assertEqual(names, {"delegate_email"})

    def test_email_delegation_description_leaves_recipient_lookup_to_the_subagent(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        delegate = next(tool["function"] for tool in ChatAgent.tool_definitions() if tool["function"]["name"] == "delegate_email")
        self.assertIn("子代理", delegate["description"])
        self.assertNotIn("调用前", delegate["description"])

    def test_chat_agent_uses_a_configurable_user_agent_header(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        self.assertIn("User-Agent", ChatAgent.client_headers())
        self.assertTrue(ChatAgent.client_headers()["User-Agent"])

    def test_runtime_context_wraps_only_the_latest_user_request(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        history = [
            {"role": "user", "content": "earlier request"},
            {"role": "assistant", "content": "earlier answer"},
            {"role": "user", "content": "what time is it?"},
        ]
        wrapped = ChatAgent.with_runtime_context(
            history,
            {"current_time": "2026-07-14 16:30:00", "timezone": "Asia/Shanghai", "locale": "zh-CN", "user_name": "Elysi"},
        )

        self.assertEqual(history[-1]["content"], "what time is it?")
        self.assertEqual(wrapped[:-1], history[:-1])
        self.assertIn("2026-07-14 16:30:00", wrapped[-1]["content"])
        self.assertIn("Elysi", wrapped[-1]["content"])
        self.assertTrue(wrapped[-1]["content"].endswith("what time is it?\n</user_request>"))


if __name__ == "__main__":
    unittest.main()
