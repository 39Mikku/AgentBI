import unittest


class _FakeBilibiliClient:
    async def search_videos(self, query, limit=3):
        from AgentBI.src.schemas.bilibili_schema import BilibiliVideo

        return [
            BilibiliVideo(
                bvid="BV1xx411c7mD",
                title=f"{query} 视频",
                author="测试 UP",
                cover_url="https://i0.hdslb.com/test.jpg",
                duration_seconds=95,
                play_count=1234,
                url="https://www.bilibili.com/video/BV1xx411c7mD",
            )
        ][:limit]

    async def get_video(self, bvid):
        from AgentBI.src.schemas.bilibili_schema import BilibiliVideo

        return BilibiliVideo(
            bvid=bvid,
            title="视频详情",
            author="测试 UP",
            url=f"https://www.bilibili.com/video/{bvid}",
        )


class _EmptyBilibiliClient:
    async def search_videos(self, query, limit=3):
        return []


class BilibiliAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_exposes_only_video_search_and_detail_tools(self):
        from AgentBI.src.agents.bilibili_agent import BilibiliAgent

        names = {tool["function"]["name"] for tool in BilibiliAgent.tool_definitions()}
        self.assertEqual(names, {"search_videos", "get_video_detail"})

    async def test_search_returns_stable_video_card_without_player_or_cookie_data(self):
        from AgentBI.src.agents.bilibili_agent import BilibiliAgent

        result = await BilibiliAgent(_FakeBilibiliClient())._invoke_tool(
            "search_videos",
            '{"query":"Python"}',
        )

        self.assertEqual(result.card["kind"], "bilibili.video-list")
        self.assertEqual(result.card["payload"]["videos"][0]["bvid"], "BV1xx411c7mD")
        serialized = str(result.card).lower()
        self.assertNotIn("player.bilibili.com", serialized)
        self.assertNotIn("cookie", serialized)

    async def test_detail_returns_single_video_card(self):
        from AgentBI.src.agents.bilibili_agent import BilibiliAgent

        result = await BilibiliAgent(_FakeBilibiliClient())._invoke_tool(
            "get_video_detail",
            '{"bvid":"BV1xx411c7mD"}',
        )

        self.assertEqual(result.card["kind"], "bilibili.video")
        self.assertEqual(len(result.card["payload"]["videos"]), 1)

    async def test_empty_search_result_does_not_create_an_empty_card(self):
        from AgentBI.src.agents.bilibili_agent import BilibiliAgent

        result = await BilibiliAgent(_EmptyBilibiliClient())._invoke_tool(
            "search_videos",
            '{"query":"不存在的视频"}',
        )

        self.assertIsNone(result.card)
        self.assertIn("没有找到", result.content)

    async def test_unknown_tool_is_returned_as_text_error(self):
        from AgentBI.src.agents.bilibili_agent import BilibiliAgent

        result = await BilibiliAgent(_FakeBilibiliClient())._invoke_tool("like_video", "{}")

        self.assertIsNone(result.card)
        self.assertIn("未知", result.content)


if __name__ == "__main__":
    unittest.main()
