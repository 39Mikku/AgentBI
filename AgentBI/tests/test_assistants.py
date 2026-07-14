import unittest


class AssistantCapabilityTests(unittest.TestCase):
    def test_default_assistant_enables_every_registered_capability(self):
        from AgentBI.src.agents.assistant_registry import DEFAULT_ASSISTANT_CAPABILITIES, enabled_capabilities

        capabilities = enabled_capabilities(DEFAULT_ASSISTANT_CAPABILITIES)

        self.assertEqual([capability["id"] for capability in capabilities], ["agent.email"])

    def test_unknown_capabilities_are_not_exposed_to_the_model(self):
        from AgentBI.src.agents.assistant_registry import enabled_capabilities

        self.assertEqual(enabled_capabilities(["agent.email", "tool.unknown"]), [
            {
                "id": "agent.email",
                "name": "邮件子代理",
                "kind": "subagent",
                "description": "撰写邮件、查询联系人并发送邮件。",
                "prompt": "需要撰写或发送邮件时，调用 delegate_email 委派给邮件子代理。",
            },
        ])


if __name__ == "__main__":
    unittest.main()
