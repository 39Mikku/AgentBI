import unittest

from fastapi import HTTPException


class CapabilitySettingsRepositoryTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")

    def tearDown(self):
        self.repository.close()

    def test_settings_are_shared_by_user_but_isolated_by_capability(self):
        self.repository.save_capability_config(
            "elysia@example.com",
            "agent.music",
            {"search_result_limit": 5, "daily_result_limit": 12},
        )
        self.repository.save_capability_config(
            "elysia@example.com",
            "agent.bilibili",
            {"default_result_limit": 3, "creator_scan_limit": 30},
        )

        self.assertEqual(
            self.repository.get_capability_config("elysia@example.com", "agent.music")["search_result_limit"],
            5,
        )
        self.assertEqual(
            self.repository.get_capability_config("elysia@example.com", "agent.bilibili")["default_result_limit"],
            3,
        )
        self.assertIsNone(self.repository.get_capability_config("other@example.com", "agent.music"))


class CapabilitySettingsSchemaTests(unittest.TestCase):
    def test_each_subagent_has_its_own_validated_defaults(self):
        from AgentBI.src.schemas.capability_settings_schema import (
            BilibiliSubagentConfig,
            MusicSubagentConfig,
            TavilySearchConfig,
        )

        self.assertEqual(MusicSubagentConfig().search_result_limit, 3)
        self.assertEqual(MusicSubagentConfig().daily_result_limit, 10)
        self.assertEqual(MusicSubagentConfig().liked_result_limit, 20)
        self.assertEqual(BilibiliSubagentConfig().default_result_limit, 3)
        self.assertEqual(BilibiliSubagentConfig().creator_scan_limit, 20)
        self.assertEqual(TavilySearchConfig().max_results, 5)
        self.assertEqual(TavilySearchConfig().search_depth, "basic")

    def test_api_validation_rejects_values_outside_the_target_subagent_schema(self):
        from AgentBI.src.api.capability_settings import validate_capability_config

        with self.assertRaises(HTTPException) as context:
            validate_capability_config("agent.music", {"search_result_limit": 99})

        self.assertEqual(context.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
