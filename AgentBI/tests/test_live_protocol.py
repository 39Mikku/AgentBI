import base64
import unittest


class LiveProtocolTests(unittest.TestCase):
    def test_session_and_turn_events_map_to_stable_state_events(self):
        from AgentBI.src.services.live.protocol import LiveEvent, map_upstream_event

        self.assertEqual(
            map_upstream_event({"type": "session.updated"}),
            [],
        )
        self.assertEqual(
            map_upstream_event(
                {"type": "input_audio_buffer.speech_started", "item_id": "user-1"}
            ),
            [LiveEvent("state.listening", {"item_id": "user-1"})],
        )
        self.assertEqual(
            map_upstream_event(
                {"type": "input_audio_buffer.committed", "item_id": "user-1"}
            ),
            [LiveEvent("state.thinking", {"item_id": "user-1"})],
        )

    def test_user_transcript_delta_keeps_confirmed_and_stashed_text(self):
        from AgentBI.src.services.live.protocol import LiveEvent, map_upstream_event

        mapped = map_upstream_event(
            {
                "type": "conversation.item.input_audio_transcription.delta",
                "item_id": "user-1",
                "text": "你好",
                "stash": "世界",
            }
        )

        self.assertEqual(
            mapped,
            [
                LiveEvent(
                    "user.transcript.delta",
                    {"item_id": "user-1", "text": "你好", "stash": "世界"},
                )
            ],
        )

    def test_assistant_subtitles_stream_and_finalize(self):
        from AgentBI.src.services.live.protocol import LiveEvent, map_upstream_event

        delta = map_upstream_event(
            {
                "type": "response.audio_transcript.delta",
                "item_id": "assistant-1",
                "delta": "你好",
            }
        )
        done = map_upstream_event(
            {
                "type": "response.audio_transcript.done",
                "item_id": "assistant-1",
                "transcript": "你好呀",
            }
        )

        self.assertEqual(delta[0], LiveEvent("state.speaking"))
        self.assertEqual(
            delta[1],
            LiveEvent(
                "assistant.transcript.delta",
                {"item_id": "assistant-1", "delta": "你好"},
            ),
        )
        self.assertEqual(
            done,
            [
                LiveEvent(
                    "assistant.transcript.final",
                    {"item_id": "assistant-1", "transcript": "你好呀"},
                )
            ],
        )

    def test_audio_delta_is_decoded_to_binary_pcm(self):
        from AgentBI.src.services.live.protocol import LiveAudio, LiveEvent, map_upstream_event

        pcm = b"\x00\x01\x02\x03"
        mapped = map_upstream_event(
            {"type": "response.audio.delta", "delta": base64.b64encode(pcm).decode()}
        )

        self.assertEqual(mapped, [LiveEvent("state.speaking"), LiveAudio(pcm)])

    def test_response_done_distinguishes_interruptions_from_completions(self):
        from AgentBI.src.services.live.protocol import LiveEvent, map_upstream_event

        interrupted = map_upstream_event(
            {"type": "response.done", "response": {"status": "cancelled"}}
        )
        completed = map_upstream_event(
            {"type": "response.done", "response": {"status": "completed"}}
        )

        self.assertEqual(interrupted, [LiveEvent("response.interrupted")])
        self.assertEqual(completed, [LiveEvent("response.completed")])

    def test_upstream_errors_are_sanitized_and_classified(self):
        from AgentBI.src.services.live.protocol import LiveEvent, map_upstream_event

        mapped = map_upstream_event(
            {
                "type": "error",
                "error": {
                    "type": "server_error",
                    "code": "upstream_busy",
                    "message": "service temporarily unavailable",
                },
            }
        )

        self.assertEqual(
            mapped,
            [
                LiveEvent(
                    "session.error",
                    {
                        "code": "upstream_busy",
                        "message": "实时语音服务暂时不可用，请结束后重新开始",
                        "recoverable": True,
                    },
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
