import unittest


class PlaygroundContextTests(unittest.TestCase):
    def test_lorebook_injects_every_constant_and_match_without_trimming(self):
        from AgentBI.src.services.playground.context_entries import resolve_context_entries

        entries = [
            {
                "_id": "low",
                "enabled": True,
                "activation_mode": "constant",
                "content": "LOW",
                "injection_position": "system_end",
                "priority": 1,
            },
            {
                "_id": "high",
                "enabled": True,
                "activation_mode": "keyword",
                "keywords": ["学园"],
                "scan_depth": 4,
                "content": "HIGH",
                "injection_position": "system_end",
                "priority": 99,
            },
            {
                "_id": "disabled",
                "enabled": False,
                "activation_mode": "constant",
                "content": "DISABLED",
                "injection_position": "system_end",
                "priority": 200,
            },
        ]
        path = [{"role": "user", "content": "回到学园"}]

        resolved = resolve_context_entries(entries, path)

        self.assertEqual([item["_id"] for item in resolved], ["high", "low"])

    def test_keyword_scan_depth_is_counted_in_messages_and_case_insensitive(self):
        from AgentBI.src.services.playground.context_entries import resolve_context_entries

        entry = {
            "_id": "entry",
            "enabled": True,
            "activation_mode": "keyword",
            "keywords": ["Moon Gate"],
            "scan_depth": 2,
            "content": "MATCH",
            "injection_position": "system_end",
            "priority": 0,
        }
        old = [
            {"role": "user", "content": "MOON GATE"},
            {"role": "assistant", "content": "one"},
            {"role": "user", "content": "two"},
        ]
        recent = [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "moon gate"},
            {"role": "user", "content": "new"},
        ]

        self.assertEqual(resolve_context_entries([entry], old), [])
        self.assertEqual(len(resolve_context_entries([entry], recent)), 1)

    def test_prompt_modules_wrap_only_the_latest_user_message(self):
        from AgentBI.src.services.playground.prompt_composer import PlaygroundPromptComposer

        assembly = PlaygroundPromptComposer().compose(
            profile={"main_prompt": "ROLE", "settings": {}},
            active_path=[
                {"_id": "old", "role": "user", "content": "old", "status": "complete"},
                {"_id": "reply", "role": "assistant", "content": "reply", "status": "complete"},
                {"_id": "latest", "role": "user", "content": "latest", "status": "complete"},
            ],
            modules=[
                {
                    "_id": "before",
                    "content": "BEFORE",
                    "enabled": True,
                    "injection_position": "before_latest_user",
                    "sort_order": 0,
                },
                {
                    "_id": "after",
                    "content": "AFTER",
                    "enabled": True,
                    "injection_position": "after_latest_user",
                    "sort_order": 0,
                },
            ],
            persona=None,
            context_entries=[],
            summary=None,
            previous_state=None,
        )

        self.assertEqual(sum("BEFORE" in str(item["content"]) for item in assembly.messages), 1)
        self.assertEqual(sum("AFTER" in str(item["content"]) for item in assembly.messages), 1)
        contents = [item["content"] for item in assembly.messages]
        self.assertLess(contents.index("BEFORE"), contents.index("latest"))
        self.assertLess(contents.index("latest"), contents.index("AFTER"))

    def test_summary_replaces_only_messages_through_its_valid_boundary(self):
        from AgentBI.src.services.playground.prompt_composer import PlaygroundPromptComposer

        assembly = PlaygroundPromptComposer().compose(
            profile={
                "main_prompt": "ROLE",
                "settings": {"summary": {"enabled": True, "injection_position": "system_end"}},
            },
            active_path=[
                {"_id": "u1", "role": "user", "content": "old user", "status": "complete"},
                {"_id": "a1", "role": "assistant", "content": "old reply", "status": "complete"},
                {"_id": "u2", "role": "user", "content": "recent user", "status": "complete"},
                {"_id": "a2", "role": "assistant", "content": "recent reply", "status": "complete"},
            ],
            modules=[],
            persona=None,
            context_entries=[],
            summary={"content": "SUMMARY", "summarized_through_message_id": "a1"},
            previous_state=None,
            context_turns=1,
        )

        serialized = "\n".join(item["content"] for item in assembly.messages)
        self.assertIn("SUMMARY", serialized)
        self.assertNotIn("old user", serialized)
        self.assertNotIn("old reply", serialized)
        self.assertIn("recent user", serialized)
        self.assertIn("recent reply", serialized)

    def test_state_and_options_protocols_do_not_serialize_message_metadata(self):
        from AgentBI.src.services.playground.prompt_composer import PlaygroundPromptComposer

        assembly = PlaygroundPromptComposer().compose(
            profile={
                "main_prompt": "ROLE",
                "settings": {
                    "state": {
                        "enabled": True,
                        "template": "custom",
                        "variables": [{"key": "mood", "type": "text", "label": "心情"}],
                        "update_instructions": "心情随剧情更新。",
                    },
                    "action_options": {"enabled": True, "style_prompt": "四种选择应明显不同。"},
                },
            },
            active_path=[
                {
                    "_id": "u1",
                    "role": "user",
                    "content": "继续",
                    "status": "complete",
                    "metadata": {"action_options": [{"text": "污染"}]},
                }
            ],
            modules=[],
            persona=None,
            context_entries=[],
            summary=None,
            previous_state={"mood": "平静"},
        )

        serialized = "\n".join(item["content"] for item in assembly.messages)
        self.assertIn("<agentbi_state>", serialized)
        self.assertIn("<agentbi_options>", serialized)
        self.assertIn('"mood": "平静"', serialized)
        self.assertNotIn("污染", serialized)


if __name__ == "__main__":
    unittest.main()
