import unittest


class ModelReasoningTests(unittest.TestCase):
    def test_gemini_options_keep_existing_extension_shape(self):
        from AgentBI.src.services.model_reasoning import model_reasoning_request_options

        self.assertEqual(
            model_reasoning_request_options("gemini-3.5-flash", "high"),
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

    def test_deepseek_v4_maps_ui_modes_to_official_reasoning_options(self):
        from AgentBI.src.services.model_reasoning import model_reasoning_request_options

        self.assertEqual(
            model_reasoning_request_options("deepseek-v4-flash", "off"),
            {"extra_body": {"thinking": {"type": "disabled"}}},
        )
        self.assertEqual(
            model_reasoning_request_options("deepseek-v4-pro", "low"),
            {
                "reasoning_effort": "high",
                "extra_body": {"thinking": {"type": "enabled"}},
            },
        )
        self.assertEqual(
            model_reasoning_request_options("deepseek-v4-pro", "high"),
            {
                "reasoning_effort": "max",
                "extra_body": {"thinking": {"type": "enabled"}},
            },
        )

    def test_deepseek_medium_uses_low_ui_semantics_and_unrelated_models_are_untouched(self):
        from AgentBI.src.services.model_reasoning import model_reasoning_request_options

        self.assertEqual(
            model_reasoning_request_options("deepseek-v4-pro", "medium")["reasoning_effort"],
            "high",
        )
        self.assertEqual(model_reasoning_request_options("deepseek-reasoner", "high"), {})
        self.assertEqual(model_reasoning_request_options("deepseek-v3", "high"), {})


if __name__ == "__main__":
    unittest.main()
