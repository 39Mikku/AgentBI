import unittest


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("POST", "https://api.tavily.com/search")
            raise httpx.HTTPStatusError("failed", request=request, response=httpx.Response(self.status_code, request=request))

    def json(self):
        return self.payload


class _HttpClient:
    def __init__(self, response):
        self.response = response

    async def post(self, url, **kwargs):
        self.request = (url, kwargs)
        return self.response


class TavilySearchClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_sends_a_lightweight_bearer_request_and_normalizes_sources(self):
        from AgentBI.src.services.tavily_search_client import TavilySearchClient

        http_client = _HttpClient(_Response({
            "query": "AgentBI",
            "results": [{
                "title": "AgentBI result",
                "url": "https://example.com/agentbi",
                "content": "Relevant excerpt",
                "score": 0.87,
                "raw_content": "must not leak",
            }],
        }))
        result = await TavilySearchClient(api_key="tvly-test", http_client=http_client).search(
            " AgentBI ",
            max_results=4,
            search_depth="basic",
            topic="general",
        )

        url, options = http_client.request
        self.assertEqual(url, "https://api.tavily.com/search")
        self.assertEqual(options["headers"]["Authorization"], "Bearer tvly-test")
        self.assertEqual(options["json"]["max_results"], 4)
        self.assertFalse(options["json"]["include_answer"])
        self.assertFalse(options["json"]["include_raw_content"])
        self.assertNotIn("raw_content", result["results"][0])

    async def test_missing_api_key_fails_before_network_request(self):
        from AgentBI.src.services.tavily_search_client import TavilySearchClient, TavilySearchError

        with self.assertRaises(TavilySearchError):
            await TavilySearchClient(api_key="").search("query")


if __name__ == "__main__":
    unittest.main()
