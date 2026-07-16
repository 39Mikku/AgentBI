import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.services.toolbox.moegirl.artifact_store import (
    MoegirlArtifactDocument,
    MoegirlArtifactSummary,
)
from AgentBI.src.services.toolbox.moegirl.scraper import (
    MoegirlContentError,
    MoegirlNotFoundError,
    MoegirlUpstreamError,
    MoegirlValidationError,
)
from AgentBI.src.services.toolbox.moegirl.service import MoegirlFetchResult


ARTIFACT_ID = "a" * 24
SUMMARY = MoegirlArtifactSummary(
    id=ARTIFACT_ID,
    requested_name="芽衣",
    title="雷电/芽衣",
    source_url="https://mzh.moegirl.org.cn/example",
    fetched_at="2026-07-15T12:00:00+08:00",
    updated_at="2026-07-15T12:30:00+08:00",
    character_count=12,
    content_sha256="b" * 64,
)
DOCUMENT = MoegirlArtifactDocument(
    **SUMMARY.__dict__,
    markdown="# 雷电芽衣\n\n正文",
)


class FakeArchiveService:
    async def fetch(self, user_id, name):
        if name == "invalid":
            raise MoegirlValidationError("条目名称无效")
        if name == "missing":
            raise MoegirlNotFoundError("条目不存在")
        if name == "upstream":
            raise MoegirlUpstreamError("上游不可用")
        if name == "empty":
            raise MoegirlContentError("页面没有正文")
        if name == "disk":
            raise OSError("磁盘已满")
        if name == "芽衣":
            return MoegirlFetchResult(
                kind="disambiguation",
                title="芽衣",
                source_url="https://mzh.moegirl.org.cn/disambiguation",
                markdown="# 芽衣\n\n- 雷电芽衣",
                message="该名称指向消歧义页，预览不会保存",
                artifact=None,
            )
        return MoegirlFetchResult(
            kind="saved",
            title="雷电/芽衣",
            source_url=SUMMARY.source_url,
            markdown=DOCUMENT.markdown,
            message="抓取完成并已保存",
            artifact=SUMMARY,
        )


class FakeArtifactStore:
    def __init__(self):
        self.documents = {ARTIFACT_ID: DOCUMENT}

    def list(self, user_id):
        return [SUMMARY] if user_id == "alice" and self.documents else []

    def get(self, user_id, artifact_id):
        if user_id != "alice":
            return None
        return self.documents.get(artifact_id)

    def delete(self, user_id, artifact_id):
        if user_id != "alice" or artifact_id not in self.documents:
            return False
        del self.documents[artifact_id]
        return True


class ToolboxMoegirlApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.toolbox_moegirl import router

        app = FastAPI()
        app.state.moegirl_archive_service = FakeArchiveService()
        self.store = FakeArtifactStore()
        app.state.moegirl_artifact_store = self.store
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_saved_fetch_and_disambiguation_response_contract(self):
        saved = self.client.post(
            "/toolbox/moegirl/fetch",
            json={"user_id": " alice ", "name": " 雷电芽衣 "},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["kind"], "saved")
        self.assertEqual(saved.json()["artifact"]["requested_name"], "芽衣")
        self.assertEqual(saved.json()["artifact"]["content_sha256"], "b" * 64)

        disambiguation = self.client.post(
            "/toolbox/moegirl/fetch",
            json={"user_id": "alice", "name": "芽衣"},
        )
        self.assertEqual(disambiguation.status_code, 200)
        self.assertEqual(disambiguation.json()["kind"], "disambiguation")
        self.assertIsNone(disambiguation.json()["artifact"])

    def test_artifact_list_get_and_cross_user_not_found(self):
        listed = self.client.get("/toolbox/moegirl/artifacts?user_id=%20alice%20")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["id"], ARTIFACT_ID)
        self.assertEqual(listed.json()[0]["requested_name"], "芽衣")

        opened = self.client.get(
            f"/toolbox/moegirl/artifacts/{ARTIFACT_ID}?user_id=alice"
        )
        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.json()["markdown"], DOCUMENT.markdown)
        self.assertEqual(
            self.client.get(
                f"/toolbox/moegirl/artifacts/{ARTIFACT_ID}?user_id=bob"
            ).status_code,
            404,
        )

    def test_download_returns_utf8_markdown_attachment_with_safe_filename(self):
        response = self.client.get(
            f"/toolbox/moegirl/artifacts/{ARTIFACT_ID}/download?user_id=alice"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, DOCUMENT.markdown.encode("utf-8"))
        self.assertEqual(response.headers["content-type"], "text/markdown; charset=utf-8")
        disposition = response.headers["content-disposition"]
        self.assertIn(f'filename="moegirl-{ARTIFACT_ID}.md"', disposition)
        self.assertIn("filename*=UTF-8''", disposition)
        self.assertNotIn("雷电/芽衣", disposition)

    def test_delete_returns_204_and_unknown_artifact_returns_404(self):
        deleted = self.client.delete(
            f"/toolbox/moegirl/artifacts/{ARTIFACT_ID}?user_id=alice"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(
            self.client.delete(
                f"/toolbox/moegirl/artifacts/{ARTIFACT_ID}?user_id=alice"
            ).status_code,
            404,
        )

    def test_typed_service_errors_map_to_expected_statuses(self):
        expected = {
            "invalid": 422,
            "missing": 404,
            "upstream": 502,
            "empty": 502,
            "disk": 500,
        }
        for name, status_code in expected.items():
            with self.subTest(name=name):
                response = self.client.post(
                    "/toolbox/moegirl/fetch",
                    json={"user_id": "alice", "name": name},
                )
                self.assertEqual(response.status_code, status_code)

    def test_query_validation_rejects_blank_and_overlong_user_ids(self):
        for user_id in ("   ", "a" * 321):
            with self.subTest(user_id=user_id):
                response = self.client.get(
                    "/toolbox/moegirl/artifacts",
                    params={"user_id": user_id},
                )
                self.assertEqual(response.status_code, 422)

    def test_query_user_id_is_trimmed_before_length_validation(self):
        response = self.client.get(
            "/toolbox/moegirl/artifacts",
            params={"user_id": f" {'a' * 320} "},
        )

        self.assertEqual(response.status_code, 200)

    def test_dependencies_are_lazily_created_and_cached_on_app_state(self):
        from AgentBI.src.api.toolbox_moegirl import (
            get_moegirl_archive_service,
            get_moegirl_artifact_store,
        )

        app = FastAPI()

        class RequestStub:
            def __init__(self, target_app):
                self.app = target_app

        request = RequestStub(app)
        store = get_moegirl_artifact_store(request)
        service = get_moegirl_archive_service(request)
        self.assertIs(store, get_moegirl_artifact_store(request))
        self.assertIs(service, get_moegirl_archive_service(request))

    def test_main_app_registers_all_moegirl_routes(self):
        from AgentBI.main import app

        methods_by_path = {
            path: {method.upper() for method in operations}
            for path, operations in app.openapi()["paths"].items()
            if path.startswith("/toolbox/moegirl")
        }

        self.assertEqual(
            methods_by_path,
            {
                "/toolbox/moegirl/fetch": {"POST"},
                "/toolbox/moegirl/artifacts": {"GET"},
                "/toolbox/moegirl/artifacts/{artifact_id}": {"GET", "DELETE"},
                "/toolbox/moegirl/artifacts/{artifact_id}/download": {"GET"},
            },
        )


if __name__ == "__main__":
    unittest.main()
