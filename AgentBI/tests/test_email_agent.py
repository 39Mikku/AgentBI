import unittest


class EmailAgentTests(unittest.TestCase):
    def test_email_agent_can_query_a_recipient_before_sending(self):
        from AgentBI.src.agents.email_agent import EmailAgent
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        names = {tool["function"]["name"] for tool in EmailAgent.tool_definitions()}
        self.assertEqual(names, {"lookup_recipient", "send_email"})
        repository = SqliteChatRepository(":memory:")
        try:
            repository.create_user("elysi@example.com", username="Elysi")
            result = EmailAgent(repository)._invoke_tool("lookup_recipient", '{"identity": "Elysi"}')
            self.assertIn("elysi@example.com", result)
        finally:
            repository.close()

    def test_chat_agent_delegates_email_work_instead_of_sending_directly(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        names = {tool["function"]["name"] for tool in ChatAgent.tool_definitions()}
        self.assertIn("delegate_email", names)
        self.assertNotIn("send_email", names)


if __name__ == "__main__":
    unittest.main()
