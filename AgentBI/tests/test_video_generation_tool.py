import json
import unittest


class FakeVideoService:
    def __init__(self):
        self.payload = None

    async def submit(self, **payload):
        self.payload = payload
        return {
            "_id": "job-1",
            "status": "queued",
            "progress": 0,
            "prompt": payload["prompt"],
            "aspect_ratio": payload.get("aspect_ratio") or "16:9",
            "duration_seconds": payload.get("duration_seconds") or 5,
        }


class VideoGenerationToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_atomic_tool_returns_immediate_job_card(self):
        from AgentBI.src.tools.video_generation_tools import generate_video

        service = FakeVideoService()
        result = await generate_video(
            service,
            user_id="user@example.com",
            conversation_id="conversation-1",
            message_id="message-1",
            prompt="A paper kite crossing a blue sky",
            aspect_ratio="9:16",
            duration_seconds=10,
            use_attached_image=True,
            reference_image_data_url="data:image/png;base64,aW1hZ2U=",
        )

        self.assertEqual(service.payload["message_id"], "message-1")
        self.assertTrue(service.payload["use_attached_image"])
        self.assertEqual(
            service.payload["reference_image_data_url"],
            "data:image/png;base64,aW1hZ2U=",
        )
        self.assertEqual(result.card["kind"], "video.generation")
        self.assertEqual(result.card["payload"]["job_id"], "job-1")
        self.assertEqual(json.loads(result.content)["status"], "queued")
        self.assertNotIn("image", result.card["payload"])

    async def test_chat_agent_exposes_only_the_minimal_video_arguments(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        tools = ChatAgent.tool_definitions(["tool.video_generation"])
        self.assertEqual([item["function"]["name"] for item in tools], ["generate_video"])
        parameters = tools[0]["function"]["parameters"]
        self.assertEqual(
            set(parameters["properties"]),
            {"prompt", "aspect_ratio", "duration_seconds", "use_attached_image"},
        )
        self.assertEqual(parameters["required"], ["prompt"])

    async def test_duration_presets_use_string_enum_for_openai_compatible_schemas(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        tools = ChatAgent.tool_definitions(["tool.video_generation"])
        duration = tools[0]["function"]["parameters"]["properties"]["duration_seconds"]

        self.assertEqual(duration["type"], "string")
        self.assertEqual(
            duration["enum"],
            ["3", "5", "10", "18"],
        )

    async def test_chat_agent_invokes_video_service_with_current_message(self):
        from AgentBI.src.agents.chat_agent import ChatAgent

        service = FakeVideoService()
        result = await ChatAgent(
            capability_ids=["tool.video_generation"],
            user_id="user@example.com",
            conversation_id="conversation-1",
            video_generation_service=service,
            assistant_message_id="message-1",
        )._invoke_direct_tool(
            "generate_video",
            json.dumps({"prompt": "A paper kite", "duration_seconds": 3}),
            {},
        )

        self.assertEqual(result.card["payload"]["job_id"], "job-1")
        self.assertEqual(service.payload["duration_seconds"], 3)


class VideoGenerationRouteTests(unittest.TestCase):
    def test_job_status_route_is_registered(self):
        from AgentBI.src.api.video_generation import router

        self.assertIn(
            "/video-generation/jobs/{job_id}",
            {route.path for route in router.routes},
        )


if __name__ == "__main__":
    unittest.main()
