import unittest

from pydantic import ValidationError


class PlaygroundRepositoryTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
        from AgentBI.src.repositories.sqlite_playground_repository import SqlitePlaygroundRepository

        self.chat = SqliteChatRepository(":memory:")
        self.repository = SqlitePlaygroundRepository.from_connection_owner(self.chat)

    def tearDown(self):
        self.chat.close()

    def test_profile_resources_and_preferences_are_user_scoped(self):
        preferences = self.repository.save_preferences(
            "user-1",
            {
                "provider_id": "provider-1",
                "model": "roleplay-model",
                "temperature": 1.0,
                "context_turns": 24,
                "thinking_level": "high",
                "summary_trigger_messages": 20,
                "summary_retain_messages": 6,
            },
        )
        profile = self.repository.create_profile(
            {
                "user_id": "user-1",
                "profile_type": "character",
                "name": "芽衣",
                "main_prompt": "扮演芽衣",
                "opening_message": "雨还在下。",
                "settings": {"action_options": {"enabled": True}},
            }
        )
        self.repository.replace_prompt_modules(
            profile["_id"],
            "user-1",
            [
                {
                    "name": "文风",
                    "content": "克制描写",
                    "enabled": True,
                    "injection_position": "system_end",
                    "sort_order": 10,
                }
            ],
        )
        self.repository.upsert_persona(
            profile["_id"],
            "user-1",
            {
                "name": "舰长",
                "identity_text": "旅行者",
                "background": "",
                "personality": "",
                "initial_relationship": "初次见面",
                "enabled": True,
                "injection_position": "system_end",
            },
        )
        self.repository.replace_context_entries(
            profile["_id"],
            "user-1",
            [
                {
                    "name": "学园",
                    "category": "地点",
                    "content": "极东支部",
                    "enabled": True,
                    "activation_mode": "keyword",
                    "keywords": ["学园"],
                    "scan_depth": 8,
                    "injection_position": "system_end",
                    "priority": 20,
                }
            ],
        )

        self.assertEqual(preferences["model"], "roleplay-model")
        self.assertEqual(self.repository.get_profile(profile["_id"], "user-1")["name"], "芽衣")
        self.assertEqual(self.repository.list_profiles("user-2"), [])
        self.assertEqual(self.repository.list_prompt_modules(profile["_id"], "user-1")[0]["name"], "文风")
        self.assertEqual(self.repository.get_persona(profile["_id"], "user-1")["name"], "舰长")
        self.assertEqual(self.repository.list_context_entries(profile["_id"], "user-1")[0]["keywords"], ["学园"])

    def test_conversation_summary_keeps_dual_checkpoints(self):
        conversation = self.chat.create_conversation(
            {
                "user_id": "user-1",
                "title": "长会话",
                "workspace_type": "playground",
                "owner_type": "world",
                "owner_id": "world-1",
            }
        )
        stored = self.repository.save_summary(
            conversation["_id"],
            "user-1",
            {
                "content": "## 关键事件时间线\n- 相遇",
                "status": "idle",
                "summarized_through_message_id": "message-8",
                "last_trigger_message_id": "message-12",
                "trigger_new_message_count": 24,
                "retain_recent_message_count": 8,
                "injection_position": "system_end",
            },
        )

        self.assertEqual(stored["summarized_through_message_id"], "message-8")
        self.assertEqual(stored["last_trigger_message_id"], "message-12")
        self.assertEqual(self.repository.get_summary(conversation["_id"], "user-2")["content"], "")

    def test_request_schemas_forbid_unknown_fields_and_invalid_profile_settings(self):
        from AgentBI.src.schemas.playground_schema import PlaygroundProfileCreate

        payload = {
            "user_id": "user-1",
            "profile_type": "character",
            "name": "芽衣",
            "settings": {
                "state": {
                    "enabled": True,
                    "template": "romance",
                    "variables": [
                        {
                            "key": "affection",
                            "type": "progress",
                            "label": "好感",
                            "minimum": 0,
                            "maximum": 100,
                        }
                    ],
                }
            },
        }

        model = PlaygroundProfileCreate.model_validate(payload)
        self.assertEqual(model.settings.state.template, "romance")

        with self.assertRaises(ValidationError):
            PlaygroundProfileCreate.model_validate({**payload, "unexpected": True})

        with self.assertRaises(ValidationError):
            PlaygroundProfileCreate.model_validate(
                {
                    **payload,
                    "settings": {
                        "state": {
                            "enabled": True,
                            "template": "romance",
                            "variables": [
                                {
                                    "key": "affection",
                                    "type": "text",
                                    "label": "好感",
                                }
                            ],
                        }
                    },
                }
            )

    def test_state_template_validation_keeps_protected_keys_and_types(self):
        from AgentBI.src.services.playground.state_templates import validate_state_variables

        variables = validate_state_variables(
            "adventure",
            [
                {
                    "key": "hp",
                    "type": "progress",
                    "label": "生命值",
                    "initial_value": 80,
                },
                {
                    "key": "reputation",
                    "type": "progress",
                    "label": "声望",
                    "minimum": -100,
                    "maximum": 100,
                },
            ],
        )
        self.assertEqual(variables[0]["label"], "生命值")
        self.assertEqual(variables[-1]["key"], "reputation")

        with self.assertRaises(ValueError):
            validate_state_variables(
                "adventure",
                [{"key": "hp", "type": "text", "label": "生命"}],
            )


if __name__ == "__main__":
    unittest.main()
