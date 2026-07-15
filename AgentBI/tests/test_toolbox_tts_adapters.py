import base64
import json
import unittest

import httpx

from AgentBI.src.schemas.toolbox_tts_schema import TtsSynthesisRequest
from AgentBI.src.services.toolbox.tts.bailian_cosyvoice import BailianCosyVoiceAdapter
from AgentBI.src.services.toolbox.tts.bailian_voice_enrollment import BailianLiveVoiceEnrollmentAdapter
from AgentBI.src.services.toolbox.tts.base import TtsConfigurationError, TtsValidationError
from AgentBI.src.services.toolbox.tts.mimo import MimoTtsAdapter
from AgentBI.src.services.toolbox.tts.minimax import MiniMaxTtsAdapter
from AgentBI.src.services.toolbox.tts.volcengine import VolcengineTtsAdapter


class FakeResponse:
    def __init__(self, *, payload=None, content=b"", status_code=200, headers=None):
        self._payload = payload
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        if self._payload is None:
            return json.loads(self.content)
        return self._payload


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


def synthesis_request(provider, model, voice_id, *, audio_format="mp3", parameters=None):
    return TtsSynthesisRequest(
        user_id="user@example.com",
        provider=provider,
        model=model,
        voice_id=voice_id,
        text="你好，欢迎来到语音工作台。",
        audio_format=audio_format,
        parameters=parameters or {},
    )


class TtsAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_bailian_enrolls_live_voice_and_returns_remote_id(self):
        from AgentBI.src.schemas.toolbox_tts_schema import LiveVoiceEnrollmentRequest

        signed_url = "https://bucket.oss-cn-beijing.aliyuncs.com/sample.mp3?signature=secret"
        client = FakeHttpClient([
            FakeResponse(payload={"output": {"voice_id": "qwen-audio-3.0-realtime-plus-voice-001"}, "request_id": "enroll-1"})
        ])
        adapter = BailianLiveVoiceEnrollmentAdapter(
            api_key="key", workspace_id="workspace", http_client=client
        )

        result = await adapter.enroll(LiveVoiceEnrollmentRequest(
            user_id="alice",
            display_name="电影旁白",
            target_model="qwen-audio-3.0-realtime-plus",
            prefix="livevoice",
            audio_url=signed_url,
        ))

        self.assertEqual(result.voice_id, "qwen-audio-3.0-realtime-plus-voice-001")
        self.assertEqual(result.request_id, "enroll-1")
        _, url, call = client.calls[0]
        self.assertEqual(url, "https://workspace.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/customization")
        self.assertEqual(call["headers"]["Authorization"], "Bearer key")
        self.assertEqual(call["json"], {
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": "qwen-audio-3.0-realtime-plus",
                "prefix": "livevoice",
                "url": signed_url,
            },
        })

    async def test_bailian_enrollment_error_does_not_echo_signed_url(self):
        from AgentBI.src.schemas.toolbox_tts_schema import LiveVoiceEnrollmentRequest
        from AgentBI.src.services.toolbox.tts.base import TtsProviderError

        signed_url = "https://bucket.test/sample.mp3?signature=top-secret"
        client = FakeHttpClient([
            FakeResponse(status_code=400, payload={"message": f"cannot fetch {signed_url}"})
        ])
        adapter = BailianLiveVoiceEnrollmentAdapter(
            api_key="key", workspace_id="workspace", http_client=client
        )

        with self.assertRaises(TtsProviderError) as raised:
            await adapter.enroll(LiveVoiceEnrollmentRequest(
                user_id="alice",
                display_name="Narrator",
                target_model="qwen-audio-3.0-realtime-flash",
                prefix="voice01",
                audio_url=signed_url,
            ))
        self.assertNotIn("top-secret", str(raised.exception))

    async def test_bailian_enrollment_network_error_is_sanitized(self):
        from AgentBI.src.schemas.toolbox_tts_schema import LiveVoiceEnrollmentRequest
        from AgentBI.src.services.toolbox.tts.base import TtsProviderError

        signed_url = "https://bucket.test/sample.mp3?signature=top-secret"

        class FailingClient:
            async def post(self, url, **kwargs):
                request = httpx.Request("POST", url)
                raise httpx.ConnectError(f"failed while fetching {signed_url}", request=request)

        adapter = BailianLiveVoiceEnrollmentAdapter(
            api_key="key", workspace_id="workspace", http_client=FailingClient()
        )
        with self.assertRaises(TtsProviderError) as raised:
            await adapter.enroll(LiveVoiceEnrollmentRequest(
                user_id="alice",
                display_name="Narrator",
                target_model="qwen-audio-3.0-realtime-flash",
                prefix="voice01",
                audio_url=signed_url,
            ))
        self.assertNotIn("top-secret", str(raised.exception))

    async def test_minimax_maps_parameters_and_decodes_hex_audio(self):
        client = FakeHttpClient(
            [FakeResponse(payload={"data": {"audio": b"audio".hex()}, "trace_id": "mm-trace", "base_resp": {"status_code": 0}})]
        )
        adapter = MiniMaxTtsAdapter(api_key="key", http_client=client)

        result = await adapter.synthesize(
            synthesis_request(
                "minimax",
                "speech-2.8-hd",
                "female-shaonv",
                parameters={"speed": 1.2, "volume": 1.4, "pitch": 2, "emotion": "happy"},
            )
        )

        self.assertEqual(result.audio, b"audio")
        self.assertEqual(result.content_type, "audio/mpeg")
        _, url, call = client.calls[0]
        self.assertEqual(url, "https://api.minimaxi.com/v1/t2a_v2")
        self.assertEqual(call["headers"]["Authorization"], "Bearer key")
        self.assertEqual(call["json"]["voice_setting"]["speed"], 1.2)
        self.assertEqual(call["json"]["voice_setting"]["emotion"], "happy")

    async def test_bailian_downloads_generated_audio_url(self):
        client = FakeHttpClient(
            [
                FakeResponse(payload={"output": {"audio": {"url": "https://audio.test/result.wav", "id": "audio-1"}}, "request_id": "bl-1"}),
                FakeResponse(content=b"audio", headers={"content-type": "audio/wav"}),
            ]
        )
        adapter = BailianCosyVoiceAdapter(api_key="key", workspace_id="workspace", http_client=client)

        result = await adapter.synthesize(
            synthesis_request(
                "bailian",
                "cosyvoice-v3.5-plus",
                "cosyvoice-clone-id",
                audio_format="wav",
                parameters={"speech_rate": 1.1, "volume": 60, "pitch": 1.05, "instruction": "温柔自然"},
            )
        )

        self.assertEqual(result.audio, b"audio")
        _, url, call = client.calls[0]
        self.assertEqual(url, "https://workspace.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer")
        self.assertEqual(call["json"]["input"]["rate"], 1.1)
        self.assertEqual(call["json"]["input"]["volume"], 60)
        self.assertEqual(call["json"]["input"]["instruction"], "温柔自然")
        self.assertEqual(client.calls[1][:2], ("GET", "https://audio.test/result.wav"))

    async def test_mimo_uses_openai_compatible_audio_response(self):
        encoded = base64.b64encode(b"audio").decode("ascii")
        client = FakeHttpClient(
            [FakeResponse(payload={"choices": [{"message": {"audio": {"data": encoded, "id": "mimo-audio"}}}]})]
        )
        adapter = MimoTtsAdapter(api_key="key", http_client=client)

        result = await adapter.synthesize(
            synthesis_request(
                "mimo",
                "mimo-v2.5-tts",
                "mimo_default",
                audio_format="wav",
                parameters={"style": "自然、轻松地说"},
            )
        )

        self.assertEqual(result.audio, b"audio")
        _, url, call = client.calls[0]
        self.assertEqual(url, "https://api.xiaomimimo.com/v1/chat/completions")
        self.assertEqual(call["headers"]["api-key"], "key")
        self.assertEqual(call["json"]["audio"], {"format": "wav", "voice": "mimo_default"})
        self.assertEqual(call["json"]["messages"][0]["role"], "user")
        self.assertIn("自然、轻松地说", call["json"]["messages"][0]["content"])
        self.assertEqual(call["json"]["messages"][-1]["role"], "assistant")

    async def test_volcengine_uses_model_resource_and_joins_chunked_audio(self):
        first = base64.b64encode(b"au").decode("ascii")
        second = base64.b64encode(b"dio").decode("ascii")
        content = (
            json.dumps({"code": 0, "data": first}, ensure_ascii=False)
            + json.dumps({"code": 0, "data": second}, ensure_ascii=False)
            + json.dumps({"code": 20000000, "message": "OK"}, ensure_ascii=False)
        ).encode("utf-8")
        client = FakeHttpClient([FakeResponse(content=content, headers={"X-Tt-Logid": "volc-log"})])
        adapter = VolcengineTtsAdapter(
            app_id="app",
            access_token="token",
            tts_resource_id="seed-tts-2.0",
            icl_resource_id="seed-icl-2.0",
            http_client=client,
        )

        result = await adapter.synthesize(
            synthesis_request(
                "volcengine",
                "doubao-seed-icl-2.0",
                "S_clone_voice",
                parameters={"speed_ratio": 1.1, "volume_ratio": 1.2, "context_text": "温柔自然"},
            )
        )

        self.assertEqual(result.audio, b"audio")
        _, url, call = client.calls[0]
        self.assertEqual(url, "https://openspeech.bytedance.com/api/v3/tts/unidirectional")
        self.assertEqual(call["headers"]["X-Api-Resource-Id"], "seed-icl-2.0")
        self.assertEqual(call["json"]["req_params"]["speaker"], "S_clone_voice")
        self.assertEqual(call["json"]["req_params"]["audio_params"]["format"], "mp3")
        self.assertEqual(call["json"]["req_params"]["additions"]["context_texts"], ["温柔自然"])

    async def test_adapters_reject_missing_configuration_and_wrong_model(self):
        with self.assertRaises(TtsConfigurationError):
            await MiniMaxTtsAdapter(api_key="").synthesize(
                synthesis_request("minimax", "speech-2.8-hd", "female-shaonv")
            )

        with self.assertRaises(TtsValidationError):
            await MimoTtsAdapter(api_key="key").synthesize(
                synthesis_request("mimo", "not-a-model", "mimo_default")
            )


if __name__ == "__main__":
    unittest.main()
