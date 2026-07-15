import unittest


class LoginServiceTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository

        self.repository = SqliteChatRepository(":memory:")

    def tearDown(self):
        self.repository.close()

    def test_first_email_login_creates_a_local_user_after_code_is_consumed(self):
        from AgentBI.src.services.login_service import LoginService

        sent = []
        service = LoginService(
            self.repository,
            sender=lambda to, subject, content: sent.append((to, subject, content)) or "ok",
            code_factory=lambda: "123456",
        )

        service.send_code("elysi@example.com")
        user = service.login("elysi@example.com", "123456")

        self.assertEqual(sent[0][0], "elysi@example.com")
        self.assertEqual(user["user_id"], "elysi@example.com")
        self.assertEqual(user["username"], "elysi")

    def test_existing_username_resolves_to_its_local_email(self):
        from AgentBI.src.services.login_service import LoginService

        existing = self.repository.create_user("elysi@example.com", username="Elysi")
        service = LoginService(self.repository, sender=lambda *_: "ok", code_factory=lambda: "123456")

        result = service.send_code("Elysi")
        user = service.login("Elysi", "123456")

        self.assertEqual(result["target_email"], existing["email"])
        self.assertEqual(user["user_id"], existing["user_id"])

    def test_login_response_returns_the_persisted_avatar(self):
        from AgentBI.src.api.api import login_response

        response = login_response(
            {
                "user_id": "elysi@example.com",
                "username": "Elysi",
                "email": "elysi@example.com",
                "avatar_data_url": "data:image/png;base64,AA==",
            }
        )

        self.assertEqual(response["data"]["avatar_data_url"], "data:image/png;base64,AA==")


if __name__ == "__main__":
    unittest.main()
