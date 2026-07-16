import unittest


class GeminiThinkingTests(unittest.TestCase):
    def test_only_supported_gemini_text_models_enable_thinking(self):
        from AgentBI.src.services.gemini_thinking import supports_gemini_thinking

        self.assertTrue(supports_gemini_thinking("gemini-2.5-pro"))
        self.assertTrue(supports_gemini_thinking("models/gemini-3.5-flash"))
        self.assertFalse(supports_gemini_thinking("gemini-2.0-flash"))
        self.assertFalse(supports_gemini_thinking("gemini-3-pro-image-preview"))
        self.assertFalse(supports_gemini_thinking("deepseek-v4-pro"))

    def test_request_options_use_the_verified_google_extension_shape(self):
        from AgentBI.src.services.gemini_thinking import gemini_request_options

        self.assertEqual(
            gemini_request_options("gemini-3.5-flash", "high"),
            {
                "extra_body": {
                    "extra_body": {
                        "google": {
                            "thinking_config": {
                                "thinking_level": "high",
                                "include_thoughts": True,
                            }
                        }
                    }
                }
            },
        )
        self.assertEqual(gemini_request_options("deepseek-v4-pro", "high"), {})

    def test_unknown_level_falls_back_to_medium(self):
        from AgentBI.src.services.gemini_thinking import normalize_thinking_level

        self.assertEqual(normalize_thinking_level(None), "medium")
        self.assertEqual(normalize_thinking_level("unsupported"), "medium")


if __name__ == "__main__":
    unittest.main()
