import unittest


class MemoryRepositoryTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")
        self.user_id = "memory@example.com"
        self.assistant = self.repository.create_assistant(
            {
                "user_id": self.user_id,
                "name": "Memory assistant",
                "memory_enabled": True,
                "memory_update_interval": 12,
                "history_search_enabled": True,
                "history_similarity_threshold": 0.58,
                "history_result_limit": 3,
                "context_strategy": "compression",
                "compression_threshold_turns": 10,
                "compression_threshold_tokens": 8000,
                "compression_keep_recent_turns": 4,
            }
        )

    def tearDown(self):
        self.repository.close()

    def test_model_routes_are_saved_by_user_and_role(self):
        route = self.repository.save_model_route(
            self.user_id, "memory", {"provider_id": "provider-1", "model": "small-chat"}
        )

        self.assertEqual(route["role"], "memory")
        self.assertEqual(self.repository.get_model_route(self.user_id, "memory")["model"], "small-chat")
        self.assertEqual(len(self.repository.list_model_routes(self.user_id)), 1)

    def test_assistant_policy_memory_and_thread_summary_are_persisted(self):
        self.assertTrue(self.assistant["memory_enabled"])
        self.assertEqual(self.assistant["context_strategy"], "compression")

        memory = self.repository.save_assistant_memory(
            self.user_id, self.assistant["_id"], "User prefers concise answers.", "message-1"
        )
        self.assertEqual(memory["summary"], "User prefers concise answers.")

        thread = self.repository.create_conversation(
            {"user_id": self.user_id, "title": "New chat", "assistant_id": self.assistant["_id"]}
        )
        updated = self.repository.save_context_summary(thread["_id"], self.user_id, "Earlier context", "message-2")
        self.assertEqual(updated["context_summary"], "Earlier context")
        self.assertEqual(updated["context_summary_until_message_id"], "message-2")

    def test_message_embeddings_can_be_listed_for_one_assistant(self):
        thread = self.repository.create_conversation(
            {"user_id": self.user_id, "title": "Vector chat", "assistant_id": self.assistant["_id"]}
        )
        message = self.repository.create_user_message(thread["_id"], self.user_id, "Remember the blue database plan")
        self.repository.save_message_embedding(
            message["_id"], self.user_id, self.assistant["_id"], "provider-1:embed-small", [0.1, 0.2, 0.3]
        )

        rows = self.repository.list_message_embeddings(self.user_id, self.assistant["_id"], "provider-1:embed-small")
        self.assertEqual(rows[0]["message_id"], message["_id"])
        self.assertEqual(rows[0]["vector"], [0.1, 0.2, 0.3])
        self.assertEqual(rows[0]["content"], "Remember the blue database plan")


if __name__ == "__main__":
    unittest.main()
