import unittest


class EmailAgentTests(unittest.TestCase):
    def test_email_agent_can_query_a_recipient_before_sending(self):
        from AgentBI.src.agents.email_agent import EmailAgent

        names = {tool["function"]["name"] for tool in EmailAgent.tool_definitions()}
        self.assertEqual(names, {"mongo_query", "send_email"})

    def test_chat_agent_delegates_email_work_instead_of_sending_directly(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        names = {tool["function"]["name"] for tool in ChatAgent.tool_definitions()}
        self.assertEqual(names, {"delegate_email"})


if __name__ == "__main__":
    unittest.main()
