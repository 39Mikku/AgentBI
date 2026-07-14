import unittest


class ChatCoreTests(unittest.TestCase):
    def test_normalize_model_ids_removes_invalid_duplicates_and_sorts(self):
        from AgentBI.src.services.provider_service import normalize_model_ids

        payload = {
            "data": [
                {"id": "zeta"},
                {"id": "alpha"},
                {"id": "zeta"},
                {"id": ""},
                {"name": "missing-id"},
            ]
        }

        self.assertEqual(normalize_model_ids(payload), ["alpha", "zeta"])

    def test_build_context_keeps_the_latest_complete_turns(self):
        from AgentBI.src.services.chat_service import build_context_messages

        messages = [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "one answer"},
            {"role": "user", "content": "two"},
            {"role": "assistant", "content": "two answer"},
            {"role": "user", "content": "three"},
        ]

        self.assertEqual(
            build_context_messages(messages, context_turns=1),
            [
                {"role": "assistant", "content": "two answer"},
                {"role": "user", "content": "three"},
            ],
        )

    def test_sse_event_encoder_has_an_event_name_and_json_payload(self):
        from AgentBI.src.services.chat_service import encode_sse_event

        self.assertEqual(
            encode_sse_event("delta", {"content": "Hello"}),
            'event: delta\\ndata: {"content":"Hello"}\\n\\n',
        )


if __name__ == "__main__":
    unittest.main()
