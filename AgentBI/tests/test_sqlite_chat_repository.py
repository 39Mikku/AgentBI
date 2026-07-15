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
        self.repository.save_preferences("local-user", {"provider_id": provider["_id"], "model": "demo", "temperature": 0.4, "context_turns": 16})
        _, profile = self.repository.save_user_avatar("local-user", "data:image/png;base64,AA==")

        self.assertEqual(updated["available_models"], ["demo", "demo-reasoner"])
        self.assertEqual(self.repository.get_preferences("local-user")["context_turns"], 16)
        self.assertEqual(profile["avatar_data_url"], "data:image/png;base64,AA==")

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

    def test_fastapi_startup_uses_the_configured_sqlite_database(self):
        from AgentBI.main import app, lifespan
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        with tempfile.TemporaryDirectory() as directory:
            database_path = str(Path(directory) / "agentbi.sqlite3")

            async def start_application():
                with patch("AgentBI.main.LoginAgent"):
                    async with lifespan(app):
                        self.assertIsInstance(app.state.chat_repository, SqliteChatRepository)
                        self.assertEqual(app.state.chat_repository.path, database_path)

            with patch.dict(os.environ, {"MONGO_URI": "", "CHAT_SQLITE_PATH": database_path}, clear=False):
                asyncio.run(start_application())


if __name__ == "__main__":
    unittest.main()
