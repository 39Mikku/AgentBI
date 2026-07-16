import base64
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.schemas.toolbox_emoji_schema import (
    StickerName,
    StickerNamingResponse,
)


PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    b"\x89PNG\r\n\x1a\nemoji"
).decode("ascii")


class _NamingService:
    async def name(self, **kwargs):
        self.request = kwargs
        return StickerNamingResponse(
            names=[StickerName(id="s1", name="开心挥手")],
            strategy=kwargs["strategy"],
            model="vision-mini",
        )


class ToolboxEmojiApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.toolbox_emoji import router

        app = FastAPI()
        app.state.emoji_naming_service = _NamingService()
        app.include_router(router)
        self.app = app
        self.client = TestClient(app)

    def test_naming_endpoint_forwards_images_and_strategy(self):
        response = self.client.post(
            "/toolbox/emoji/name",
            json={
                "user_id": "user-1",
                "strategy": "batch",
                "images": [{"id": "s1", "data_url": PNG_DATA_URL}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["names"], [{"id": "s1", "name": "开心挥手"}])
        self.assertEqual(self.app.state.emoji_naming_service.request["strategy"], "batch")

    def test_naming_contract_rejects_unsupported_image_data(self):
        response = self.client.post(
            "/toolbox/emoji/name",
            json={
                "user_id": "user-1",
                "strategy": "individual",
                "images": [{"id": "s1", "data_url": "data:image/gif;base64,R0lGODlh"}],
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
