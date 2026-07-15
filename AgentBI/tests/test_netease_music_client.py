import json
import unittest

import httpx


class _AlwaysAvailableManager:
    base_url = "http://music.test"

    async def ensure_running(self):
        return True


def _client_with_routes(routes, cookie="MUSIC_U=top-secret-cookie"):
    from AgentBI.src.services.netease_music_client import NeteaseMusicClient

    async def handler(request):
        key = request.url.path
        payload = routes[key]
        if callable(payload):
            payload = payload(request)
        return httpx.Response(payload[0], json=payload[1], request=request)

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return NeteaseMusicClient(
        _AlwaysAvailableManager(),
        cookie=cookie,
        http_client=http_client,
    ), http_client


class NeteaseMusicClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_normalizes_song_variants_and_limits_results(self):
        client, http_client = _client_with_routes(
            {
                "/cloudsearch": (
                    200,
                    {
                        "code": 200,
                        "result": {
                            "songs": [
                                {
                                    "id": index,
                                    "name": f"Song {index}",
                                    "ar": [{"name": "A"}, {"name": "B"}],
                                    "al": {"name": "Album", "picUrl": "https://img.test/cover.jpg"},
                                    "dt": 123000,
                                }
                                for index in range(5)
                            ]
                        },
                    },
                )
            }
        )
        try:
            tracks = await client.search_tracks("night drive")
        finally:
            await http_client.aclose()

        self.assertEqual(len(tracks), 3)
        self.assertEqual(tracks[0].artists, ["A", "B"])
        self.assertEqual(tracks[0].album, "Album")
        self.assertEqual(tracks[0].cover_url, "https://img.test/cover.jpg")
        self.assertEqual(tracks[0].duration_ms, 123000)

    async def test_daily_recommendations_accepts_daily_songs_shape(self):
        client, http_client = _client_with_routes(
            {
                "/recommend/songs": (
                    200,
                    {
                        "code": 200,
                        "data": {
                            "dailySongs": [
                                {
                                    "id": 42,
                                    "name": "Daily",
                                    "artists": [{"name": "Artist"}],
                                    "album": {"name": "Record", "picUrl": "https://img.test/daily.jpg"},
                                    "duration": 999,
                                }
                            ]
                        },
                    },
                )
            }
        )
        try:
            tracks = await client.daily_recommendations()
        finally:
            await http_client.aclose()

        self.assertEqual(tracks[0].id, "42")
        self.assertEqual(tracks[0].artists, ["Artist"])
        self.assertEqual(tracks[0].duration_ms, 999)

    async def test_resolve_playback_marks_track_unavailable_when_url_is_missing(self):
        client, http_client = _client_with_routes(
            {"/song/url/v1": (200, {"code": 200, "data": [{"id": 7, "url": None, "message": "版权限制"}]})}
        )
        try:
            playback = await client.resolve_playback_url("7")
        finally:
            await http_client.aclose()

        self.assertFalse(playback.available)
        self.assertIsNone(playback.url)
        self.assertEqual(playback.unavailable_reason, "版权限制")

    async def test_expired_cookie_raises_sanitized_authentication_error(self):
        secret = "MUSIC_U=never-print-me"
        client, http_client = _client_with_routes(
            {"/recommend/songs": (200, {"code": 301, "message": f"需要登录 {secret}"})},
            cookie=secret,
        )
        try:
            with self.assertRaisesRegex(Exception, "Cookie") as raised:
                await client.daily_recommendations()
        finally:
            await http_client.aclose()

        self.assertNotIn(secret, str(raised.exception))

    async def test_http_301_is_reported_as_expired_cookie(self):
        client, http_client = _client_with_routes(
            {"/recommend/songs": (301, {"code": 301, "message": "需要登录"})}
        )
        try:
            with self.assertRaisesRegex(Exception, "Cookie"):
                await client.daily_recommendations()
        finally:
            await http_client.aclose()

    async def test_cookie_is_sent_only_as_an_internal_header(self):
        captured = {}

        def response(request):
            captured["cookie"] = request.headers.get("cookie")
            captured["url"] = str(request.url)
            return 200, {"code": 200, "result": {"songs": []}}

        client, http_client = _client_with_routes({"/cloudsearch": response})
        try:
            await client.search_tracks("hello")
        finally:
            await http_client.aclose()

        self.assertEqual(captured["cookie"], "MUSIC_U=top-secret-cookie")
        self.assertNotIn("top-secret-cookie", captured["url"])


if __name__ == "__main__":
    unittest.main()
