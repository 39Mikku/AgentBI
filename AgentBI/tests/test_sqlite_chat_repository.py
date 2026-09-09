import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SqliteChatRepositoryTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")
        self.assistant = self.repository.ensure_default_assistant("local-user")
        self.thread = self.repository.create_conversation(
            {"user_id": "local-user", "title": "Test", "assistant_id": self.assistant["_id"]}
        )

    def tearDown(self):
        self.repository.close()

    def test_active_path_persists_a_complete_conversation(self):
        user = self.repository.create_user_message(self.thread["_id"], "local-user", "Hello")
        reply = self.repository.create_assistant_message(self.thread["_id"], "local-user", user["_id"])
        self.repository.complete_assistant_message(reply["_id"], "Hi")

        self.assertEqual(
            [item["content"] for item in self.repository.get_active_path(self.thread["_id"], "local-user")],
            ["", "Hello", "Hi"],
        )

    def test_provider_preferences_and_avatar_are_local_persistent_records(self):
        provider = self.repository.create_provider(
            {"name": "Local", "base_url": "https://example.test/v1", "api_key": "key", "default_model": "demo"}
        )
        updated = self.repository.update_provider(provider["_id"], {"available_models": ["demo", "demo-reasoner"]})
        self.repository.save_preferences(
            "local-user",
            {
                "provider_id": provider["_id"],
                "model": "demo",
                "temperature": 0.4,
                "context_turns": 16,
                "thinking_level": "high",
            },
        )
        user = self.repository.create_user("local-user@example.com")
        _, profile = self.repository.save_user_avatar(user["user_id"], "data:image/png;base64,AA==")

        self.assertEqual(updated["available_models"], ["demo", "demo-reasoner"])
        self.assertEqual(self.repository.get_preferences("local-user")["context_turns"], 16)
        self.assertEqual(self.repository.get_preferences("local-user")["thinking_level"], "high")
        self.assertEqual(profile["avatar_data_url"], "data:image/png;base64,AA==")

    def test_chat_preferences_default_to_medium_thinking(self):
        self.assertEqual(self.repository.get_preferences("new-user")["thinking_level"], "medium")

    def test_manual_default_model_is_selectable_before_refresh(self):
        provider = self.repository.create_provider({
            'name': 'Manual', 'base_url': 'https://example.test/v1',
            'api_key': 'key', 'default_model': 'manual-model',
        })
        self.assertEqual(provider['available_models'], ['manual-model'])
        refreshed = self.repository.update_provider(provider['_id'], {'available_models': ['another-model']})
        self.assertEqual(refreshed['available_models'], ['manual-model', 'another-model'])

    def test_local_user_profile_is_persisted(self):
        user = self.repository.create_user("elysi@example.com")
        updated = self.repository.update_user(user["user_id"], {"username": "elysi", "avatar_data_url": "data:image/png;base64,AA=="})


        self.assertEqual(updated["username"], "elysi")
        self.assertEqual(self.repository.find_user("elysi")["avatar_data_url"], "data:image/png;base64,AA==")
        self.assertEqual(self.repository.update_user(user["user_id"], {"username": "elysi-renamed"})["username"], "elysi-renamed")
        self.assertEqual(self.repository.find_user("elysi-renamed")["email"], "elysi@example.com")

    def test_edit_and_retry_create_selectable_message_versions(self):
        user = self.repository.create_user_message(self.thread["_id"], "local-user", "Original")
        reply = self.repository.create_assistant_message(self.thread["_id"], "local-user", user["_id"])
        self.repository.complete_assistant_message(reply["_id"], "First answer")
        edited = self.repository.edit_user_message(self.thread["_id"], "local-user", user["_id"], "Edited")
        retried = self.repository.retry_assistant_message(self.thread["_id"], "local-user", reply["_id"])

        self.assertEqual([item["content"] for item in self.repository.get_sibling_versions(edited)], ["Original", "Edited"])
        self.assertEqual(retried["status"], "streaming")
        selected = self.repository.list_messages(self.thread["_id"], "local-user")[-1]
        self.assertEqual(selected["_id"], retried["_id"])
        self.assertEqual(selected["sibling_count"], 2)

    def test_branch_copies_the_selected_path_without_copying_other_versions(self):
        user = self.repository.create_user_message(self.thread["_id"], "local-user", "Question")
        reply = self.repository.create_assistant_message(self.thread["_id"], "local-user", user["_id"])
        self.repository.complete_assistant_message(reply["_id"], "Answer")
        branch = self.repository.create_branch_conversation(self.thread["_id"], "local-user", reply["_id"])

        self.assertEqual(
            [item["content"] for item in self.repository.get_active_path(branch["_id"], "local-user")],
            ["", "Question", "Answer"],
        )

    def test_workspace_threads_are_isolated_and_message_metadata_round_trips(self):
        playground = self.repository.create_conversation(
            {
                "user_id": "local-user",
                "title": "Roleplay",
                "workspace_type": "playground",
                "owner_type": "character",
                "owner_id": "character-1",
            }
        )
        opening = self.repository.create_opening_assistant_message(
            playground["_id"], "local-user", "欢迎来到雨夜。"
        )
        updated = self.repository.update_message_metadata(
            opening["_id"],
            "local-user",
            {
                "state_snapshot": {"affection": 3},
                "action_options": [{"text": "敲门"}],
            },
        )

        rows = self.repository.list_workspace_conversations(
            "local-user", "playground", "character", "character-1"
        )
        messages = self.repository.list_messages(playground["_id"], "local-user")

        self.assertEqual([item["_id"] for item in rows], [playground["_id"]])
        self.assertEqual(updated["metadata"]["state_snapshot"]["affection"], 3)
        self.assertEqual(messages[0]["metadata"]["action_options"], [{"text": "敲门"}])
        self.assertNotIn(self.thread["_id"], [item["_id"] for item in rows])

    def test_branch_with_map_copies_workspace_ownership_and_metadata(self):
        playground = self.repository.create_conversation(
            {
                "user_id": "local-user",
                "title": "Roleplay",
                "workspace_type": "playground",
                "owner_type": "world",
                "owner_id": "world-1",
            }
        )
        opening = self.repository.create_opening_assistant_message(
            playground["_id"], "local-user", "世界开始运转。"
        )
        self.repository.update_message_metadata(
            opening["_id"], "local-user", {"state_snapshot": {"danger": 2}}
        )

        result = self.repository.create_branch_conversation_with_map(
            playground["_id"], "local-user", opening["_id"]
        )

        self.assertIsNotNone(result)
        branch, message_map = result
        copied = self.repository.get_workspace_conversation(
            branch["_id"], "local-user", "playground"
        )
        copied_opening = self.repository.get_path_to_message(
            branch["_id"], "local-user", message_map[opening["_id"]]
        )[-1]
        self.assertEqual(copied["owner_type"], "world")
        self.assertEqual(copied["owner_id"], "world-1")
        self.assertEqual(copied_opening["metadata"]["state_snapshot"], {"danger": 2})

    def test_fastapi_startup_uses_the_configured_sqlite_database(self):
        from AgentBI.main import app, lifespan
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        with tempfile.TemporaryDirectory() as directory:
            database_path = str(Path(directory) / "agentbi.sqlite3")

            async def start_application():
                async with lifespan(app):
                    self.assertIsInstance(app.state.chat_repository, SqliteChatRepository)
                    self.assertEqual(app.state.chat_repository.path, database_path)

            with patch.dict(os.environ, {"MONGO_URI": "", "CHAT_SQLITE_PATH": database_path}, clear=False):
                asyncio.run(start_application())


if __name__ == "__main__":
    unittest.main()
