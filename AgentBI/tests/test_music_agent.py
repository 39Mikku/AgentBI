import unittest


class _FakeMusicClient:
    def __init__(self):
        self.search_limit = None
        self.daily_limit = None
        self.liked_limit = None

    async def search_tracks(self, query, limit=3):
        from AgentBI.src.schemas.music_schema import MusicTrack

        self.search_limit = limit
        return [MusicTrack(id="1", name=f"{query} Song", artists=["Artist"], album="Album")]

    async def daily_recommendations(self, limit=10):
        from AgentBI.src.schemas.music_schema import MusicTrack

        self.daily_limit = limit
        return [MusicTrack(id="2", name="Daily Song", artists=["Artist"])]

    async def liked_tracks(self, limit=20):
        from AgentBI.src.schemas.music_schema import MusicTrack

        self.liked_limit = limit
        return [MusicTrack(id="3", name="Liked Song", artists=["Artist"])]

    async def resolve_track(self, track_id):
        from AgentBI.src.schemas.music_schema import MusicTrack

        return MusicTrack(id=str(track_id), name="Exact Song", artists=["Artist"])


class MusicAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_music_agent_exposes_only_music_tools(self):
        from AgentBI.src.agents.music_agent import MusicAgent

        names = {tool["function"]["name"] for tool in MusicAgent.tool_definitions()}
        self.assertEqual(
            names,
            {"search_tracks", "daily_recommendations", "liked_tracks", "resolve_track"},
        )

    async def test_music_tool_result_contains_a_stable_card_without_cookie_or_playback_url(self):
        from AgentBI.src.agents.music_agent import MusicAgent

        result = await MusicAgent(_FakeMusicClient())._invoke_tool(
            "search_tracks",
            '{"query":"Night"}',
        )

        self.assertEqual(result.card["kind"], "music.track-list")
        self.assertEqual(result.card["payload"]["tracks"][0]["id"], "1")
        serialized = str(result.card).lower()
        self.assertNotIn("cookie", serialized)
        self.assertNotIn("playback_url", serialized)

    async def test_unknown_music_tool_returns_an_error_instead_of_raising(self):
        from AgentBI.src.agents.music_agent import MusicAgent

        result = await MusicAgent(_FakeMusicClient())._invoke_tool("send_email", "{}")

        self.assertIn("未知", result.content)
        self.assertIsNone(result.card)

    async def test_music_agent_uses_only_its_own_result_limits(self):
        from AgentBI.src.agents.music_agent import MusicAgent

        client = _FakeMusicClient()
        agent = MusicAgent(
            client,
            settings={"search_result_limit": 5, "daily_result_limit": 12, "liked_result_limit": 24},
        )

        await agent._invoke_tool("search_tracks", '{"query":"Night"}')
        await agent._invoke_tool("daily_recommendations", "{}")
        liked = await agent._invoke_tool("liked_tracks", "{}")

        self.assertEqual(client.search_limit, 5)
        self.assertEqual(client.daily_limit, 12)
        self.assertEqual(client.liked_limit, 24)
        self.assertEqual(liked.card["kind"], "music.track-list")
        self.assertEqual(liked.card["payload"]["title"], "我喜欢的音乐")


if __name__ == "__main__":
    unittest.main()
