import unittest
from unittest.mock import patch


class ToolboxTtsRegistryTests(unittest.TestCase):
    def test_registry_exposes_only_approved_models_and_voice_kinds(self):
        from AgentBI.src.services.toolbox.tts.registry import TtsProviderRegistry

        registry = TtsProviderRegistry.from_environment()
        providers = {item["id"]: item for item in registry.capabilities()}

        self.assertEqual(
            [item["id"] for item in providers["bailian"]["models"]],
            ["cosyvoice-v3.5-plus", "cosyvoice-v3.5-flash"],
        )
        self.assertEqual(providers["bailian"]["builtin_voices"], [])
        self.assertEqual(
            [item["id"] for item in providers["volcengine"]["models"]],
            ["doubao-seed-tts-2.0", "doubao-seed-icl-2.0"],
        )
        self.assertEqual(providers["mimo"]["models"][0]["voice_kinds"], ["builtin"])

    def test_registry_reports_missing_configuration_without_secret_values(self):
        from AgentBI.src.services.toolbox.tts.registry import TtsProviderRegistry

        with patch.dict("os.environ", {}, clear=True):
            providers = {item["id"]: item for item in TtsProviderRegistry.from_environment().capabilities()}

        self.assertFalse(providers["minimax"]["configured"])
        self.assertIn("MINIMAX_API_KEY", providers["minimax"]["missing_configuration"])
        self.assertFalse(providers["volcengine"]["configured"])
        with patch.dict(
            "os.environ",
            {
                "MINIMAX_API_KEY": "secret-minimax-value",
                "DASHSCOPE_API_KEY": "secret-bailian-value",
                "DASHSCOPE_WORKSPACE_ID": "workspace",
                "MIMO_API_KEY": "secret-mimo-value",
                "VOLCENGINE_TTS_APP_ID": "app",
                "VOLCENGINE_TTS_ACCESS_TOKEN": "secret-volc-value",
            },
            clear=True,
        ):
            serialized = repr(TtsProviderRegistry.from_environment().capabilities())
        self.assertNotIn("secret-minimax-value", serialized)
        self.assertNotIn("secret-volc-value", serialized)

    def test_registry_rejects_unknown_provider(self):
        from AgentBI.src.services.toolbox.tts.base import TtsValidationError
        from AgentBI.src.services.toolbox.tts.registry import TtsProviderRegistry

        with self.assertRaises(TtsValidationError):
            TtsProviderRegistry.from_environment().get("unknown")


if __name__ == "__main__":
    unittest.main()
