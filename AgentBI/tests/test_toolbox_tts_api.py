import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.api.toolbox_tts import router
from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.toolbox.tts.base import TtsProviderError, TtsSynthesisResult
from AgentBI.src.services.toolbox.tts.bailian_voice_enrollment import LiveVoiceEnrollmentResult


class FakeAdapter:
    provider_id = "minimax"

    async def synthesize(self, request):
        if request.text == "fail":
            raise TtsProviderError("供应商暂时不可用")
        return TtsSynthesisResult(
            audio=b"audio",
            content_type="audio/mpeg",
            extension="mp3",
            elapsed_ms=42,
            metadata={"trace_id": "trace-1"},
        )


class FakeRegistry:
    def capabilities(self):
        return [{"id": "minimax", "label": "MiniMax", "configured": True}]

    def get(self, provider_id):
        if provider_id != "minimax":
            raise TtsProviderError("供应商不存在", code="validation_error")
        return FakeAdapter()


class FakeEnrollmentAdapter:
    async def enroll(self, payload):
        return LiveVoiceEnrollmentResult(
            voice_id=f"{payload.target_model}-{payload.prefix}-remote001",
            request_id="enroll-request-1",
        )


class ToolboxTtsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = SqliteChatRepository(str(Path(self.temp_dir.name) / "toolbox.sqlite3"))
        app = FastAPI()
        app.state.chat_repository = self.repository
        app.state.tts_provider_registry = FakeRegistry()
        app.state.live_voice_enrollment_adapter = FakeEnrollmentAdapter()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.repository.close()
        self.temp_dir.cleanup()

    def test_capabilities_and_voice_crud_are_user_scoped(self):
        capabilities = self.client.get("/toolbox/tts/capabilities")
        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(capabilities.json()["providers"][0]["id"], "minimax")

        created = self.client.post(
            "/toolbox/tts/voices",
            json={
                "user_id": "alice",
                "provider": "minimax",
                "display_name": "我的音色",
                "external_voice_id": "voice-clone-1",
                "voice_kind": "cloned",
                "bound_model": "speech-2.8-hd",
            },
        )
        self.assertEqual(created.status_code, 201)
        voice = created.json()
        self.assertEqual(self.client.get("/toolbox/tts/voices?user_id=alice").json()[0]["id"], voice["id"])
        self.assertEqual(self.client.get("/toolbox/tts/voices?user_id=bob").json(), [])

        renamed = self.client.put(
            f"/toolbox/tts/voices/{voice['id']}?user_id=alice",
            json={"display_name": "重命名音色"},
        )
        self.assertEqual(renamed.json()["display_name"], "重命名音色")
        self.assertEqual(
            self.client.delete(f"/toolbox/tts/voices/{voice['id']}?user_id=bob").status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/toolbox/tts/voices/{voice['id']}?user_id=alice").status_code,
            204,
        )

    def test_live_enrollment_persists_friendly_name_remote_id_and_exact_model(self):
        signed_url = "https://bucket.oss-cn-beijing.aliyuncs.com/sample.mp3?signature=secret"
        response = self.client.post(
            "/toolbox/tts/voices/enroll-live",
            json={
                "user_id": "alice",
                "display_name": "电影旁白",
                "target_model": "qwen-audio-3.0-realtime-plus",
                "prefix": "livevoice",
                "audio_url": signed_url,
            },
        )

        self.assertEqual(response.status_code, 201)
        voice = response.json()
        self.assertEqual(voice["display_name"], "电影旁白")
        self.assertEqual(
            voice["external_voice_id"],
            "qwen-audio-3.0-realtime-plus-livevoice-remote001",
        )
        self.assertEqual(voice["bound_model"], "qwen-audio-3.0-realtime-plus")
        self.assertEqual(voice["provider_metadata"], {
            "usage": "live",
            "prefix": "livevoice",
            "request_id": "enroll-request-1",
        })
        self.assertNotIn("audio_url", voice["provider_metadata"])
        stored = self.repository.list_toolbox_tts_voices("alice")[0]
        self.assertNotIn("secret", str(stored))

    def test_synthesis_returns_audio_and_runtime_headers(self):
        response = self.client.post(
            "/toolbox/tts/synthesize",
            json={
                "user_id": "alice",
                "provider": "minimax",
                "model": "speech-2.8-hd",
                "voice_id": "female-shaonv",
                "text": "你好",
                "audio_format": "mp3",
                "parameters": {},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"audio")
        self.assertEqual(response.headers["content-type"], "audio/mpeg")
        self.assertEqual(response.headers["x-tts-elapsed-ms"], "42")
        self.assertEqual(response.headers["x-tts-provider"], "minimax")

    def test_registered_voice_cannot_be_used_with_a_different_bound_model(self):
        self.client.post(
            "/toolbox/tts/voices",
            json={
                "user_id": "alice",
                "provider": "bailian",
                "display_name": "Flash 专用",
                "external_voice_id": "voice-flash-1",
                "voice_kind": "cloned",
                "bound_model": "cosyvoice-v3.5-flash",
            },
        )

        response = self.client.post(
            "/toolbox/tts/synthesize",
            json={
                "user_id": "alice",
                "provider": "bailian",
                "model": "cosyvoice-v3.5-plus",
                "voice_id": "voice-flash-1",
                "text": "你好",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("绑定", response.json()["detail"])

    def test_provider_error_is_isolated_as_bad_gateway(self):
        response = self.client.post(
            "/toolbox/tts/synthesize",
            json={
                "user_id": "alice",
                "provider": "minimax",
                "model": "speech-2.8-hd",
                "voice_id": "female-shaonv",
                "text": "fail",
            },
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "供应商暂时不可用")


if __name__ == "__main__":
    unittest.main()
