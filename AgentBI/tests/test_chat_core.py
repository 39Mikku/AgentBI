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

    def test_zero_context_turns_keeps_the_full_message_history(self):
        from AgentBI.src.services.chat_service import build_context_messages

        messages = [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "one answer"},
            {"role": "user", "content": "two"},
        ]

        self.assertEqual(build_context_messages(messages, context_turns=0), messages)

    def test_sse_event_encoder_has_an_event_name_and_json_payload(self):
        from AgentBI.src.services.chat_service import encode_sse_event

        self.assertEqual(
            encode_sse_event("delta", {"content": "Hello"}),
            'event: delta\ndata: {"content":"Hello"}\n\n',
        )

    def test_timeline_keeps_content_and_tool_events_in_emission_order(self):
        from AgentBI.src.services.chat_service import append_timeline_event

        timeline = []
        append_timeline_event(timeline, "delta", {"content": "先说明。"})
        append_timeline_event(timeline, "tool_started", {"tool": "lookup_recipient"})
        append_timeline_event(timeline, "delta", {"content": "再汇报。"})

        self.assertEqual(
            timeline,
            [
                {"type": "delta", "content": "先说明。"},
                {"type": "tool_started", "tool": "lookup_recipient"},
                {"type": "delta", "content": "再汇报。"},
            ],
        )

    def test_timeline_keeps_card_events_between_streamed_text(self):
        from AgentBI.src.services.chat_service import append_timeline_event

        timeline = []
        append_timeline_event(timeline, "delta", {"content": "先给你找几首。"})
        append_timeline_event(
            timeline,
            "card",
            {
                "kind": "music.track-list",
                "payload": {"tracks": [{"id": "1", "name": "Song"}]},
            },
        )
        append_timeline_event(timeline, "delta", {"content": "点卡片即可播放。"})

        self.assertEqual(
            timeline,
            [
                {"type": "delta", "content": "先给你找几首。"},
                {
                    "type": "card",
                    "kind": "music.track-list",
                    "payload": {"tracks": [{"id": "1", "name": "Song"}]},
                },
                {"type": "delta", "content": "点卡片即可播放。"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
