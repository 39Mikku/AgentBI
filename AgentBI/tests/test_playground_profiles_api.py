import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.repositories.sqlite_playground_repository import SqlitePlaygroundRepository


class PlaygroundProfilesApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.playground_profiles import router

        self.chat = SqliteChatRepository(":memory:")
        self.repository = SqlitePlaygroundRepository.from_connection_owner(self.chat)
        app = FastAPI()
        app.state.chat_repository = self.chat
        app.state.playground_repository = self.repository
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.chat.close()

    def test_router_exposes_management_endpoints(self):
        from AgentBI.src.api.playground_profiles import router

        paths = {route.path for route in router.routes}
        self.assertIn("/playground/preferences", paths)
        self.assertIn("/playground/profiles", paths)
        self.assertIn("/playground/profiles/{profile_id}/persona", paths)
        self.assertIn("/playground/profiles/{profile_id}/prompt-modules", paths)
        self.assertIn("/playground/profiles/{profile_id}/context-entries", paths)
        self.assertIn("/playground/state-templates", paths)

    def test_profile_resources_round_trip_and_are_user_scoped(self):
        created = self.client.post(
            "/playground/profiles",
            json={
                "user_id": "user-1",
                "profile_type": "character",
                "name": "芽衣",
                "main_prompt": "保持克制而温柔的语气。",
                "opening_message": "雨还在下。",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        profile_id = created.json()["id"]

        prompt_modules = self.client.put(
            f"/playground/profiles/{profile_id}/prompt-modules",
            params={"user_id": "user-1"},
            json={
                "items": [
                    {
                        "name": "文风",
                        "content": "使用克制的电影化描写。",
                        "injection_position": "system_end",
                        "sort_order": 10,
                    }
                ]
            },
        )
        persona = self.client.put(
            f"/playground/profiles/{profile_id}/persona",
            params={"user_id": "user-1"},
            json={"name": "舰长", "identity_text": "来自休伯利安。"},
        )
        lorebook = self.client.put(
            f"/playground/profiles/{profile_id}/context-entries",
            params={"user_id": "user-1"},
            json={
                "items": [
                    {
                        "name": "极东支部",
                        "content": "圣芙蕾雅学园位于极东支部。",
                        "activation_mode": "keyword",
                        "keywords": ["学园"],
                        "priority": 20,
                    }
                ]
            },
        )

        self.assertEqual(prompt_modules.status_code, 200, prompt_modules.text)
        self.assertEqual(persona.status_code, 200, persona.text)
        self.assertEqual(lorebook.status_code, 200, lorebook.text)
        self.assertEqual(
            self.client.get(
                f"/playground/profiles/{profile_id}", params={"user_id": "user-2"}
            ).status_code,
            404,
        )

    def test_profile_rejects_foreign_or_non_image_assets(self):
        foreign = self.chat.create_asset(
            {
                "user_id": "user-2",
                "kind": "image",
                "filename": "foreign.png",
                "mime_type": "image/png",
                "size": 1,
            }
        )
        document = self.chat.create_asset(
            {
                "user_id": "user-1",
                "kind": "document",
                "filename": "notes.md",
                "mime_type": "text/markdown",
                "size": 1,
            }
        )
        base = {"user_id": "user-1", "profile_type": "character", "name": "角色"}

        self.assertEqual(
            self.client.post(
                "/playground/profiles",
                json={**base, "avatar_attachment_id": foreign["_id"]},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/playground/profiles",
                json={**base, "background_attachment_id": document["_id"]},
            ).status_code,
            400,
        )

    def test_delete_profile_removes_its_playground_threads_only(self):
        profile = self.repository.create_profile(
            {
                "user_id": "user-1",
                "profile_type": "character",
                "name": "角色",
                "settings": {},
            }
        )
        owned = self.chat.create_conversation(
            {
                "user_id": "user-1",
                "title": "角色会话",
                "workspace_type": "playground",
                "owner_type": "character",
                "owner_id": profile["_id"],
            }
        )
        other = self.chat.create_conversation(
            {
                "user_id": "user-1",
                "title": "其他会话",
                "workspace_type": "playground",
                "owner_type": "world",
                "owner_id": "world-1",
            }
        )

        response = self.client.delete(
            f"/playground/profiles/{profile['_id']}", params={"user_id": "user-1"}
        )

        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.chat.get_conversation(owned["_id"], "user-1"))
        self.assertIsNotNone(self.chat.get_conversation(other["_id"], "user-1"))


if __name__ == "__main__":
    unittest.main()
