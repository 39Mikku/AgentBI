import unittest


class PlaygroundStructuredOutputTests(unittest.TestCase):
    def test_parser_hides_protocol_json_split_across_chunks(self):
        from AgentBI.src.services.playground.structured_output import StructuredTailParser

        parser = StructuredTailParser(
            expect_state=True,
            expect_options=True,
            variable_definitions=[
                {"key": "affection", "type": "progress", "minimum": 0, "maximum": 100}
            ],
            previous_state={"affection": 3},
        )
        visible = "".join(
            [
                parser.feed("她推开门。<agentbi_st"),
                parser.feed('ate>{"affection":4}</agentbi_state><agentbi_options>'),
                parser.feed(
                    '[{"text":"进入"},{"text":"等待"},{"text":"离开"},{"text":"询问"}]'
                    "</agentbi_options>"
                ),
            ]
        )
        result = parser.finish()

        self.assertEqual(visible + result.visible_tail, "她推开门。")
        self.assertEqual(result.state_snapshot["affection"], 4)
        self.assertEqual(len(result.action_options), 4)

    def test_state_normalizer_keeps_fixed_keys_and_previous_values(self):
        from AgentBI.src.services.playground.state_templates import normalize_state_snapshot

        definitions = [
            {"key": "affection", "type": "progress", "minimum": 0, "maximum": 100},
            {"key": "mood", "type": "text"},
        ]
        normalized = normalize_state_snapshot(
            definitions,
            {"affection": 3, "mood": "平静"},
            {"affection": 105, "invented": "discard"},
        )

        self.assertEqual(normalized, {"affection": 100, "mood": "平静"})

    def test_malformed_protocol_is_hidden_and_reported(self):
        from AgentBI.src.services.playground.structured_output import StructuredTailParser

        parser = StructuredTailParser(expect_state=False, expect_options=True)
        visible = parser.feed("正文<agentbi_options>{invalid")
        result = parser.finish()

        self.assertEqual(visible + result.visible_tail, "正文")
        self.assertIsNone(result.action_options)
        self.assertTrue(result.errors)

    def test_options_require_exactly_four_nonempty_text_items(self):
        from AgentBI.src.services.playground.structured_output import StructuredTailParser

        parser = StructuredTailParser(expect_state=False, expect_options=True)
        parser.feed(
            '<agentbi_options>{"options":[{"text":"一"},{"text":"二"},{"text":"三"}]}'
            "</agentbi_options>"
        )
        result = parser.finish()

        self.assertIsNone(result.action_options)
        self.assertIn("恰好四个", result.errors[0])

    def test_disabled_protocol_tag_remains_ordinary_visible_text(self):
        from AgentBI.src.services.playground.structured_output import StructuredTailParser

        parser = StructuredTailParser(expect_state=False, expect_options=False)
        visible = parser.feed("提到 agentbi 并不是协议。<agentbi_state>{}</agentbi_state>")
        result = parser.finish()

        self.assertEqual(
            visible + result.visible_tail,
            "提到 agentbi 并不是协议。<agentbi_state>{}</agentbi_state>",
        )
        self.assertEqual(result.errors, [])

    def test_state_only_parser_preserves_missing_list_from_previous_snapshot(self):
        from AgentBI.src.services.playground.structured_output import StructuredTailParser

        parser = StructuredTailParser(
            expect_state=True,
            expect_options=False,
            variable_definitions=[
                {"key": "mood", "type": "text", "initial_value": "未知"},
                {"key": "items", "type": "list", "initial_value": []},
            ],
            previous_state={"mood": "平静", "items": ["钥匙"]},
        )
        parser.feed('<agentbi_state>{"mood":"紧张","invented":1}</agentbi_state>')
        result = parser.finish()

        self.assertEqual(result.state_snapshot, {"mood": "紧张", "items": ["钥匙"]})
        self.assertIsNone(result.action_options)


if __name__ == "__main__":
    unittest.main()
