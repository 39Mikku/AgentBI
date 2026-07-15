import unittest


class _FakeMusicClient:
    async def search_tracks(self, query):
        from AgentBI.src.schemas.music_schema import MusicTrack

        return [MusicTrack(id="1", name=f"{query} Song", artists=["Artist"], album="Album")]

    async def daily_recommendations(self):
        from AgentBI.src.schemas.music_schema import MusicTrack

        return [MusicTrack(id="2", name="Daily Song", artists=["Artist"])]

    async def resolve_track(self, track_id):
        from AgentBI.src.schemas.music_schema import MusicTrack

        return MusicTrack(id=str(track_id), name="Exact Song", artists=["Artist"])


class MusicAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_music_agent_exposes_only_music_tools(self):
        from AgentBI.src.agents.music_agent import MusicAgent

        names = {tool["function"]["name"] for tool in MusicAgent.tool_definitions()}
        self.assertEqual(names, {"search_tracks", "daily_recommendations", "resolve_track"})

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


if __name__ == "__main__":
    unittest.main()
