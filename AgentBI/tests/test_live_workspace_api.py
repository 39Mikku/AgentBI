import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient


class LiveWorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.live import router
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")
        app = FastAPI()
        app.state.chat_repository = self.repository
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.repository.close()

    def _create_role(self, user_id="alice", name="陪伴者"):
        response = self.client.post(
            "/live/roles",
            json={
                "user_id": user_id,
                "name": name,
                "instructions": "自然、简洁地交流",
                "voice": "clone-voice-001",
                "memory_enabled": True,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_role_crud_accepts_avatar_and_custom_voice(self):
        role = self._create_role()

        updated = self.client.put(
            f"/live/roles/{role['id']}?user_id=alice",
            json={"avatar_data_url": "data:image/png;base64,AA==", "voice": "clone-voice-002"},
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["voice"], "clone-voice-002")
        self.assertEqual(updated.json()["avatar_data_url"], "data:image/png;base64,AA==")
        listed = self.client.get("/live/roles?user_id=alice").json()
        self.assertTrue(any(item["id"] == role["id"] for item in listed))

    def test_foreign_user_cannot_read_or_update_role_resources(self):
        role = self._create_role()

        update = self.client.put(
            f"/live/roles/{role['id']}?user_id=bob",
            json={"name": "偷改"},
        )
        memory = self.client.get(f"/live/roles/{role['id']}/memory?user_id=bob")

        self.assertEqual(update.status_code, 404)
        self.assertEqual(memory.status_code, 404)

    def test_default_role_cannot_be_deleted(self):
        default_role = self.client.get("/live/roles?user_id=alice").json()[0]

        response = self.client.delete(f"/live/roles/{default_role['id']}?user_id=alice")

        self.assertEqual(response.status_code, 409)

    def test_conversations_and_messages_are_role_scoped_and_owned(self):
        role = self._create_role()
        created = self.client.post(
            "/live/conversations",
            json={"user_id": "alice", "role_id": role["id"]},
        )
        self.assertEqual(created.status_code, 201)
        conversation = created.json()
        self.repository.append_live_message(
            conversation["id"], "alice", role["id"], "user", "你好", "u1", "complete"
        )

        messages = self.client.get(
            f"/live/conversations/{conversation['id']}/messages?user_id=alice"
        )
        foreign = self.client.get(
            f"/live/conversations/{conversation['id']}/messages?user_id=bob"
        )

        self.assertEqual(messages.status_code, 200)
        self.assertEqual(messages.json()[0]["content"], "你好")
        self.assertEqual(foreign.status_code, 404)

    def test_conversation_can_be_renamed_and_deleted(self):
        role = self._create_role()
        conversation = self.client.post(
            "/live/conversations",
            json={"user_id": "alice", "role_id": role["id"]},
        ).json()

        renamed = self.client.put(
            f"/live/conversations/{conversation['id']}?user_id=alice",
            json={"title": "夜间通话"},
        )
        deleted = self.client.delete(
            f"/live/conversations/{conversation['id']}?user_id=alice"
        )

        self.assertEqual(renamed.json()["title"], "夜间通话")
        self.assertEqual(deleted.status_code, 204)

    def test_role_memory_can_be_saved_and_cleared_while_disabled(self):
        role = self._create_role()
        self.client.put(
            f"/live/roles/{role['id']}?user_id=alice",
            json={"memory_enabled": False},
        )

        saved = self.client.put(
            f"/live/roles/{role['id']}/memory?user_id=alice",
            json={"content": "用户喜欢安静的环境"},
        )
        loaded = self.client.get(f"/live/roles/{role['id']}/memory?user_id=alice")
        cleared = self.client.delete(f"/live/roles/{role['id']}/memory?user_id=alice")

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(loaded.json()["content"], "用户喜欢安静的环境")
        self.assertEqual(cleared.status_code, 204)


if __name__ == "__main__":
    unittest.main()
