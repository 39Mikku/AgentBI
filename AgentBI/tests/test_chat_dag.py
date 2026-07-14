import unittest
from datetime import datetime, timezone


class ActivePathContextTests(unittest.TestCase):
    def test_stream_start_payload_contains_data_needed_to_finalize_the_optimistic_timeline(self):
        from AgentBI.src.api.chat import build_message_start_payload

        created_at = datetime(2026, 7, 14, 14, 30, tzinfo=timezone.utc)
        payload = build_message_start_payload(
            "thread-1",
            {"_id": "assistant-1", "parent_id": "user-1", "created_at": created_at},
            "First question",
        )

        self.assertEqual(payload["message_id"], "assistant-1")
        self.assertEqual(payload["parent_message_id"], "user-1")
        self.assertEqual(payload["conversation_title"], "First question")
        self.assertEqual(payload["conversation_active_message_id"], "assistant-1")
        self.assertEqual(payload["created_at"], "2026-07-14T14:30:00+00:00")

    def test_active_path_context_excludes_root_and_keeps_only_selected_branch(self):
        from AgentBI.src.services.chat_service import build_active_path_context_messages

        active_path = [
            {"role": "root", "content": ""},
            {"role": "user", "content": "Explain MongoDB DAGs"},
            {"role": "assistant", "content": "Version A"},
            {"role": "user", "content": "Use the Atlas example"},
        ]

        self.assertEqual(
            build_active_path_context_messages(active_path, context_turns=2),
            [
                {"role": "user", "content": "Explain MongoDB DAGs"},
                {"role": "assistant", "content": "Version A"},
                {"role": "user", "content": "Use the Atlas example"},
            ],
        )

    def test_chat_service_reads_the_repository_active_path_instead_of_linear_history(self):
        from AgentBI.src.services.chat_service import ChatService

        class Repository:
            def get_active_path(self, conversation_id, user_id):
                self.called = (conversation_id, user_id)
                return [
                    {"role": "root", "content": ""},
                    {"role": "user", "content": "branch question"},
                    {"role": "assistant", "content": "selected answer"},
                ]

            def list_messages(self, *_):
                raise AssertionError("linear message history must not be used for context")

        repository = Repository()
        context = ChatService(repository).build_context("thread-1", "user@example.com", context_turns=1)

        self.assertEqual(repository.called, ("thread-1", "user@example.com"))
        self.assertEqual(
            context,
            [
                {"role": "user", "content": "branch question"},
                {"role": "assistant", "content": "selected answer"},
            ],
        )

    def test_chat_service_can_build_context_for_a_retry_parent_without_using_the_pending_sibling(self):
        from AgentBI.src.services.chat_service import ChatService

        class Repository:
            def get_path_to_message(self, conversation_id, user_id, message_id):
                self.called = (conversation_id, user_id, message_id)
                return [
                    {"role": "root", "content": ""},
                    {"role": "user", "content": "retry this answer"},
                ]

        repository = Repository()
        context = ChatService(repository).build_context_to_message("thread-1", "user@example.com", "user-node", 8)

        self.assertEqual(repository.called, ("thread-1", "user@example.com", "user-node"))
        self.assertEqual(context, [{"role": "user", "content": "retry this answer"}])


if __name__ == "__main__":
    unittest.main()
