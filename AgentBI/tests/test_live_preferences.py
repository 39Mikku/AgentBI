import unittest

from pydantic import ValidationError


class LivePreferenceRepositoryTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")

    def tearDown(self):
        self.repository.close()

    def test_live_preferences_have_stable_defaults_and_are_isolated_by_user(self):
        alice_defaults = self.repository.get_live_preferences("alice")

        self.assertEqual(alice_defaults["model"], "qwen-audio-3.0-realtime-flash")
        self.assertEqual(alice_defaults["voice"], "longanqian")
        self.assertIn("口语", alice_defaults["instructions"])

        self.repository.save_live_preferences(
            "alice",
            {
                "model": "qwen-audio-3.0-realtime-plus",
                "voice": "longanlingxi",
                "instructions": "你是一位实时语音主持人。",
            },
        )

        self.assertEqual(
            self.repository.get_live_preferences("alice")["model"],
            "qwen-audio-3.0-realtime-plus",
        )
        self.assertEqual(
            self.repository.get_live_preferences("bob")["model"],
            "qwen-audio-3.0-realtime-flash",
        )

    def test_partial_live_preference_updates_keep_existing_values(self):
        self.repository.save_live_preferences("alice", {"voice": "longanxiaoxin"})
        updated = self.repository.save_live_preferences(
            "alice", {"instructions": "只说简洁的纯文本。"}
        )

        self.assertEqual(updated["model"], "qwen-audio-3.0-realtime-flash")
        self.assertEqual(updated["voice"], "longanxiaoxin")
        self.assertEqual(updated["instructions"], "只说简洁的纯文本。")


class LivePreferenceSchemaTests(unittest.TestCase):
    def test_live_preferences_accept_only_supported_models_and_voices(self):
        from AgentBI.src.api.live import LivePreferencesUpdate

        with self.assertRaises(ValidationError):
            LivePreferencesUpdate(
                model="unknown-model",
                voice="longanqian",
                instructions="hello",
            )

        with self.assertRaises(ValidationError):
            LivePreferencesUpdate(
                model="qwen-audio-3.0-realtime-flash",
                voice="unknown-voice",
                instructions="hello",
            )

    def test_live_preferences_reject_blank_or_oversized_instructions(self):
        from AgentBI.src.api.live import LivePreferencesUpdate

        with self.assertRaises(ValidationError):
            LivePreferencesUpdate(
                model="qwen-audio-3.0-realtime-flash",
                voice="longanqian",
                instructions="   ",
            )

        with self.assertRaises(ValidationError):
            LivePreferencesUpdate(
                model="qwen-audio-3.0-realtime-flash",
                voice="longanqian",
                instructions="x" * 12001,
            )


if __name__ == "__main__":
    unittest.main()
