import base64
import unittest


PNG = b"\x89PNG\r\n\x1a\nminimal-png"
PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(PNG).decode("ascii")


class _FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.request = None

    async def create(self, **kwargs):
        self.request = kwargs
        return self.response


class _FakeClient:
    def __init__(self, response):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(response)})()


class LiteImageParserTests(unittest.TestCase):
    def test_extracts_newapi_message_images(self):
        from AgentBI.src.services.image_generation.lite_adapter import extract_image_data

        payload = {
            "choices": [{"message": {"images": [{"image_url": {"url": PNG_DATA_URL}}]}}]
        }

        image_bytes, media_type = extract_image_data(payload)
        self.assertEqual(image_bytes, PNG)
        self.assertEqual(media_type, "image/png")

    def test_extracts_multimodal_content_and_markdown_data_urls(self):
        from AgentBI.src.services.image_generation.lite_adapter import extract_image_data

        content_payload = {
            "choices": [
                {"message": {"content": [{"type": "image_url", "image_url": {"url": PNG_DATA_URL}}]}}
            ]
        }
        markdown_payload = {
            "choices": [{"message": {"content": f"Generated image: ![result]({PNG_DATA_URL})"}}]
        }

        self.assertEqual(extract_image_data(content_payload), (PNG, "image/png"))
        self.assertEqual(extract_image_data(markdown_payload), (PNG, "image/png"))

    def test_rejects_text_only_or_invalid_image_payloads(self):
        from AgentBI.src.services.image_generation.lite_adapter import (
            ImageGenerationError,
            extract_image_data,
        )

        with self.assertRaisesRegex(ImageGenerationError, "未返回可解析图片"):
            extract_image_data({"choices": [{"message": {"content": "sorry"}}]})
        with self.assertRaisesRegex(ImageGenerationError, "图片数据无效"):
            extract_image_data(
                {
                    "choices": [
                        {
                            "message": {
                                "images": [
                                    {
                                        "image_url": {
                                            "url": "data:image/png;base64,"
                                            + base64.b64encode(b"not-an-image").decode("ascii")
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            )


class LiteImageAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_calls_chat_completions_with_configured_model_and_image_modalities(self):
        from AgentBI.src.services.image_generation.lite_adapter import LiteChatImageAdapter

        client = _FakeClient(
            {"choices": [{"message": {"images": [{"image_url": {"url": PNG_DATA_URL}}]}}]}
        )
        adapter = LiteChatImageAdapter(client_factory=lambda provider: client)

        result = await adapter.generate(
            provider={"api_key": "secret", "base_url": "https://newapi.example/v1"},
            model="gemini-image",
            prompt="a red paper crane",
            aspect_ratio="landscape",
        )

        request = client.chat.completions.request
        self.assertEqual(request["model"], "gemini-image")
        self.assertEqual(request["messages"], [{"role": "user", "content": "a red paper crane"}])
        self.assertEqual(request["extra_body"]["modalities"], ["text", "image"])
        self.assertEqual(request["extra_body"]["image_config"]["aspect_ratio"], "16:9")
        self.assertNotIn("stream", request)
        self.assertEqual(result.image_bytes, PNG)
        self.assertEqual(result.media_type, "image/png")
        self.assertEqual(result.model, "gemini-image")

    async def test_reference_image_uses_openai_compatible_multimodal_content(self):
        from AgentBI.src.services.image_generation.lite_adapter import LiteChatImageAdapter

        client = _FakeClient(
            {"choices": [{"message": {"images": [{"image_url": {"url": PNG_DATA_URL}}]}}]}
        )
        adapter = LiteChatImageAdapter(client_factory=lambda provider: client)

        await adapter.generate(
            provider={"api_key": "secret", "base_url": "https://newapi.example/v1"},
            model="gemini-image",
            prompt="保留参考角色，生成表情贴纸",
            aspect_ratio="square",
            reference_image_data_url=PNG_DATA_URL,
        )

        content = client.chat.completions.request["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "image_url", "image_url": {"url": PNG_DATA_URL}})
        self.assertEqual(content[1], {"type": "text", "text": "保留参考角色，生成表情贴纸"})


if __name__ == "__main__":
    unittest.main()
