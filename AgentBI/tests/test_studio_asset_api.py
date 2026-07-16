import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.studio_asset_service import StudioAssetService


PNG = b"\x89PNG\r\n\x1a\n" + b"asset-api"


class StudioAssetApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.studio_assets import router

        self.directory = tempfile.TemporaryDirectory()
        self.repository = SqliteChatRepository(":memory:")
        self.service = StudioAssetService(self.repository, Path(self.directory.name))
        app = FastAPI()
        app.state.chat_repository = self.repository
        app.state.studio_asset_service = self.service
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.repository.close()
        self.directory.cleanup()

    def test_upload_download_list_and_delete(self):
        response = self.client.post(
            "/assets",
            data={"user_id": "user-1"},
            files={"file": ("diagram.png", PNG, "image/png")},
        )
        self.assertEqual(response.status_code, 201)
        asset = response.json()

        assistant = self.repository.ensure_default_assistant("user-1")
        thread = self.repository.create_conversation(
            {
                "user_id": "user-1", "title": "assets", "temperature": 1.0,
                "context_turns": 8, "assistant_id": assistant["_id"],
            }
        )
        message = self.repository.create_user_message(thread["_id"], "user-1", "image")
        self.service.bind_assets(message["_id"], "user-1", [asset["id"]])

        listing = self.client.get("/assets", params={"user_id": "user-1", "kind": "image"})
        content = self.client.get(f"/assets/{asset['id']}/content", params={"user_id": "user-1"})
        deleted = self.client.delete(f"/assets/{asset['id']}", params={"user_id": "user-1"})

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["id"], asset["id"])
        self.assertEqual(content.content, PNG)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            self.client.get(f"/assets/{asset['id']}/content", params={"user_id": "user-1"}).status_code,
            410,
        )

    def test_cross_user_content_is_hidden(self):
        asset = self.service.upload(
            user_id="user-1", filename="diagram.png", content_type="image/png", data=PNG
        )
        response = self.client.get(
            f"/assets/{asset['_id']}/content", params={"user_id": "user-2"}
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
