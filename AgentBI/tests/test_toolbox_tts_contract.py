import unittest

from pydantic import ValidationError


class ToolboxTtsContractTests(unittest.TestCase):
    def test_live_voice_enrollment_requires_https_supported_model_and_safe_prefix(self):
        from AgentBI.src.schemas.toolbox_tts_schema import LiveVoiceEnrollmentRequest

        payload = LiveVoiceEnrollmentRequest(
            user_id=" alice ",
            display_name=" 电影旁白 ",
            target_model="qwen-audio-3.0-realtime-plus",
            prefix="voice01",
            audio_url="https://bucket.oss-cn-beijing.aliyuncs.com/sample.mp3?signature=secret",
        )
        self.assertEqual(payload.user_id, "alice")
        self.assertEqual(payload.display_name, "电影旁白")

        for changes in (
            {"audio_url": "http://bucket.test/sample.mp3"},
            {"target_model": "qwen-audio-3.0-realtime-other"},
            {"prefix": "中文前缀"},
            {"prefix": "voice_name_11"},
        ):
            values = payload.model_dump()
            values.update(changes)
            with self.assertRaises(ValidationError):
                LiveVoiceEnrollmentRequest(**values)

    def test_bailian_live_voice_can_bind_to_each_exact_realtime_model(self):
        from AgentBI.src.schemas.toolbox_tts_schema import TtsVoiceCreate

        for model in (
            "qwen-audio-3.0-realtime-flash",
            "qwen-audio-3.0-realtime-plus",
        ):
            voice = TtsVoiceCreate(
                user_id="alice",
                provider="bailian",
                display_name="Live voice",
                external_voice_id=f"{model}-voice-001",
                voice_kind="cloned",
                bound_model=model,
            )
            self.assertEqual(voice.bound_model, model)

    def test_bailian_custom_voice_requires_exact_bound_model(self):
        from AgentBI.src.schemas.toolbox_tts_schema import TtsVoiceCreate

        with self.assertRaises(ValidationError):
            TtsVoiceCreate(
                user_id="alice",
                provider="bailian",
                display_name="旁白音色",
                external_voice_id="voice-001",
                voice_kind="cloned",
            )

        voice = TtsVoiceCreate(
            user_id="alice",
            provider="bailian",
            display_name="旁白音色",
            external_voice_id="voice-001",
            voice_kind="cloned",
            bound_model="cosyvoice-v3.5-flash",
        )
        self.assertEqual(voice.display_name, "旁白音色")
        self.assertEqual(voice.external_voice_id, "voice-001")
        self.assertEqual(voice.bound_model, "cosyvoice-v3.5-flash")

    def test_synthesis_request_rejects_blank_text(self):
        from AgentBI.src.schemas.toolbox_tts_schema import TtsSynthesisRequest

        with self.assertRaises(ValidationError):
            TtsSynthesisRequest(
                user_id="alice",
                provider="minimax",
                model="speech-2.8-hd",
                voice_id="female-shaonv",
                text="   ",
            )

    def test_synthesis_request_normalizes_identity_and_keeps_parameters(self):
        from AgentBI.src.schemas.toolbox_tts_schema import TtsSynthesisRequest

        request = TtsSynthesisRequest(
            user_id=" alice ",
            provider="bailian",
            model="cosyvoice-v3.5-plus",
            voice_id=" longxiaochun ",
            text=" 你好，世界。 ",
            parameters={"speed": 1.1},
        )

        self.assertEqual(request.user_id, "alice")
        self.assertEqual(request.voice_id, "longxiaochun")
        self.assertEqual(request.text, "你好，世界。")
        self.assertEqual(request.parameters, {"speed": 1.1})
        self.assertEqual(request.audio_format, "mp3")

    def test_synthesis_result_exposes_audio_metadata_without_persistence_fields(self):
        from AgentBI.src.services.toolbox.tts.base import TtsSynthesisResult

        result = TtsSynthesisResult(
            audio=b"audio",
            content_type="audio/mpeg",
            extension="mp3",
            elapsed_ms=12,
            metadata={"request_id": "safe-id"},
        )

        self.assertEqual(result.audio, b"audio")
        self.assertEqual(result.content_type, "audio/mpeg")
        self.assertFalse(hasattr(result, "file_path"))


if __name__ == "__main__":
    unittest.main()
