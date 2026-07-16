import unittest

import httpx

from AgentBI.src.services.toolbox.moegirl.scraper import (
    MoegirlContentError,
    MoegirlNotFoundError,
    MoegirlScraper,
    MoegirlUpstreamError,
    MoegirlValidationError,
)


MOESKIN_HTML = """
<title>雷电芽衣 - 萌娘百科</title>
<script>RLCONF={"wgPageName":"雷电芽衣","wgCategories":["崩坏3角色"]};</script>
<template id="MOE_SKIN_TEMPLATE_BODYCONTENT">
  <div id="mw-content-text"><div class="mw-parser-output"><h2>简介</h2><p>正文</p></div></div>
</template>
"""


class MoegirlScraperExtractionTests(unittest.TestCase):
    def test_extracts_article_from_moeskin_template(self):
        page = MoegirlScraper.extract(
            MOESKIN_HTML,
            "https://mzh.moegirl.org.cn/example",
        )

        self.assertEqual(page.title, "雷电芽衣")
        self.assertIn("mw-parser-output", page.article_html)
        self.assertEqual(page.categories, ("崩坏3角色",))

    def test_falls_back_to_direct_mediawiki_content(self):
        html = '<h1 id="firstHeading">可莉</h1><div id="mw-content-text"><p>正文</p></div>'

        page = MoegirlScraper.extract(
            html,
            "https://mzh.moegirl.org.cn/example",
        )

        self.assertEqual(page.title, "可莉")
        self.assertIn("正文", page.article_html)

    def test_falls_back_to_original_soup_when_moeskin_template_has_no_article(self):
        html = """
        <h1 id="firstHeading">可莉</h1>
        <div id="mw-content-text"><p>原始正文</p></div>
        <template id="MOE_SKIN_TEMPLATE_BODYCONTENT"><div>模板占位</div></template>
        """

        page = MoegirlScraper.extract(html, "https://mzh.moegirl.org.cn/example")

        self.assertIn("原始正文", page.article_html)

    def test_falls_back_to_title_and_category_links(self):
        html = """
        <title>琪亚娜 - 萌娘百科</title>
        <main><p>正文</p></main>
        <a href="/Category:崩坏3角色">崩坏3角色</a>
        """

        page = MoegirlScraper.extract(html, "https://mzh.moegirl.org.cn/example")

        self.assertEqual(page.title, "琪亚娜")
        self.assertEqual(page.categories, ("崩坏3角色",))

    def test_missing_title_or_article_raises_content_error(self):
        with self.assertRaises(MoegirlContentError):
            MoegirlScraper.extract("<main>正文</main>", "https://example.com")
        with self.assertRaises(MoegirlContentError):
            MoegirlScraper.extract("<h1>标题</h1>", "https://example.com")
        with self.assertRaises(MoegirlContentError):
            MoegirlScraper.extract(
                "<h1>标题</h1><main>  </main>",
                "https://example.com",
            )


class MoegirlScraperFetchTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_normalizes_name_and_sends_browser_headers(self):
        requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, text=MOESKIN_HTML, request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            page = await MoegirlScraper(client).fetch(" 雷电芽衣 ")

        self.assertEqual(
            requests[0].url.raw_path,
            b"/%E9%9B%B7%E7%94%B5%E8%8A%BD%E8%A1%A3",
        )
        self.assertIn("Mozilla", requests[0].headers["User-Agent"])
        self.assertIn("zh-CN", requests[0].headers["Accept-Language"])
        self.assertEqual(requests[0].extensions["timeout"]["read"], 30.0)
        self.assertEqual(page.source_url, str(requests[0].url))

    async def test_fetch_rejects_blank_or_overlong_names(self):
        scraper = MoegirlScraper()

        for name in ("   ", "字" * 201):
            with self.subTest(name_length=len(name)):
                with self.assertRaisesRegex(MoegirlValidationError, "200"):
                    await scraper.fetch(name)

    async def test_fetch_maps_404_to_not_found(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(MoegirlNotFoundError):
                await MoegirlScraper(client).fetch("不存在")

    async def test_fetch_maps_non_2xx_and_transport_errors_to_upstream_error(self):
        async def status_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, request=request)

        async def transport_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline", request=request)

        for handler in (status_handler, transport_handler):
            with self.subTest(handler=handler.__name__):
                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    with self.assertRaises(MoegirlUpstreamError):
                        await MoegirlScraper(client).fetch("雷电芽衣")


if __name__ == "__main__":
    unittest.main()
