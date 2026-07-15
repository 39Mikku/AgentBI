import asyncio
import os
import sys
import unittest

import httpx


class BilibiliClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_normalizes_public_video_results_and_respects_limit(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient

        async def search_provider(query: str):
            self.assertEqual(query, "人工智能")
            return {
                "result": [
                    {
                        "bvid": "BV1xx411c7mD",
                        "title": "<em class=\"keyword\">人工智能</em> 入门",
                        "author": "测试 UP",
                        "pic": "//i0.hdslb.com/test.jpg",
                        "duration": "2:03",
                        "play": "12000",
                        "pubdate": 1710000000,
                        "description": "公开视频",
                    },
                    {
                        "bvid": "BV1Q541167Qg",
                        "title": "第二个视频",
                        "author": "另一位 UP",
                        "duration": "1:00:05",
                        "play": 42,
                    },
                ]
            }

        videos = await BilibiliClient(search_provider=search_provider).search_videos(" 人工智能 ", limit=1)

        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0].bvid, "BV1xx411c7mD")
        self.assertEqual(videos[0].title, "人工智能 入门")
        self.assertEqual(videos[0].cover_url, "https://i0.hdslb.com/test.jpg")
        self.assertEqual(videos[0].duration_seconds, 123)
        self.assertEqual(videos[0].play_count, 12000)
        self.assertEqual(videos[0].url, "https://www.bilibili.com/video/BV1xx411c7mD")

    async def test_detail_normalizes_owner_stats_and_description(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient

        async def detail_provider(bvid: str):
            self.assertEqual(bvid, "BV1xx411c7mD")
            return {
                "bvid": bvid,
                "title": "视频详情",
                "owner": {"name": "详情 UP"},
                "pic": "https://i0.hdslb.com/detail.jpg",
                "duration": 95,
                "pubdate": 1710000001,
                "desc": "详情简介",
                "stat": {"view": 9988},
            }

        video = await BilibiliClient(detail_provider=detail_provider).get_video("BV1xx411c7mD")

        self.assertEqual(video.author, "详情 UP")
        self.assertEqual(video.description, "详情简介")
        self.assertEqual(video.play_count, 9988)
        self.assertEqual(video.duration_seconds, 95)

    def test_http_bilibili_cover_urls_are_upgraded_to_https(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient

        self.assertEqual(
            BilibiliClient._cover_url("http://i0.hdslb.com/test.jpg"),
            "https://i0.hdslb.com/test.jpg",
        )

    async def test_empty_query_and_invalid_bvid_are_rejected_before_upstream_call(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient, BilibiliClientError

        client = BilibiliClient()
        with self.assertRaisesRegex(BilibiliClientError, "搜索关键词"):
            await client.search_videos("   ")
        with self.assertRaisesRegex(BilibiliClientError, "BV"):
            await client.get_video("not-a-bvid")

    async def test_upstream_errors_are_converted_to_stable_client_errors(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient, BilibiliClientError

        async def failing_search(_: str):
            raise RuntimeError("upstream implementation detail")

        with self.assertRaisesRegex(BilibiliClientError, "搜索失败") as raised:
            await BilibiliClient(search_provider=failing_search).search_videos("测试")
        self.assertNotIn("implementation detail", str(raised.exception))

    async def test_default_cli_adapter_uses_structured_utf8_output_and_enriches_search_results(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient

        async def cli_runner(arguments, environment):
            self.assertEqual(arguments[:4], ["bili", "search", "测试", "--type"])
            self.assertIn("--json", arguments)
            self.assertEqual(environment["PYTHONUTF8"], "1")
            self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")
            return (
                0,
                '{"ok":true,"schema_version":"1","data":[{"id":"BV1xx411c7mD","bvid":"BV1xx411c7mD","title":"测试视频","author":"测试 UP","play":1,"duration":"0:12"}]}',
                "",
            )

        async def detail_provider(bvid):
            return {
                "bvid": bvid,
                "title": "测试视频",
                "owner": {"name": "测试 UP"},
                "pic": "//i0.hdslb.com/enriched.jpg",
                "duration": 12,
                "stat": {"view": 1},
            }

        videos = await BilibiliClient(
            cli_runner=cli_runner,
            detail_provider=detail_provider,
        ).search_videos("测试")

        self.assertEqual([video.bvid for video in videos], ["BV1xx411c7mD"])
        self.assertEqual(videos[0].cover_url, "https://i0.hdslb.com/enriched.jpg")

    async def test_default_detail_http_adapter_converts_upstream_error_codes(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient, BilibiliClientError

        async def handler(_: httpx.Request):
            return httpx.Response(200, json={"code": -412, "message": "request blocked"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            with self.assertRaisesRegex(BilibiliClientError, "拒绝"):
                await BilibiliClient(http_client=http_client).get_video("BV1xx411c7mD")

    async def test_cli_error_envelope_is_converted_to_a_stable_search_error(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient, BilibiliClientError

        async def cli_runner(arguments, environment):
            return 1, '{"ok":false,"error":{"code":"request_failed","message":"blocked"}}', ""

        with self.assertRaisesRegex(BilibiliClientError, "CLI"):
            await BilibiliClient(cli_runner=cli_runner).search_videos("测试")


@unittest.skipUnless(os.name == "nt", "Windows SelectorEventLoop regression")
class BilibiliCliWindowsLoopTests(unittest.TestCase):
    def test_cli_runner_works_on_uvicorn_reload_selector_event_loop(self):
        from AgentBI.src.services.bilibili_client import BilibiliClient

        loop = asyncio.SelectorEventLoop()
        try:
            returncode, stdout, stderr = loop.run_until_complete(
                BilibiliClient()._run_cli(
                    [sys.executable, "-c", "print('selector-loop-ok')"],
                    os.environ.copy(),
                )
            )
        finally:
            loop.close()

        self.assertEqual(returncode, 0)
        self.assertEqual(stdout.strip(), "selector-loop-ok")
        self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
