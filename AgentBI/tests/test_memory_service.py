import unittest


class MemoryServiceTests(unittest.TestCase):
    def test_similarity_filter_applies_threshold_and_limit(self):
        from AgentBI.src.services.memory_service import rank_similar

        rows = [
            {"message_id": "a", "vector": [1.0, 0.0], "content": "database plan"},
            {"message_id": "b", "vector": [0.8, 0.2], "content": "related plan"},
            {"message_id": "c", "vector": [0.0, 1.0], "content": "unrelated"},
        ]
        ranked = rank_similar([1.0, 0.0], rows, threshold=0.8, limit=2)

        self.assertEqual([item["message_id"] for item in ranked], ["a", "b"])
        self.assertGreaterEqual(ranked[-1]["similarity"], 0.8)

    def test_memory_update_runs_only_after_configured_number_of_new_turns(self):
        from AgentBI.src.services.memory_service import memory_update_due

        self.assertFalse(memory_update_due(new_message_count=10, interval_turns=6))
        self.assertTrue(memory_update_due(new_message_count=12, interval_turns=6))

    def test_compressed_context_keeps_only_recent_turns_when_summary_exists(self):
        from AgentBI.src.services.memory_service import build_context_bundle

        path = [{"_id": str(index), "role": "user" if index % 2 else "assistant", "content": str(index)} for index in range(1, 13)]
        bundle = build_context_bundle(
            path,
            context_turns=8,
            strategy="compression",
            summary="Earlier discussion",
            summary_until_message_id="8",
            keep_recent_turns=2,
        )

        self.assertEqual(bundle["summary"], "Earlier discussion")
        self.assertEqual([item["content"] for item in bundle["messages"]], ["9", "10", "11", "12"])

    def test_window_strategy_ignores_cached_summary(self):
        from AgentBI.src.services.memory_service import build_context_bundle

        path = [{"_id": str(index), "role": "user", "content": str(index)} for index in range(1, 7)]
        bundle = build_context_bundle(path, 2, "window", "stale", "4", 1)

        self.assertIsNone(bundle["summary"])
        self.assertEqual([item["content"] for item in bundle["messages"]], ["3", "4", "5", "6"])

    def test_compression_ignores_summary_from_another_dag_branch(self):
        from AgentBI.src.services.memory_service import build_context_bundle

        path = [
            {"_id": "u1", "role": "user", "content": "first"},
            {"_id": "a1", "role": "assistant", "content": "answer"},
            {"_id": "u2", "role": "user", "content": "current branch"},
        ]
        bundle = build_context_bundle(path, 8, "compression", "summary from another branch", "missing", 2)

        self.assertIsNone(bundle["summary"])
        self.assertEqual([item["content"] for item in bundle["messages"]], ["first", "answer", "current branch"])


class MemoryIndexBatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_embedding_index_batches_never_exceed_ten_messages(self):
        from AgentBI.src.services.memory_service import MemoryService

        class Repository:
            def get_model_route(self, user_id, role):
                return {"provider_id": "provider", "model": "embedding-model"}

            def list_message_embeddings(self, user_id, assistant_id, model_key):
                return []

            def list_assistant_messages(self, user_id, assistant_id):
                return [{"_id": str(index), "content": f"message {index}"} for index in range(23)]

            def save_message_embedding(self, *args):
                pass

        class ModelTasks:
            def __init__(self):
                self.batch_sizes = []

            async def embed(self, user_id, texts):
                self.batch_sizes.append(len(texts))
                return "provider:embedding-model", [[0.1] for _ in texts]

        tasks = ModelTasks()
        await MemoryService(Repository(), tasks).ensure_history_index("user", "assistant")

        self.assertEqual(tasks.batch_sizes, [10, 10, 3])


if __name__ == "__main__":
    unittest.main()
