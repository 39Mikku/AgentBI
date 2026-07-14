import unittest


class ChatAgentTests(unittest.TestCase):
    def test_chat_agent_exposes_existing_email_and_mongo_tools(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        names = {tool["function"]["name"] for tool in ChatAgent.tool_definitions()}
        self.assertEqual(names, {"mongo_query", "send_email"})


if __name__ == "__main__":
    unittest.main()
