import unittest


class ToolboxTtsRepositoryTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")

    def tearDown(self):
        self.repository.close()

    def _create(self, user_id: str = "alice", provider: str = "bailian"):
        return self.repository.create_toolbox_tts_voice(
            {
                "user_id": user_id,
                "provider": provider,
                "display_name": "旁白音色",
                "external_voice_id": "voice-001",
                "voice_kind": "cloned",
                "bound_model": "cosyvoice-v3.5-plus" if provider == "bailian" else None,
                "provider_metadata": {"source": "console"},
            }
        )

    def test_voice_catalog_is_scoped_by_user_and_preserves_metadata(self):
        created = self._create()
        self._create("bob")

        voices = self.repository.list_toolbox_tts_voices("alice")

        self.assertEqual(len(voices), 1)
        self.assertEqual(voices[0]["id"], created["id"])
        self.assertEqual(voices[0]["provider_metadata"], {"source": "console"})
        self.assertEqual(voices[0]["bound_model"], "cosyvoice-v3.5-plus")

    def test_foreign_user_cannot_update_or_delete_voice(self):
        voice = self._create()

        updated = self.repository.update_toolbox_tts_voice(
            voice["id"], "bob", {"display_name": "偷改"}
        )
        deleted = self.repository.delete_toolbox_tts_voice(voice["id"], "bob")

        self.assertIsNone(updated)
        self.assertFalse(deleted)
        self.assertEqual(
            self.repository.list_toolbox_tts_voices("alice")[0]["display_name"],
            "旁白音色",
        )

    def test_voice_can_be_renamed_rebound_and_deleted(self):
        voice = self._create()

        updated = self.repository.update_toolbox_tts_voice(
            voice["id"],
            "alice",
            {
                "display_name": "快速旁白",
                "bound_model": "cosyvoice-v3.5-flash",
                "provider_metadata": {"note": "新版"},
            },
        )

        self.assertEqual(updated["display_name"], "快速旁白")
        self.assertEqual(updated["bound_model"], "cosyvoice-v3.5-flash")
        self.assertEqual(updated["provider_metadata"], {"note": "新版"})
        self.assertTrue(self.repository.delete_toolbox_tts_voice(voice["id"], "alice"))
        self.assertEqual(self.repository.list_toolbox_tts_voices("alice"), [])


if __name__ == "__main__":
    unittest.main()
