import unittest


class ChatPreferencesTests(unittest.TestCase):
    def test_preference_response_is_scoped_to_one_user(self):
        from AgentBI.src.schemas.chat_schema import ChatPreferencesResponse

        response = ChatPreferencesResponse.from_document(
            {
                "user_id": "user@example.com",
                "provider_id": "provider-1",
                "model": "model-1",
                "temperature": 1.1,
                "context_turns": 12,
                "thinking_level": "high",
            }
        )

        self.assertEqual(response.user_id, "user@example.com")
        self.assertEqual(response.model, "model-1")
        self.assertEqual(response.temperature, 1.1)
        self.assertEqual(response.thinking_level, "high")

    def test_preference_response_defaults_thinking_level_to_medium(self):
        from AgentBI.src.schemas.chat_schema import ChatPreferencesResponse

        response = ChatPreferencesResponse.from_document({"user_id": "user@example.com"})

        self.assertEqual(response.thinking_level, "medium")


if __name__ == "__main__":
    unittest.main()
