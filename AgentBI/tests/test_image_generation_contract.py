import tempfile
import unittest
from pathlib import Path


class ImageGenerationContractTests(unittest.TestCase):
    def test_image_generation_config_has_safe_user_controlled_defaults(self):
        from AgentBI.src.schemas.image_generation_schema import ImageGenerationConfig

        config = ImageGenerationConfig()

        self.assertEqual(config.mode, "lite")
        self.assertEqual(config.lite_model, "")
        self.assertEqual(config.pro_quality, "high")

    def test_image_request_accepts_only_supported_aspect_ratios(self):
        from pydantic import ValidationError

        from AgentBI.src.schemas.image_generation_schema import ImageGenerationRequest

        request = ImageGenerationRequest(
            user_id="elysia@example.com",
            prompt="a luminous mechanical flower",
            aspect_ratio="portrait",
        )
        self.assertEqual(request.aspect_ratio, "portrait")
        with self.assertRaises(ValidationError):
            ImageGenerationRequest(
                user_id="elysia@example.com",
                prompt="a luminous mechanical flower",
                aspect_ratio="cinema",
            )

    def test_direct_image_tool_exposes_prompt_and_aspect_ratio_only(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        function = next(
            tool["function"]
            for tool in ChatAgent.tool_definitions(["tool.image_generation"])
            if tool["function"]["name"] == "generate_image"
        )

        self.assertEqual(set(function["parameters"]["properties"]), {"prompt", "aspect_ratio"})
        self.assertEqual(set(function["parameters"]["required"]), {"prompt", "aspect_ratio"})
        self.assertNotIn("mode", function["parameters"]["properties"])
        self.assertNotIn("quality", function["parameters"]["properties"])

    def test_artifact_store_hashes_user_and_returns_a_stable_media_url(self):
        from AgentBI.src.services.image_generation.artifact_store import ImageArtifactStore

        with tempfile.TemporaryDirectory() as directory:
            store = ImageArtifactStore(Path(directory), public_prefix="/generated-images")
            image = store.save(
                user_id="elysia@example.com",
                scope_id="conversation/unsafe",
                image_bytes=b"\x89PNG\r\n\x1a\nimage",
                media_type="image/png",
                metadata={"mode": "lite", "model": "gemini-image"},
            )

            self.assertTrue((Path(directory) / image.relative_path).is_file())
            self.assertTrue(image.url.startswith("/generated-images/"))
            self.assertNotIn("elysia", image.url)
            self.assertNotIn("@", image.url)
            self.assertNotIn("/unsafe", image.url)
            self.assertEqual(image.mode, "lite")
            self.assertEqual(image.model, "gemini-image")

    def test_codex_oauth_secret_has_an_explicit_ignore_rule(self):
        ignore = Path(__file__).resolve().parents[2] / ".gitignore"
        content = ignore.read_text(encoding="utf-8")

        self.assertIn("codex-image-oauth.json", content)


if __name__ == "__main__":
    unittest.main()
