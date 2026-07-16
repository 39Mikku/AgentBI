import json
import unittest
from types import SimpleNamespace


class ChatAgentTests(unittest.TestCase):
    def test_default_chat_agent_exposes_registered_subagent_delegations(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        names = {tool["function"]["name"] for tool in ChatAgent.tool_definitions()}
        self.assertEqual(
            names,
            {"delegate_email", "delegate_music", "delegate_bilibili", "search_web", "generate_image", "generate_video"},
        )

    def test_web_search_is_exposed_only_when_direct_tool_is_mounted(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        disabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.email"])}
        enabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["tool.web_search"])}

        self.assertEqual(disabled, {"delegate_email"})
        self.assertEqual(enabled, {"search_web"})

    def test_image_generation_is_exposed_only_when_direct_tool_is_mounted(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        disabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.email"])}
        enabled = {
            tool["function"]["name"]
            for tool in ChatAgent.tool_definitions(["tool.image_generation"])
        }

        self.assertEqual(disabled, {"delegate_email"})
        self.assertEqual(enabled, {"generate_image"})

    def test_music_delegation_is_exposed_only_when_capability_is_mounted(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        disabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.email"])}
        enabled = {tool["function"]["name"] for tool in ChatAgent.tool_definitions(["agent.music"])}

        self.assertEqual(disabled, {"delegate_email"})
        self.assertEqual(enabled, {"delegate_music"})

    def test_music_capability_tells_main_agent_to_resolve_descriptive_song_requests_first(self):
        from AgentBI.src.agents.assistant_registry import capability_prompt

        prompt = capability_prompt(["agent.music", "tool.web_search"])

        self.assertIn("非具体歌名", prompt)
        self.assertIn("search_web", prompt)
        self.assertLess(prompt.index("search_web"), prompt.index("delegate_music"))

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

    def test_subagent_instruction_excludes_multimodal_base64_payloads(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        instruction = ChatAgent._delegated_instruction(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "把图片内容写进邮件"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,VERY_LARGE_SECRET_DATA"},
                        },
                    ],
                }
            ],
            '{"instruction":"发送邮件"}',
            "邮件任务",
        )

        self.assertIn("把图片内容写进邮件", instruction)
        self.assertNotIn("base64", instruction)
        self.assertNotIn("VERY_LARGE_SECRET_DATA", instruction)

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


class ChatAgentGeminiThinkingTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_tool_loop_applies_gemini_thinking_options(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        class Chunks:
            def __aiter__(self):
                return self

            async def __anext__(self):
                if hasattr(self, "sent"):
                    raise StopAsyncIteration
                self.sent = True
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(
                                content="answer",
                                reasoning_content="summary",
                                tool_calls=[],
                            )
                        )
                    ]
                )

        class Completions:
            async def create(self, **kwargs):
                self.request = kwargs
                return Chunks()

        completions = Completions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        events = [
            event
            async for event in ChatAgent(capability_ids=[])._stream_tool_loop(
                client,
                [{"role": "user", "content": "question"}],
                "gemini-3.5-flash",
                1.0,
                {},
                "high",
            )
        ]

        self.assertEqual(
            completions.request["extra_body"]["extra_body"]["google"]["thinking_config"],
            {"thinking_level": "high", "include_thoughts": True},
        )
        self.assertEqual([event["type"] for event in events], ["delta", "reasoning_summary"])

    async def test_tool_call_message_preserves_deepseek_reasoning_content(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        class Chunks:
            def __aiter__(self):
                return self

            async def __anext__(self):
                if hasattr(self, "sent"):
                    raise StopAsyncIteration
                self.sent = True
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(
                                content=None,
                                reasoning_content="private reasoning state",
                                tool_calls=[
                                    SimpleNamespace(
                                        index=0,
                                        id="call-1",
                                        function=SimpleNamespace(name="unknown_tool", arguments="{}"),
                                    )
                                ],
                            )
                        )
                    ]
                )

        class Completions:
            async def create(self, **kwargs):
                return Chunks()

        messages = [{"role": "user", "content": "question"}]
        client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
        events = [
            event
            async for event in ChatAgent(capability_ids=[])._stream_tool_loop(
                client,
                messages,
                "deepseek-v4-pro",
                1.0,
                {},
                "high",
            )
        ]

        self.assertEqual(messages[1]["reasoning_content"], "private reasoning state")
        self.assertIn("reasoning_summary", [event["type"] for event in events])


class ChatAgentWebSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_web_search_uses_its_own_capability_config(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        class Repository:
            def get_capability_config(self, user_id, capability_id):
                self.request = (user_id, capability_id)
                return {"max_results": 4, "search_depth": "fast"}

        class SearchClient:
            async def search(self, query, **options):
                self.request = (query, options)
                return {
                    "query": query,
                    "results": [{"title": "Result", "url": "https://example.com", "content": "Answer", "score": 0.9}],
                }

        repository = Repository()
        search_client = SearchClient()
        result = await ChatAgent(
            capability_ids=["tool.web_search"],
            repository=repository,
            user_id="user@example.com",
            web_search_client=search_client,
        )._invoke_direct_tool("search_web", '{"query":"current news","topic":"news"}')

        self.assertEqual(repository.request, ("user@example.com", "tool.web_search"))
        self.assertEqual(search_client.request[0], "current news")
        self.assertEqual(search_client.request[1]["max_results"], 4)
        self.assertEqual(search_client.request[1]["search_depth"], "fast")
        self.assertEqual(search_client.request[1]["topic"], "news")
        self.assertEqual(json.loads(result)["results"][0]["url"], "https://example.com")


class ChatAgentImageGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_image_tool_receives_current_provider_and_conversation_scope(self):
        from AgentBI.src.agents.chat_agent import ChatAgent
        from AgentBI.src.schemas.image_generation_schema import GeneratedImage

        class Repository:
            def get_capability_config(self, user_id, capability_id):
                return {"mode": "lite", "lite_model": "gemini-image", "pro_quality": "high"}

        class ImageService:
            async def generate(self, **kwargs):
                self.request = kwargs
                return GeneratedImage(
                    id="image-1",
                    url="/api/generated-images/hash/chat/image-1.png",
                    relative_path="hash/chat/image-1.png",
                    media_type="image/png",
                    mode="lite",
                    model="gemini-image",
                    aspect_ratio="landscape",
                    prompt=kwargs["prompt"],
                )

        service = ImageService()
        provider = {"_id": "provider-1", "api_key": "key", "base_url": "https://example.com/v1"}
        result = await ChatAgent(
            capability_ids=["tool.image_generation"],
            repository=Repository(),
            user_id="user@example.com",
            conversation_id="conversation-1",
            image_generation_service=service,
        )._invoke_direct_tool(
            "generate_image",
            '{"prompt":"planned prompt","aspect_ratio":"landscape"}',
            provider,
        )

        self.assertEqual(service.request["provider"], provider)
        self.assertEqual(service.request["scope_id"], "conversation-1")
        self.assertEqual(result.card["kind"], "image.generated")

    async def test_direct_image_tool_rejects_missing_prompt_before_upstream_call(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        result = await ChatAgent(capability_ids=["tool.image_generation"])._invoke_direct_tool(
            "generate_image", '{"aspect_ratio":"square"}', {}
        )

        self.assertIn("提示词", result)


if __name__ == "__main__":
    unittest.main()
