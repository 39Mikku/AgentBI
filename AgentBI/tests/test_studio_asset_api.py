import base64
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.studio_asset_service import StudioAssetService
from AgentBI.src.schemas.image_generation_schema import GeneratedImage


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

    def test_bound_user_image_can_be_reused_as_a_generation_reference(self):
        asset = self.service.upload(
            user_id="user-1", filename="character.png", content_type="image/png", data=PNG
        )
        assistant = self.repository.ensure_default_assistant("user-1")
        thread = self.repository.create_conversation(
            {
                "user_id": "user-1", "title": "reference", "temperature": 1.0,
                "context_turns": 8, "assistant_id": assistant["_id"],
            }
        )
        message = self.repository.create_user_message(thread["_id"], "user-1", "参考这张图")
        self.service.bind_assets(message["_id"], "user-1", [asset["_id"]])

        reference = self.service.message_reference_image_data_url(message["_id"], "user-1")

        self.assertEqual(
            reference,
            "data:image/png;base64," + base64.b64encode(PNG).decode("ascii"),
        )

    def test_generated_video_is_registered_listed_and_served_inline(self):
        relative_path = "videos/user-hash/job-1.mp4"
        target = Path(self.directory.name) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"\x00\x00\x00\x18ftypmp42video")
        asset = self.service.register_generated_video(
            user_id="user-1",
            job_id="job-1",
            relative_path=relative_path,
            size=target.stat().st_size,
            metadata={
                "prompt": "A quiet lake at dawn",
                "aspect_ratio": "16:9",
                "duration_seconds": 5,
                "model": "agnes-video-v2.0",
                "provider_video_id": "agnes-1",
            },
        )
        assistant = self.repository.ensure_default_assistant("user-1")
        thread = self.repository.create_conversation(
            {
                "user_id": "user-1", "title": "video", "temperature": 1.0,
                "context_turns": 8, "assistant_id": assistant["_id"],
            }
        )
        message = self.repository.create_user_message(thread["_id"], "user-1", "video")
        self.service.bind_assets(message["_id"], "user-1", [asset["_id"]])

        listing = self.client.get("/assets", params={"user_id": "user-1", "kind": "video"})
        content = self.client.get(f"/assets/{asset['_id']}/content", params={"user_id": "user-1"})

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["kind"], "video")
        self.assertEqual(content.headers["content-type"], "video/mp4")
        self.assertTrue(content.headers["content-disposition"].startswith("inline"))

    def test_unbound_toolbox_generated_image_is_listed(self):
        relative_path = "hash/toolbox-emoji/sheet.png"
        target = Path(self.directory.name) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(PNG)
        image = GeneratedImage(
            id="sheet-1",
            url="/api/generated-images/hash/toolbox-emoji/sheet.png",
            relative_path=relative_path,
            media_type="image/png",
            mode="pro",
            model="gpt-image-2",
            prompt="表情贴纸表",
        )
        self.service.register_generated(
            "user-1", image, metadata={"scope_id": "toolbox-emoji"}
        )

        listing = self.client.get("/assets", params={"user_id": "user-1", "kind": "image"})

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["id"], "sheet-1")
        self.assertEqual(listing.json()[0]["metadata"]["scope_id"], "toolbox-emoji")
        self.assertIsNone(listing.json()[0]["source_conversation_id"])


if __name__ == "__main__":
    unittest.main()
