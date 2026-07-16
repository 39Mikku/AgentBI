import unittest

from pydantic import ValidationError


FULL_METADATA = {
    "id": "a" * 24,
    "requested_name": "芽衣",
    "title": "雷电芽衣",
    "source_url": "https://mzh.moegirl.org.cn/example",
    "fetched_at": "2026-07-15T12:00:00+08:00",
    "updated_at": "2026-07-15T12:30:00+08:00",
    "character_count": 12,
    "content_sha256": "b" * 64,
}


class ToolboxMoegirlContractTests(unittest.TestCase):
    def test_fetch_request_trims_identity_and_name(self):
        from AgentBI.src.schemas.toolbox_moegirl_schema import MoegirlFetchRequest

        payload = MoegirlFetchRequest(user_id=" alice ", name=" 雷电芽衣 ")

        self.assertEqual(payload.user_id, "alice")
        self.assertEqual(payload.name, "雷电芽衣")

    def test_fetch_request_rejects_blank_overlong_and_extra_fields(self):
        from AgentBI.src.schemas.toolbox_moegirl_schema import MoegirlFetchRequest

        invalid_payloads = (
            {"user_id": "   ", "name": "雷电芽衣"},
            {"user_id": "alice", "name": "   "},
            {"user_id": "a" * 321, "name": "雷电芽衣"},
            {"user_id": "alice", "name": "雷" * 201},
            {"user_id": "alice", "name": "雷电芽衣", "url": "https://example.com"},
        )

        for values in invalid_payloads:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                MoegirlFetchRequest(**values)

    def test_summary_and_document_expose_complete_metadata(self):
        from AgentBI.src.schemas.toolbox_moegirl_schema import (
            MoegirlArtifactDocumentResponse,
            MoegirlArtifactSummaryResponse,
        )

        summary = MoegirlArtifactSummaryResponse(**FULL_METADATA)
        document = MoegirlArtifactDocumentResponse(
            **FULL_METADATA,
            markdown="# 雷电芽衣\n\n正文",
        )

        self.assertEqual(summary.model_dump(), FULL_METADATA)
        self.assertEqual(
            document.model_dump(),
            {**FULL_METADATA, "markdown": "# 雷电芽衣\n\n正文"},
        )

    def test_fetch_response_supports_saved_and_disambiguation_results(self):
        from AgentBI.src.schemas.toolbox_moegirl_schema import MoegirlFetchResponse

        saved = MoegirlFetchResponse(
            kind="saved",
            title="雷电芽衣",
            source_url="https://mzh.moegirl.org.cn/example",
            markdown="# 雷电芽衣",
            message="抓取完成并已保存",
            artifact=FULL_METADATA,
        )
        disambiguation = MoegirlFetchResponse(
            kind="disambiguation",
            title="芽衣",
            source_url="https://mzh.moegirl.org.cn/disambiguation",
            markdown="# 芽衣",
            message="该名称指向消歧义页，预览不会保存",
            artifact=None,
        )

        self.assertEqual(saved.artifact.requested_name, "芽衣")
        self.assertIsNone(disambiguation.artifact)
        with self.assertRaises(ValidationError):
            MoegirlFetchResponse(
                kind="other",
                title="芽衣",
                source_url="https://mzh.moegirl.org.cn/example",
                markdown="# 芽衣",
                message="invalid",
                artifact=None,
            )

    def test_fetch_response_enforces_kind_artifact_invariant(self):
        from AgentBI.src.schemas.toolbox_moegirl_schema import MoegirlFetchResponse

        common = {
            "title": "芽衣",
            "source_url": "https://mzh.moegirl.org.cn/example",
            "markdown": "# 芽衣",
            "message": "result",
        }

        with self.assertRaises(ValidationError):
            MoegirlFetchResponse(kind="saved", artifact=None, **common)
        with self.assertRaises(ValidationError):
            MoegirlFetchResponse(
                kind="disambiguation",
                artifact=FULL_METADATA,
                **common,
            )


if __name__ == "__main__":
    unittest.main()
