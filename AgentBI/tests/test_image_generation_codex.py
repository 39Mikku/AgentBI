import base64
import json
import tempfile
import time
import unittest
from pathlib import Path


PNG = b"\x89PNG\r\n\x1a\npro-image"


def jwt_with_account(account_id: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps(
            {"https://api.openai.com/auth": {"chatgpt_account_id": account_id}}
        ).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"header.{payload}.signature"


class _Response:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _RefreshClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.request = None

    async def post(self, url, **kwargs):
        self.request = (url, kwargs)
        return _Response(200, self.payload)


class _DeviceClient:
    def __init__(self):
        self.request = None

    async def post(self, url, **kwargs):
        self.request = (url, kwargs)
        return _Response(
            200,
            {
                "user_code": "ABCD-EFGH",
                "device_auth_id": "device-secret",
                "interval": 5,
            },
        )


class CodexOAuthStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_device_login_start_exposes_only_user_code_and_verification_url(self):
        from AgentBI.src.services.image_generation.codex_oauth import request_device_login

        client = _DeviceClient()
        pending = await request_device_login(client)

        self.assertEqual(pending.user_code, "ABCD-EFGH")
        self.assertEqual(pending.authorization_url, "https://auth.openai.com/codex/device")
        self.assertEqual(pending.device_auth_id, "device-secret")
        self.assertEqual(client.request[1]["json"]["client_id"], "app_EMoamEEZ73f0CkXaXp7hrann")
    async def test_refreshes_expiring_token_and_rotates_refresh_token_in_independent_file(self):
        from AgentBI.src.services.image_generation.codex_oauth import CodexOAuthTokenStore

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "codex-image-oauth.json"
            store = CodexOAuthTokenStore(path)
            store.save_tokens(
                {
                    "access_token": jwt_with_account("account-old"),
                    "refresh_token": "refresh-old",
                    "expires_in": 1,
                },
                now=int(time.time()) - 20,
            )
            client = _RefreshClient(
                {
                    "access_token": jwt_with_account("account-new"),
                    "refresh_token": "refresh-new",
                    "expires_in": 3600,
                }
            )

            token = await store.valid_access_token(client=client)

            self.assertEqual(token, jwt_with_account("account-new"))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["refresh_token"], "refresh-new")
            self.assertEqual(saved["account_id"], "account-new")
            self.assertNotIn("codex-cli", str(path).lower())
            self.assertEqual(client.request[1]["data"]["grant_type"], "refresh_token")

    async def test_status_and_disconnect_never_return_tokens(self):
        from AgentBI.src.services.image_generation.codex_oauth import CodexOAuthTokenStore

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "codex-image-oauth.json"
            store = CodexOAuthTokenStore(path)
            store.save_tokens(
                {
                    "access_token": jwt_with_account("account-1"),
                    "refresh_token": "refresh-secret",
                    "expires_in": 3600,
                }
            )

            status = store.status().model_dump()
            self.assertEqual(status["account_id"], "account-1")
            self.assertNotIn("access_token", status)
            self.assertNotIn("refresh_token", status)
            store.disconnect()
            self.assertFalse(store.status().connected)
            self.assertFalse(path.exists())


class CodexImageProtocolTests(unittest.TestCase):
    def test_builds_required_gpt_image_2_tool_request(self):
        from AgentBI.src.services.image_generation.codex_adapter import build_codex_payload

        payload = build_codex_payload(
            prompt="a silver moth",
            aspect_ratio="portrait",
            quality="high",
        )

        self.assertEqual(payload["model"], "gpt-5.5")
        self.assertFalse(payload["store"])
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["tools"][0]["model"], "gpt-image-2")
        self.assertEqual(payload["tools"][0]["size"], "1024x1536")
        self.assertEqual(payload["tools"][0]["quality"], "high")
        self.assertEqual(payload["tool_choice"]["mode"], "required")

    def test_codex_headers_include_account_without_exposing_token(self):
        from AgentBI.src.services.image_generation.codex_adapter import codex_headers

        headers = codex_headers(jwt_with_account("account-2"))

        self.assertEqual(headers["ChatGPT-Account-ID"], "account-2")
        self.assertEqual(headers["originator"], "codex_cli_rs")
        self.assertEqual(headers["Authorization"], f"Bearer {jwt_with_account('account-2')}")

    def test_extracts_latest_final_or_partial_image_from_sse(self):
        from AgentBI.src.services.image_generation.codex_adapter import (
            extract_image_b64,
            parse_sse_lines,
        )

        partial = base64.b64encode(b"partial").decode("ascii")
        final = base64.b64encode(PNG).decode("ascii")
        events = list(
            parse_sse_lines(
                [
                    "event: response.image_generation_call.partial_image\n",
                    f'data: {{"partial_image_b64":"{partial}"}}\n',
                    "\n",
                    f'data: {{"output": [{{"type":"image_generation_call","result":"{final}"}}]}}\n',
                    "\n",
                    "data: [DONE]\n",
                    "\n",
                ]
            )
        )

        self.assertEqual(extract_image_b64(events[0]), partial)
        self.assertEqual(extract_image_b64(events[1]), final)


class _StreamingResponse:
    status_code = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def aiter_lines(self):
        final = base64.b64encode(PNG).decode("ascii")
        yield "event: response.output_item.done"
        yield f'data: {{"item":{{"type":"image_generation_call","result":"{final}"}}}}'
        yield ""
        raise AssertionError("adapter consumed the stream after the final image event")


class _StreamingClient:
    def stream(self, *args, **kwargs):
        return _StreamingResponse()


class CodexImageStreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_as_soon_as_final_image_event_arrives(self):
        from AgentBI.src.services.image_generation.codex_adapter import CodexImageAdapter

        image = await CodexImageAdapter().generate(
            access_token=jwt_with_account("account-2"),
            prompt="a silver moth",
            aspect_ratio="square",
            quality="medium",
            client=_StreamingClient(),
        )

        self.assertEqual(image.image_bytes, PNG)
        self.assertEqual(image.model, "gpt-image-2")


if __name__ == "__main__":
    unittest.main()
