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
        self.assertEqual(alice_defaults["history_context_turns"], 12)
        self.assertEqual(alice_defaults["max_history_turns"], 20)

        self.repository.save_live_preferences(
            "alice",
            {
                "model": "qwen-audio-3.0-realtime-plus",
                "history_context_turns": 0,
                "max_history_turns": 36,
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
        self.repository.save_live_preferences("alice", {"history_context_turns": 0})
        updated = self.repository.save_live_preferences(
            "alice", {"max_history_turns": 50}
        )

        self.assertEqual(updated["model"], "qwen-audio-3.0-realtime-flash")
        self.assertEqual(updated["history_context_turns"], 0)
        self.assertEqual(updated["max_history_turns"], 50)

    def test_default_live_role_inherits_legacy_voice_and_instructions(self):
        role = self.repository.ensure_default_live_role("alice")

        self.assertEqual(role["voice"], "longanqian")
        self.assertIn("口语", role["instructions"])
        self.assertTrue(role["is_default"])


class LivePreferenceSchemaTests(unittest.TestCase):
    def test_live_preferences_accept_only_supported_models_and_history_ranges(self):
        from AgentBI.src.api.live import LivePreferencesUpdate

        payload = LivePreferencesUpdate(
            model="qwen-audio-3.0-realtime-flash",
            history_context_turns=0,
            max_history_turns=50,
        )
        self.assertEqual(payload.history_context_turns, 0)

        with self.assertRaises(ValidationError):
            LivePreferencesUpdate(
                model="unknown-model",
                history_context_turns=12,
                max_history_turns=20,
            )

        with self.assertRaises(ValidationError):
            LivePreferencesUpdate(
                model="qwen-audio-3.0-realtime-flash",
                history_context_turns=51,
                max_history_turns=20,
            )

    def test_live_role_accepts_custom_voice_but_rejects_blank_fields(self):
        from AgentBI.src.api.live import LiveRoleCreate

        payload = LiveRoleCreate(
            user_id="alice",
            name="旅行伙伴",
            instructions="自然地交流",
            voice="clone-voice-001",
        )
        self.assertEqual(payload.voice, "clone-voice-001")

        with self.assertRaises(ValidationError):
            LiveRoleCreate(
                user_id="alice",
                name="旅行伙伴",
                instructions="自然地交流",
                voice="   ",
            )


if __name__ == "__main__":
    unittest.main()
