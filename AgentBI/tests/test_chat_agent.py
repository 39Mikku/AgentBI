import unittest


class ChatAgentTests(unittest.TestCase):
    def test_default_chat_agent_exposes_registered_subagent_delegations(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        names = {tool["function"]["name"] for tool in ChatAgent.tool_definitions()}
        self.assertEqual(names, {"delegate_email", "delegate_music", "delegate_bilibili"})

    def test_music_delegation_is_exposed_only_when_capability_is_mounted(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        disabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.email"])}
        enabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.music"])}

        self.assertEqual(disabled, {"delegate_email"})
        self.assertEqual(enabled, {"delegate_music"})

    def test_bilibili_delegation_is_exposed_only_when_capability_is_mounted(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        disabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.email"])}
        enabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.bilibili"])}

        self.assertEqual(disabled, {"delegate_email"})
        self.assertEqual(enabled, {"delegate_bilibili"})

    def test_subagents_are_resolved_from_one_registry(self):
        from AgentBI.src.agents.assistant_registry import create_subagent, get_subagent_registration
        from AgentBI.src.agents.email_agent import EmailAgent
        from AgentBI.src.agents.music_agent import MusicAgent
        from AgentBI.src.agents.bilibili_agent import BilibiliAgent

        music_registration = get_subagent_registration("delegate_music")

        self.assertEqual(music_registration.display_name, "音乐子代理")
        self.assertIsInstance(create_subagent("delegate_music", music_client=object()), MusicAgent)
        self.assertIsInstance(create_subagent("delegate_email", repository=object()), EmailAgent)
        self.assertIsInstance(
            create_subagent("delegate_bilibili", dependencies={"bilibili_client": object()}),
            BilibiliAgent,
        )
        self.assertIsNone(create_subagent("delegate_unknown"))

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

    def test_runtime_context_can_be_disabled_without_leaving_prompt_instructions(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        messages = ChatAgent("answer tersely", [], include_runtime_context=False).build_request_messages(
            [{"role": "user", "content": "hello"}],
            {"current_time": "2026-07-14 16:30:00"},
        )

        self.assertNotIn("runtime_context", messages[0]["content"])
        self.assertEqual(messages[1]["content"], "hello")

    def test_history_search_tool_is_exposed_only_when_enabled(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        disabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions([], False)}
        enabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions([], True)}

        self.assertEqual(disabled, set())
        self.assertEqual(enabled, {"search_assistant_history"})

    def test_memory_and_compressed_context_are_separate_system_sections(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        messages = ChatAgent(
            "answer tersely",
            [],
            include_runtime_context=False,
            memory_summary="the user prefers Chinese",
            context_summary="we already selected SQLite",
        ).build_request_messages([{"role": "user", "content": "continue"}], {})

        self.assertIn("<assistant_memory>", messages[0]["content"])
        self.assertIn("the user prefers Chinese", messages[0]["content"])
        self.assertIn("<conversation_summary>", messages[0]["content"])
        self.assertIn("we already selected SQLite", messages[0]["content"])


class ChatAgentHistoryFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_provider_failure_does_not_abort_the_main_chat(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        class FailingMemoryService:
            async def search_history(self, *args, **kwargs):
                raise RuntimeError("batch size is invalid")

        result = await ChatAgent(
            capability_ids=[],
            memory_service=FailingMemoryService(),
            user_id="user",
            assistant={"_id": "assistant", "history_search_enabled": True},
        )._search_history('{"query":"previous decision"}')

        self.assertIn("历史会话检索失败", result)
        self.assertIn("batch size is invalid", result)


if __name__ == "__main__":
    unittest.main()
