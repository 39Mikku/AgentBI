import unittest


class UserProfileSchemaTests(unittest.TestCase):
    def test_profile_prefers_database_username_and_persisted_avatar(self):
        from AgentBI.src.schemas.user_profile_schema import UserProfileResponse

        profile = UserProfileResponse.from_documents(
            "elysi@example.com",
            {"username": "Elysi", "email": "elysi@example.com"},
            {"avatar_data_url": "data:image/png;base64,avatar"},
        )

        self.assertEqual(profile.user_id, "elysi@example.com")
        self.assertEqual(profile.username, "Elysi")
        self.assertEqual(profile.email, "elysi@example.com")
        self.assertEqual(profile.avatar_data_url, "data:image/png;base64,avatar")


if __name__ == "__main__":
    unittest.main()
